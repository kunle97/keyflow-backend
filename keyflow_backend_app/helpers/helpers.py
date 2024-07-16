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


def sendEmailBySendGrid(from_email, to_email, subject, content, is_html=False):
    api_key = os.getenv("SENDGRID_API_KEY")
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    from_email = Email(from_email)  # Change to your verified sender
    if os.getenv("ENVIRONMENT") == "development":
        to_email = "keyflowsoftware@gmail.com"
    to_emails = To(to_email)  # Change to your recipient
    # Check if content is html
    if is_html:
        content = Content("text/html", content)
        mail = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=content
        )
    else:
        content = Content("text/plain", content)
        mail = Mail(
            from_email=from_email,
            to_emails=to_emails,
            subject=subject,
            html_content=content
        )

    try:
        # Send an HTTP POST request to /mail/send
        response = sg.send(mail)
        print(response.status_code)
        print(response.headers)
        print(response.body)
        return response
    except Exception as e:
        print(e)


#Test Integration  SendGrid API KEy: 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
def sendGridTestIntegreation():
    message = Mail(
    from_email='from_email@example.com',
    to_emails='to@example.com',
    subject='Sending with Twilio SendGrid is Fun',
    html_content='<strong>and easy to do anywhere, even with Python</strong>')
    try:
        sg = SendGridAPIClient("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")
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

