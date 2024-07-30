from math import e
import json
import stripe
import os
import random
import string
from dotenv import load_dotenv
import boto3
from keyflow_backend_app.models.portfolio import Portfolio
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.rental_unit import RentalUnit
import sendgrid
import os
from sendgrid.helpers.mail import Mail, Email, To, Content
from sendgrid import SendGridAPIClient
from datetime import datetime, time, timezone
from dateutil.relativedelta import relativedelta
from datetime import datetime



load_dotenv()

#Create a random hash string of a specific length
def make_id(length):
    result = ""
    characters = string.ascii_letters + string.digits
    characters_length = len(characters)
    counter = 0
    while counter < length:
        result += characters[random.randint(0, characters_length - 1)]
        counter += 1
    return result


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


# Function to generate a presigned URL for a specific S3 file
def generate_presigned_url(file_key):
    s3_client = boto3.client("s3", region_name=os.getenv("AWS_S3_REGION_NAME"))

    # Generate a presigned URL for the file_key within your S3 bucket
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "Key": file_key,
        },
        ExpiresIn=3600,  # Optional: URL expiration time in seconds
    )

    return presigned_url

def calculate_final_price_in_cents(invoice_amount):
    invoice_amount_in_cents = int(invoice_amount * 100)
    if not isinstance(invoice_amount_in_cents, int):
        raise ValueError("invoice_amount_in_cents must be an integer representing cents")

    stripe_fee_percentage = 0.03 # 3% fee
    stripe_fee_fixed = 30  # Fixed fee in cents

    stripe_fee = (invoice_amount_in_cents * stripe_fee_percentage) + stripe_fee_fixed
    final_price = invoice_amount_in_cents + stripe_fee

    return {
        "stripe_fee_in_cents": int(stripe_fee),
        "final_price_in_cents": int(final_price),
        "stripe_fee": stripe_fee / 100,
        "final_price": final_price / 100
    }

def calculate_rent_periods(lease_start_date, rent_frequency, term):
    rent_periods = []
    current_date = lease_start_date
    end_date = None
    if rent_frequency == "month":
        end_date = lease_start_date + relativedelta(months=term)
    elif rent_frequency == "week":
        end_date = lease_start_date + relativedelta(weeks=term)
    elif rent_frequency == "day":
        end_date = lease_start_date + relativedelta(days=term)
    elif rent_frequency == "year":
        end_date = lease_start_date + relativedelta(years=term)

    while current_date < end_date:
        period_start = current_date
        if rent_frequency == "month":
            next_period_end = current_date + relativedelta(months=1)
        elif rent_frequency == "week":
            next_period_end = current_date + relativedelta(weeks=1)
        elif rent_frequency == "day":
            next_period_end = current_date + relativedelta(days=1)
        elif rent_frequency == "year":
            next_period_end = current_date + relativedelta(years=1)
        
        period_end = min(next_period_end, end_date)
        rent_periods.append((period_start, period_end))
        current_date = period_end

    return rent_periods

def create_invoice_for_period(
    period_start,
    period_end,
    rent_amount,
    customer_id,
    due_date,
    unit,
    additional_charges_dict,
    lease_agreement
):
    due_date_end_of_day = datetime.combine(due_date, time.max)
    current_time = datetime.now()
    if due_date_end_of_day <= current_time:
        due_date_end_of_day = current_time + relativedelta(days=1)

    invoice = stripe.Invoice.create(
        customer=customer_id,
        auto_advance=True,
        collection_method="send_invoice",
        due_date=int(due_date_end_of_day.timestamp()),
        metadata={
            "type": "rent_payment",
            "subtype": "stripe_invoice",
            "description": f"Rent payment for {period_start.strftime('%m/%d/%Y')} - {period_end.strftime('%m/%d/%Y')}",
            "tenant_id": unit.tenant.id,
            "owner_id": unit.owner.id,
            "rental_property_id": unit.rental_property.id,
            "rental_unit_id": unit.id,
            "lease_agreement_id": lease_agreement.id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
        transfer_data={"destination": unit.owner.stripe_account_id},
    )

    price = stripe.Price.create(
        unit_amount=int(rent_amount * 100),
        currency="usd",
        product_data={"name": f"Rent for unit {unit.name} at {unit.rental_property.name}"},
    )

    stripe.InvoiceItem.create(
        customer=customer_id,
        price=price.id,
        currency="usd",
        description="Rent payment",
        invoice=invoice.id,
    )

    stripe_fee_in_cents = calculate_final_price_in_cents(rent_amount)["stripe_fee_in_cents"]

    stripe_fee_product = stripe.Product.create(name="Payment processing fee", type="service")
    stripe_fee_price = stripe.Price.create(
        unit_amount=int(stripe_fee_in_cents),
        currency="usd",
        product=stripe_fee_product.id,
    )

    stripe.InvoiceItem.create(
        customer=customer_id,
        price=stripe_fee_price.id,
        currency="usd",
        description="Payment processing fee",
        invoice=invoice.id,
    )

    if additional_charges_dict:
        for charge in additional_charges_dict:
            amount = charge["amount"]
            if isinstance(amount, str):
                amount = float(amount)
            charge_amount = amount
            charge_name = charge["name"]
            charge_product_name = f"{charge_name} for unit {unit.name} at {unit.rental_property.name}"

            charge_product = stripe.Product.create(name=charge_product_name, type="service")
            charge_price = stripe.Price.create(
                unit_amount=int(charge_amount * 100),
                currency="usd",
                product=charge_product.id,
            )
            stripe.InvoiceItem.create(
                customer=customer_id,
                price=charge_price.id,
                currency="usd",
                description=charge_product_name,
                invoice=invoice.id,
            )

    stripe.Invoice.finalize_invoice(invoice.id)
    return invoice

def create_rent_invoices(
    lease_start_date,
    rent_amount,
    rent_frequency,
    lease_term,
    customer_id,
    unit,
    additional_charges_dict,
    lease_agreement
):
    cancel_existing_rent_subscriptions(customer_id)
    
    rent_periods = calculate_rent_periods(
        lease_start_date, rent_frequency, lease_term
    )
    print("Rent Periods:", rent_periods)  # Debug print

    lease_terms = json.loads(unit.lease_terms)
    combined_payments = next(
        (item for item in lease_terms if item["name"] == "combine_payments"),
        None,
    )
    security_deposit = next(
        (item for item in lease_terms if item["name"] == "security_deposit"),
        None,
    )
    security_deposit_amount = float(security_deposit["value"])
    #add 1 day to the security deposit due date and convert it to a timestamp
    security_deposit_due_date = lease_start_date + relativedelta(days=+1)
    security_deposit_due_date_timestamp = int(security_deposit_due_date.timestamp())
    #If the security deposit amount is greater than 0, create an invoice for the security deposit
    if security_deposit_amount > 0:
        security_deposit_invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=True,
            collection_method="send_invoice",
            due_date=int(security_deposit_due_date_timestamp),
            metadata={
                "type": "security_deposit",
                "subtype": "stripe_invoice",
                "description": "Security deposit",
                "tenant_id": unit.tenant.id,
                "owner_id": unit.owner.id,
                "rental_property_id": unit.rental_property.id,
                "rental_unit_id": unit.id,
                "lease_agreement_id": lease_agreement.id,
            },
            transfer_data={"destination": unit.owner.stripe_account_id},
        )

        security_deposit_price = stripe.Price.create(
            unit_amount=int(security_deposit_amount * 100),
            currency="usd",
            product_data={"name": f"Security deposit for unit {unit.name} at {unit.rental_property.name}"},
        )

        stripe.InvoiceItem.create(
            customer=customer_id,
            price=security_deposit_price.id,
            currency="usd",
            description="Security deposit",
            invoice=security_deposit_invoice.id,
        )

        stripe.Invoice.finalize_invoice(security_deposit_invoice)

    grace_period = next(
        (item for item in lease_terms if item["name"] == "grace_period"),
        None,
    )
    grace_period_value = int(grace_period["value"])
    grace_period_increase = None

    paid_invoices = stripe.Invoice.list(customer=customer_id, status="paid")
    paid_periods = set()

    for invoice in paid_invoices:
        if invoice.metadata.get("lease_agreement_id") == None:
            continue
        if int(invoice.metadata.get("lease_agreement_id")) == lease_agreement.id:
            period_start = datetime.fromisoformat(invoice.metadata.get("period_start"))
            period_end = datetime.fromisoformat(invoice.metadata.get("period_end"))
            paid_periods.add((period_start, period_end))
        print("Paid Invoice Metdata:", invoice.metadata)  # Debug print

    print("Paid Periods:", paid_periods)  # Debug print
    
    if combined_payments and combined_payments["value"] == "combined":
        due_date = lease_start_date + relativedelta(days=+grace_period_value)
        due_date_end_of_day = datetime.combine(due_date, time.max)
        current_time = datetime.now()
        if due_date_end_of_day <= current_time:
            due_date_end_of_day = current_time + relativedelta(days=1)

        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=True,
            collection_method="send_invoice",
            due_date=int(due_date_end_of_day.timestamp()),
            metadata={
                "type": "rent_payment",
                "subtype": "stripe_invoice",
                "description": "Rent payment",
                "tenant_id": unit.tenant.id,
                "owner_id": unit.owner.id,
                "rental_property_id": unit.rental_property.id,
                "rental_unit_id": unit.id,
                "lease_agreement_id": lease_agreement.id,
            },
            transfer_data={"destination": unit.owner.stripe_account_id},
        )

        price = stripe.Price.create(
            unit_amount=int(rent_amount * 100),
            currency="usd",
            product_data={"name": f"Rent for unit {unit.name} at {unit.rental_property.name}"},
        )

        for period_start, period_end in rent_periods:
            if (period_start, period_end) in paid_periods:
                continue

            formatted_period_start = period_start.strftime("%m/%d/%Y")
            stripe.InvoiceItem.create(
                customer=customer_id,
                price=price.id,
                currency="usd",
                description=f"Rent payment for {formatted_period_start}",
                invoice=invoice.id,
            )

            if additional_charges_dict:
                for charge in additional_charges_dict:
                    charge_amount = int(charge["amount"])
                    charge_name = charge["name"]
                    charge_product_name = f"{charge_name} for unit {unit.name} at {unit.rental_property.name}"
                    charge_product = stripe.Product.create(name=charge_product_name, type="service")
                    charge_price = stripe.Price.create(
                        unit_amount=int(charge_amount * 100),
                        currency="usd",
                        product=charge_product.id,
                    )
                    stripe.InvoiceItem.create(
                        customer=customer_id,
                        price=charge_price.id,
                        currency="usd",
                        description=charge_product_name,
                        invoice=invoice.id,
                    )

        stripe.Invoice.finalize_invoice(invoice.id)
        return invoice

    for period_start, period_end in rent_periods:
        if (period_start, period_end) in paid_periods:
            continue
        print(f"Creating invoice for period: {period_start} to {period_end}")  # Debug print
        create_invoice_for_period(
            period_start,
            period_end,
            rent_amount,
            customer_id,
            # period_end + relativedelta(days=+grace_period_value), # uncomment when grace period is inmplemnted
            period_end,
            unit,
            additional_charges_dict,
            lease_agreement,
        )