def calculate_final_price_in_cents(invoice_amount):
    invoice_amount_in_cents = int(invoice_amount * 100)
    # Ensure invoice_amount_in_cents is an int
    if not isinstance(invoice_amount_in_cents, int):
        print(invoice_amount_in_cents)
        raise ValueError("invoice_amount_in_cents must be an integer representing cents")

    stripe_fee_percentage = 0.03 # 3% fee
    stripe_fee_fixed = 30  # Fixed fee in cents

    # Calculate fee in cents
    stripe_fee = (invoice_amount_in_cents * stripe_fee_percentage)+ stripe_fee_fixed
    final_price = invoice_amount_in_cents + stripe_fee

   #return the stripe fee and the final price in a dictionary
    return {
        "stripe_fee_in_cents": int(stripe_fee),
        "final_price_in_cents": int(final_price),
        "stripe_fee": stripe_fee/100,
        "final_price": final_price/100
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
        period_end = None
        if rent_frequency == "month":
            next_period_end = current_date + relativedelta(months=1)
        elif rent_frequency == "week":
            next_period_end = current_date + relativedelta(weeks=1)
        elif rent_frequency == "day":
            next_period_end = current_date + relativedelta(days=1)
        elif rent_frequency == "year":
            next_period_end = current_date + relativedelta(years=1)
        
        # Ensure the period end does not exceed the lease end date
        period_end = min(next_period_end, end_date)

        rent_periods.append((period_start, period_end))
        current_date = period_end

    return rent_periods
def create_invoice_for_period(
    period_start,
    rent_amount,
    customer_id,
    due_date,
    unit,
    additional_charges_dict,
    lease_agreement
):

    # Set time part of due_date to end of the day
    due_date_end_of_day = datetime.combine(due_date, time.max)

    # Ensure due_date is in the future
    current_time = datetime.now()
    if due_date_end_of_day <= current_time:
        due_date_end_of_day = current_time + relativedelta(days=1)  # Adjust as needed to ensure it's in the future

    # Create Stripe Invoice for the specified rent payment period
    invoice = stripe.Invoice.create(
        customer=customer_id,
        auto_advance=True,
        collection_method="send_invoice",
        due_date=int(due_date_end_of_day.timestamp()),
        metadata={
            "type": "rent_payment",
            "description": "Rent payment",
            "tenant_id": unit.tenant.id,
            "owner_id": unit.owner.id,
            "rental_property_id": unit.rental_property.id,
            "rental_unit_id": unit.id,
            "lease_agreement_id": lease_agreement.id, #TODO: Add lease agreement to metadata
        },
        transfer_data={"destination": unit.owner.stripe_account_id},
    )

    # Create a Stripe price for the rent amount
    price = stripe.Price.create(
        unit_amount=int(rent_amount * 100),
        currency="usd",
        product_data={
            "name": f"Rent for unit {unit.name} at {unit.rental_property.name}"
        },
    )

    # Create a Stripe invoice item for the rent amount
    invoice_item = stripe.InvoiceItem.create(
        customer=customer_id,
        price=price.id,
        currency="usd",
        description="Rent payment",
        invoice=invoice.id,
    )

    # Calculate the Stripe fee based on the rent amount
    stripe_fee_in_cents = calculate_final_price_in_cents(rent_amount)["stripe_fee_in_cents"]
    
    # Create a Stripe product and price for the Stripe fee
    stripe_fee_product = stripe.Product.create(
        name=f"Payment processing fee",
        type="service",
    )
    stripe_fee_price = stripe.Price.create(
        unit_amount=int(stripe_fee_in_cents),
        currency="usd",
        product=stripe_fee_product.id,
    )

    # Create a Stripe invoice item for the Stripe fee
    invoice_item = stripe.InvoiceItem.create(
        customer=customer_id,
        price=stripe_fee_price.id,
        currency="usd",
        description=f"Payment processing fee",
        invoice=invoice.id,
    )

    # Add additional charges to the invoice if there are any
    if additional_charges_dict:
        for charge in additional_charges_dict:
            amount = charge["amount"]
            # Check if the charge is a string; if so, convert it to a float first
            if isinstance(amount, str):
                amount = float(amount)
            charge_amount = amount
            charge_name = charge["name"]
            charge_product_name = f"{charge_name} for unit {unit.name} at {unit.rental_property.name}"
            
            charge_product = stripe.Product.create(
                name=charge_product_name,
                type="service",
            )
            charge_price = stripe.Price.create(
                unit_amount=int(charge_amount * 100),
                currency="usd",
                product=charge_product.id,
            )
            invoice_item = stripe.InvoiceItem.create(
                customer=customer_id,
                price=charge_price.id,
                currency="usd",
                description=charge_product_name,
                invoice=invoice.id,
            )

    # Finalize the invoice
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
    rent_periods = calculate_rent_periods(
        lease_start_date, rent_frequency, lease_term
    )
    lease_terms = json.loads(unit.lease_terms)
    combined_payments = next(
        (item for item in lease_terms if item["name"] == "combine_payments"),
        None,
    )
    grace_period_days = 0  # Assuming a 5-day grace period; adjust as needed
    if combined_payments["value"] == "combined":
        due_date = lease_start_date + relativedelta(days=+grace_period_days)

        # Set time part of due_date to end of the day
        due_date_end_of_day = datetime.combine(due_date, time.max)

        # Ensure due_date is in the future
        current_time = datetime.now()
        if due_date_end_of_day <= current_time:
            due_date_end_of_day = current_time + relativedelta(days=1)  # Adjust as needed to ensure it's in the future

        # Create Stripe Invoice for the specified rent payment period
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=True,
            collection_method="send_invoice",
            due_date=int(due_date_end_of_day.timestamp()),
            metadata={
                "type": "rent_payment",
                "description": "Rent payment",
                "tenant_id": unit.tenant.id,
                "owner_id": unit.owner.id,
                "rental_property_id": unit.rental_property.id,
                "rental_unit_id": unit.id,
                "lease_agreement_id": lease_agreement.id, #TODO: Add lease agreement to metadata
            },
            transfer_data={"destination": unit.owner.stripe_account_id},
        )

        # Create a Stripe price for the rent amount
        price = stripe.Price.create(
            unit_amount=int(rent_amount * 100),
            currency="usd",
            product_data={
                "name": f"Rent for unit {unit.name} at {unit.rental_property.name}"
            },
        )

        for period_start, period_end in rent_periods:
            # format the period start and end dates to a more human readable format
            formatted_period_start = period_start.strftime("%m/%d/%Y")
            invoice_item = stripe.InvoiceItem.create(
                customer=customer_id,
                price=price.id,
                currency="usd",
                description=f"Rent payment for {formatted_period_start}",
                invoice=invoice.id,
            )

            # Add additional charges to the invoice if there are any
            if additional_charges_dict:
                for charge in additional_charges_dict:
                    charge_amount = int(charge["amount"])
                    charge_name = charge["name"]
                    charge_product_name = f"{charge_name} for unit {unit.name} at {unit.rental_property.name}"

                    charge_product = stripe.Product.create(
                        name=charge_product_name,
                        type="service",
                    )
                    charge_price = stripe.Price.create(
                        unit_amount=int(charge_amount * 100),
                        currency="usd",
                        product=charge_product.id,
                    )
                    invoice_item = stripe.InvoiceItem.create(
                        customer=customer_id,
                        price=charge_price.id,
                        currency="usd",
                        description=charge_product_name,
                        invoice=invoice.id,
                    )

        # Finalize the invoice
        stripe.Invoice.finalize_invoice(invoice.id)

    else:
        for period_start, period_end in rent_periods:
            # Assuming the due date is at the start of the period plus a grace period
            due_date = period_start + relativedelta(days=+grace_period_days)
            
            # Make due_date timezone-aware if it isn't already
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            
            # Ensure due_date is in the future
            current_time = datetime.now(timezone.utc)
            if due_date <= current_time:
                due_date = current_time + relativedelta(days=1)  # Adjust as needed to ensure it's in the future
            
            # Create Stripe invoice for each rent payment period
            create_invoice_for_period(
                period_start,
                rent_amount,
                customer_id,
                due_date,
                unit,
                additional_charges_dict,
                lease_agreement
            )
    
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