def cancel_existing_rent_subscriptions(customer_id):
    subscriptions = stripe.Subscription.list(customer=customer_id)
    for subscription in subscriptions.auto_paging_iter():
        if subscription.metadata.get("type") == "rent_payment":
            stripe.Subscription.cancel(subscription.id)

#Create a function that is called when autopay is enabled and creates a subscription for the tenant and deletes all of the tenants unpaid invoices.
def create_autopay_subscription_for_tenant(customer_id, unit, lease_agreement):

    # Retrieve all of the tenants unpaid invoices with the same lease_agreement id in the metadata  
    invoices = stripe.Invoice.list(customer=customer_id, status="open", limit=100)
    for invoice in invoices:
        if int(invoice.metadata.get("lease_agreement_id")) == int(lease_agreement.id) and invoice.metadata.get("type") == "rent_payment":
            stripe.Invoice.void_invoice(invoice.id)
            print(f"Voided invoice with matching lease agreement and type {invoice.id}")
            print("Cancelled Invoice metadata",invoice.metadata)
            print("Cancelled Invoice metadata type",invoice.metadata.get("type") )
            print("Cancelled Invoice metadata lease_agreement_id",invoice.metadata.get("lease_agreement_id") )
    
    #Retrieve any or all security deposit invoices with the same lease_agreement id in the metadata
    security_deposit_invoices = stripe.Invoice.list(customer=customer_id, status="open", limit=100)
    for invoice in security_deposit_invoices:
        if int(invoice.metadata.get("lease_agreement_id")) == int(lease_agreement.id) and invoice.metadata.get("type") == "security_deposit":
            #Pay the security deposit invoice
            stripe.Invoice.pay(invoice.id)
            print(f"Voided security deposit invoice with matching lease agreement and type {invoice.id}")

    lease_terms = json.loads(unit.lease_terms)

    combined_payments = next(
        (item for item in lease_terms if item["name"] == "combine_payments"),
        None,
    )

    #Check if the lease terms are combined payments. If it is return an error message saying that the lease terms are combined payments and the tenant cannot enable autopay.
    if combined_payments["value"] == "combined":
        return "Error: Lease terms are combined payments. Tenant cannot enable autopay."

    rent = next(
        (item for item in lease_terms if item["name"] == "rent"),
        None,
    )
    rent_amount = float(rent["value"])
    rent_frequency = next(
        (item for item in lease_terms if item["name"] == "rent_frequency"),
        None,
    )
    rent_frequency = rent_frequency["value"]
    # Create a Stripe price for the rent amount
    price = stripe.Price.create(
        unit_amount=int(rent_amount * 100),
        currency="usd",
        product_data={
            "name": f"Rent for unit {unit.name} at {unit.rental_property.name}"
        },
        recurring={"interval": rent_frequency},
    )

    # Using the trial_end parameter to set when the subscription should start
    trial_end = None
    invoices = stripe.Invoice.list(customer=customer_id, status="paid", limit=100)
    # Get the number of invoices that have been paid
    num_paid_invoices = len(invoices.data)

    # Get the lease agreement start_date
    lease_start_date = lease_agreement.start_date

    # Convert lease_start_date to datetime object
    lease_start_datetime = datetime.combine(lease_start_date, datetime.min.time())

    # Calculate trial_end based on rent frequency
    if rent_frequency == "month":
        trial_end = lease_start_datetime + relativedelta(months=num_paid_invoices)
    elif rent_frequency == "week":
        trial_end = lease_start_datetime + relativedelta(weeks=num_paid_invoices)
    elif rent_frequency == "day":
        trial_end = lease_start_datetime + relativedelta(days=num_paid_invoices)
    elif rent_frequency == "year":
        trial_end = lease_start_datetime + relativedelta(years=num_paid_invoices)

    # Convert trial_end to a Unix timestamp
    trial_end_timestamp = int(trial_end.timestamp())

    # Ensure trial_end is in the future
    current_timestamp = int(datetime.now().timestamp())
    if trial_end_timestamp <= current_timestamp:
        # If trial_end is in the past or current time, set it to a future timestamp (e.g., 1 hour from now)
        trial_end_timestamp = current_timestamp + 3600  # 3600 seconds = 1 hour

    # Assuming lease_agreement.end_date is a datetime.date object
    cancel_at = None

    # Convert the date object to a datetime object
    dt_object = datetime.combine(lease_agreement.end_date, datetime.min.time())

    #Add one day to the end date
    dt_object = dt_object + relativedelta(days=+1)

    # Convert the datetime object to a timestamp
    cancel_at = int(dt_object.timestamp())
        
    # Create a Stripe subscription for the tenant (No stripe fee is added to the subscription)
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[
            {
                "price": price.id,
            },
        ],
        metadata={
            "type": "rent_payment",
            "subtype": "stripe_subscription",
            "description": "Rent payment",
            "tenant_id": unit.tenant.id,
            "owner_id": unit.owner.id,
            "rental_property_id": unit.rental_property.id,
            "rental_unit_id": unit.id,
            "lease_agreement_id": lease_agreement.id, #TODO: Add lease agreement to metadata
        },
        transfer_data={"destination": unit.owner.stripe_account_id},
        trial_end=trial_end_timestamp,
        cancel_at=cancel_at
    )

    return subscription
    
#Create a function that checks to see if a name for a unit with the same property already exists
def unitNameIsValid(rental_property, name, owner):
    try:
        #Remove white spaces from the name
        name = name.strip()
        rental_property_instance = RentalProperty.objects.get(id=rental_property)
        if RentalUnit.objects.filter(owner=owner, rental_property=rental_property_instance, name=name).exists():
            return False
        return True
    except RentalProperty.DoesNotExist:
        return True

    
#Create a helper function validate_property_name that checks if the property name already exists with this owner
def propertyNameIsValid(name, owner):
    #Remove white spaces from the name
    name = name.strip()
    if RentalProperty.objects.filter(name=name, owner=owner).exists():
        return False
    return True

#Create a helper function isPortfolioNameValid that checks if the portfolio name already exists with this owner
def portfolioNameIsValid(name, owner):
    #Remove white spaces from the name
    name = name.strip()
    if Portfolio.objects.filter(name=name, owner=owner).exists():
        return False
    return True

