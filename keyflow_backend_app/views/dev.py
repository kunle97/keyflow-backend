import os
import hashlib
import stripe
import random
from dotenv import load_dotenv
from datetime import datetime, date, timezone, timedelta
from dateutil.relativedelta import relativedelta
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from django.contrib.auth.hashers import make_password
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from ..models.user import User
from faker import Faker
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.notification import Notification
from ..models.lease_template import LeaseTemplate
from ..models.lease_agreement import LeaseAgreement
from ..models.rental_application import RentalApplication
from ..models.transaction import Transaction
from ..models.lease_template import LeaseTemplate
from ..models.message import Message
from ..models.maintenance_request import MaintenanceRequest
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from ..models.lease_renewal_request import LeaseRenewalRequest
from ..helpers import make_id, strtobool
from django.views.decorators.csrf import csrf_exempt



faker = Faker()
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")

# ----------TEST FUNCTIONS ----------------


# test to see if tooken is valid and return user info
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
def test_token(request):
    return Response("passed for {}".format(request.user.username))


# Create a function to retrieve all landlord userss emails
@api_view(["GET"])
# @authentication_classes([JWTAuthentication])
def get_landlord_emails(request):
    # Retrieve all landlord users
    landlords = User.objects.filter(account_type="landlord").order_by("-id")
    # Create a list of landlord emails
    landlord_emails = []
    for landlord in landlords:
        landlord_emails.append(landlord.email)
    # Return a response
    return Response(landlord_emails, status=status.HTTP_200_OK)


# Create a function to retrieve all landlord userss usernames
@api_view(["GET"])
def get_landlord_usernames(request):
    # Retrieve all landlord users
    landlords = User.objects.filter(account_type="landlord").order_by("-id")
    # Create a list of landlord usernames
    landlord_usernames = []
    for landlord in landlords:
        landlord_usernames.append(landlord.username)
    # Return a response
    return Response(landlord_usernames, status=status.HTTP_200_OK)


@api_view(["POST"])

# Create a function to retrieve all tenant userss emails
@api_view(["GET"])
def get_tenant_emails(request):
    # Retrieve all tenant users
    tenants = User.objects.filter(account_type="tenant")
    # Create a list of tenant emails
    tenant_emails = []
    for tenant in tenants:
        tenant_emails.append(tenant.email)
    # Return a response
    return Response(tenant_emails, status=status.HTTP_200_OK)


# Create a function to retrieve all tenant userss usernames
@api_view(["GET"])
def get_tenant_usernames(request):
    # Retrieve all tenant users
    tenants = User.objects.filter(account_type="tenant")
    # Create a list of tenant usernames
    tenant_usernames = []
    for tenant in tenants:
        tenant_usernames.append(tenant.username)
    # Return a response
    return Response(tenant_usernames, status=status.HTTP_200_OK)


# -------------DEV TOOL FUNCTIONS----------------
@csrf_exempt
@api_view(["POST"])
def generate_properties(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    user_id = request.data.get("user_id")

    # create a entries for properties with faker data with count number in a loop
    while int_count > 0:
        RentalProperty.objects.create(
            name=faker.company(),
            street=faker.street_address(),
            city=faker.city(),
            state=faker.state(),
            zip_code=faker.postcode(),
            country="Unites States",
            user=User.objects.get(id=user_id),
        )
        int_count -= 1
    # Return a response
    return Response(
        {"message": "Properties generated", "status": status.HTTP_201_CREATED},
        status=status.HTTP_200_OK,
    )


@csrf_exempt
@api_view(["POST"])
def generate_units(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    data = request.data.copy()
    user_id = data["user_id"]
    rental_property_id = data["rental_property"]
    subscription_id = data["subscription_id"]
    product_id = data["product_id"]

    # Retrieve all of the landlord's properties
    properties = RentalProperty.objects.filter(user_id=user_id)
    # retrieve user
    user = User.objects.get(id=user_id)

    stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
    subscription = stripe.Subscription.retrieve(
        subscription_id,  # Retrieve the subscription from stripe
    )

    # If user has the premium plan, check to see if they have 10 or less units
    if product_id == os.getenv("STRIPE_STANDARD_PLAN_PRODUCT_ID"):
        if (
            RentalUnit.objects.filter(user=user).count() >= 10
            or int_count > 10
            or int_count + RentalUnit.objects.filter(user=user).count() > 10
        ):
            return Response(
                {
                    "message": "You have reached the maximum number of units for your subscription plan. Please upgrade to a higher plan."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    # If user has the pro plan, increase the metered usage for the user based on the new number of units
    if product_id == os.getenv("STRIPE_PRO_PLAN_PRODUCT_ID"):
        # Update the subscriptions quantity to the new number of units
        subscription_item = stripe.SubscriptionItem.modify(
            subscription["items"]["data"][0].id,
            quantity=RentalUnit.objects.filter(user=user).count() + int_count,
        )
    while int_count > 0:
        # if rental_property_id is None Choose a random property
        if rental_property_id is None:
            property = properties.order_by("?").first()  # random property
        else:
            property = properties.get(id=rental_property_id)
        # Create a rental unit for the property
        RentalUnit.objects.create(
            name=faker.bothify(
                text="?#"
            ),  # Generate a 2 charachter string that the first character is a random letter and the 2nd character is a random number  using faker
            rental_property=property,
            beds=faker.pyint(min_value=1, max_value=5),
            baths=faker.pyint(min_value=1, max_value=5),
            user=user,
            size=faker.pyint(min_value=500, max_value=5000),
        )
        int_count -= 1
    # Return a response
    return Response(
        {"message": "Units created", "status": status.HTTP_201_CREATED},
        status=status.HTTP_200_OK,
    )


# Create a function that generates a number of tenants bas e don the count variable from the request
@csrf_exempt
@api_view(["POST"])
def generate_tenants(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)  # retrieve user (landlord) making the request
    unit_mode = request.data.get(
        "unit_mode"
    )  # Values are 'new', 'random' or 'specific'
    rental_unit_id = request.data.get(
        "rental_unit_id"
    )  # If unit_mode is 'specific' then this is the rental unit id
    lease_template_mode = request.data.get(
        "lease_template_mode"
    )  # Values are 'new', 'random' or 'specific'
    lease_template_id = request.data.get(
        "lease_template_id"
    )  # If lease_template_mode is 'specific' then this is the lease term id
    rental_application_is_approved = request.data.get(
        "rental_application_is_approved", False
    )  # Values are 'True' or 'False'
    rental_application_is_archived = request.data.get(
        "rental_application_is_archived", False
    )  # Values are 'True' or 'False'
    has_grace_period = request.data.get(
        "has_grace_period"
    )  # Values are 'True' or 'False'
    create_rental_application = request.data.get(
        "create_rental_application", False
    )  # Values are 'True' or 'False'

    tenant = None
    lease_agreement = None
    subscription = None
    # Retrieve all of the landlord's properties
    properties = RentalProperty.objects.filter(user_id=user_id)

    # create a entries for tenants with faker data with count number in a loop
    while int_count > 0:
        unit = None
        first_name = faker.first_name()
        last_name = faker.last_name()
        # Create a username from the first and last name and random number
        username = (
            first_name + last_name + str(faker.pyint(min_value=1, max_value=1000))
        )
        # Create an email from the username
        email = username + "@gmail.com"
        password = make_password("Password1")
        account_type = "tenant"
        customer = stripe.Customer.create(
            email=email,
            metadata={
                "landlord_id": user.id,
            },
        )
        # retrieve current landlord users subscriprion
        subscription = stripe.Subscription.retrieve(
            user.stripe_subscription_id,  # Retrieve the subscription from stripe
        )
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2034,
                "cvc": "314",
            },
        )

        # attach the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method.id,
            customer=customer.id,
        )

        stripe_customer_id = customer.id

        # Create a tenant for the property
        tenant = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=password,
            account_type=account_type,
            stripe_customer_id=stripe_customer_id,
        )

        # ---------LEASE Template GENEREATION LOGIC----------------

        lease_template = None
        if has_grace_period:
            grace_period = faker.pyint(min_value=1, max_value=5)
        else:
            grace_period = 0

        # if lease_template_mode is 'new' create a new lease template for the tenant
        if lease_template_mode == "new":
            rent = faker.pyint(min_value=500, max_value=5000)
            term = faker.pyint(min_value=6, max_value=12)
            late_fee = faker.pyint(min_value=50, max_value=500)
            security_deposit = faker.pyint(min_value=500, max_value=5000)
            gas_included = faker.pybool()
            water_included = faker.pybool()
            electric_included = faker.pybool()
            repairs_included = faker.pybool()
            grace_period = grace_period
            lease_cancellation_notice_period = faker.pyint(min_value=1, max_value=10)
            lease_cancellation_fee = faker.pyint(min_value=500, max_value=5000)
            description = faker.text(max_nb_chars=200)
            # Create a lease term for the tenant
            lease_template = LeaseTemplate.objects.create(
                start_date=faker.date_between(start_date="-1y", end_date="today"),
                end_date=faker.date_between(start_date="today", end_date="+1y"),
                term=term,
                rent=rent,
                user=user,
                template_id="a6d7a4b5-bb38-4d92-a6c9-90e76e7a96ce",
                description=description,
                late_fee=late_fee,
                security_deposit=security_deposit,
                gas_included=gas_included,
                water_included=water_included,
                electric_included=electric_included,
                repairs_included=repairs_included,
                grace_period=grace_period,
                lease_cancellation_notice_period=lease_cancellation_notice_period,
                lease_cancellation_fee=lease_cancellation_fee,
            )
            # Create a stripe product for the lease term
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            product = stripe.Product.create(
                name=f"{user.first_name} {user.last_name}'s (User ID: {user.id}) {term} month lease @ ${rent}/month. Lease Term ID: {lease_template.id}",
                type="service",
                metadata={
                    "seller_id": user.stripe_account_id
                },  # Associate the product with the connected account
            )

            # Create a stripe price for the lease term
            price = stripe.Price.create(
                unit_amount=rent * 100,
                recurring={"interval": "month"},
                currency="usd",
                product=product.id,
            )

            # update the lease term object with the stripe product and price ids
            lease_template.stripe_product_id = product.id
            lease_template.stripe_price_id = price.id
            lease_template.save()
        # else if lease_template_mode is 'random' choose a random lease term for the tenant
        elif lease_template_mode == "random":
            # Choose a random lease term
            lease_template = LeaseTemplate.objects.order_by("?").first()
        # else if lease_template_mode is 'specific' assign the tenant to the specific lease term
        elif lease_template_mode == "specific":
            # Retrieve the lease term
            lease_template = LeaseTemplate.objects.get(id=lease_template_id)

        # ---------UNIT GENEREATION LOGIC----------------
        # if unit_mode is 'new' create a new unit for the tenant
        if unit_mode == "new":
            # Choose a random property
            property = properties.order_by("?").first()
            unit = RentalUnit.objects.create(
                name=faker.bothify(
                    text="?#"
                ),  # Generate a 2 charachter string that the first character is a random letter and the 2nd character is a random number  using faker
                rental_property=property,
                beds=faker.pyint(min_value=1, max_value=5),
                baths=faker.pyint(min_value=1, max_value=5),
                user=user,
                tenant=tenant,
                is_occupied=True,
                lease_template=lease_template,
            )

            # Update the subscriptions quantity to the new number of units
            subscription_item = stripe.SubscriptionItem.modify(
                subscription["items"]["data"][0].id,
                quantity=RentalUnit.objects.filter(user=user).count(),
            )
            # Create a notification for the landlord that a tenant has been added
            notification = Notification.objects.create(
                user=user,
                message=f"{first_name} {last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                type="tenant_registered",
                title="Tenant Registered",
            )
        # else if unit_mode is 'random' choose a random unoccumpued unit for the tenant
        elif unit_mode == "random":
            # Choose a random property
            property = properties.order_by("?").first()

            # Choose a random unoccupied unit
            unit = (
                RentalUnit.objects.filter(is_occupied=False, user=user)
                .order_by("?")
                .first()
            )
            # Assign the tenant to the unit
            unit.tenant = tenant
            unit.is_occupied = True
            unit.lease_template = lease_template
            unit.save()
            # Create a notification for the landlord that a tenant has been added
            notification = Notification.objects.create(
                user=user,
                message=f"{first_name} {last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                type="tenant_registered",
                title="Tenant Registered",
            )
        # else if unit_mode is 'specific' assign the tenant to the specific unit
        elif unit_mode == "specific":
            # Retrieve the unit
            unit = RentalUnit.objects.get(id=rental_unit_id)
            # Assign the tenant to the unit
            unit.tenant = tenant
            unit.lease_template = lease_template
            unit.is_occupied = True
            unit.save()
            # Create a notification for the landlord that a tenant has been added
            notification = Notification.objects.create(
                user=user,
                message=f"{first_name} {last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                type="tenant_registered",
                title="Tenant Registered",
            )

        # Get the current date
        current_date = date.today()

        # Define a future date range
        start_date = current_date
        end_date = current_date.replace(
            year=current_date.year + 1
        )  # One year in the future
        rental_application = None
        # Create a random hash string that ius at most 100 characters
        if create_rental_application:
            rental_application = RentalApplication.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                date_of_birth=faker.date_of_birth(
                    minimum_age=18, maximum_age=65
                ).strftime("%Y-%m-%d"),
                phone_number="1235557624",
                desired_move_in_date=faker.date_between(
                    start_date=start_date, end_date=end_date
                ).strftime("%Y-%m-%d"),
                unit=unit,
                approval_hash=make_id(64),
                other_occupants=faker.pybool(),
                pets=faker.pybool(),
                vehicles=faker.pybool(),
                convicted=faker.pybool(),
                bankrupcy_filed=faker.pybool(),
                evicted=faker.pybool(),
                employment_history=faker.text(max_nb_chars=200),
                residential_history=faker.text(max_nb_chars=200),
                comments=faker.text(max_nb_chars=200),
                is_approved=rental_application_is_approved,
                is_archived=rental_application_is_archived,
                landlord=user,
            )

        # Create a notification for the landlord that a new rental application has been submitted
        notification = Notification.objects.create(
            user=unit.user,
            message=f"{first_name} {last_name} has submitted a rental application for unit {unit.name} at {unit.rental_property.name}",
            type="rental_application_submitted",
            title="Rental Application Submitted",
        )

        # Define the number of months to add
        months_to_add = lease_template.term

        # Calculate the new date by adding months
        end_date = current_date + relativedelta(months=+months_to_add)
        # Create a lease agreement for the tenant
        lease_agreement = LeaseAgreement.objects.create(
            lease_template=lease_template,
            tenant=tenant,
            user=user,
            rental_unit=unit,
            approval_hash=faker.sha256(raw_output=False),
            start_date=current_date,
            end_date=end_date,
            document_id="",
            signed_date=current_date,
            is_active=True,
            auto_pay_is_enabled=True,
        )

        ##Security Deposit Payment
        landlord = unit.user
        if lease_template.security_deposit > 0:
            # Retrieve landlord from the unit
            security_deposit_payment_intent = stripe.PaymentIntent.create(
                amount=int(lease_template.security_deposit * 100),
                currency="usd",
                payment_method_types=["card"],
                customer=customer.id,
                payment_method=payment_method.id,
                transfer_data={
                    "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
                },
                confirm=True,
                # Add Metadata to the transaction signifying that it is a security deposit
                metadata={
                    "type": "revenue",
                    "description": f"{tenant.first_name} {tenant.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    "user_id": user.id,
                    "tenant_id": tenant.id,
                    "landlord_id": landlord.id,
                    "rental_property_id": unit.rental_property.id,
                    "rental_unit_id": unit.id,
                    "payment_method_id": payment_method.id,
                },
            )

            # create a transaction object for the security deposit
            security_deposit_transaction = Transaction.objects.create(
                type="revenue",
                description=f"{tenant.first_name} {tenant.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                rental_property=unit.rental_property,
                rental_unit=unit,
                user=landlord,
                tenant=user,
                amount=int(lease_template.security_deposit),
                payment_method_id=payment_method.id,
                payment_intent_id=security_deposit_payment_intent.id,
            )
            # Create a notification for the landlord that the security deposit has been paid
            notification = Notification.objects.create(
                user=landlord,
                message=f"{tenant.first_name} {tenant.last_name} has paid the security deposit for the amount of ${lease_template.security_deposit} for unit {unit.name} at {unit.rental_property.name}",
                type="security_deposit_paid",
                title="Security Deposit Paid",
            )

        subscription = None
        if lease_template.grace_period != 0:
            # Convert the ISO date string to a datetime object
            start_date = datetime.fromisoformat(f"{lease_agreement.start_date}")

            # Number of months to add
            months_to_add = lease_template.grace_period

            # Calculate the end date by adding months
            end_date = start_date + relativedelta(months=months_to_add)

            # Convert the end date to a Unix timestamp
            grace_period_end = int(end_date.timestamp())
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": lease_template.stripe_price_id},
                ],
                default_payment_method=payment_method.id,
                trial_end=grace_period_end,
                transfer_data={
                    "destination": user.stripe_account_id  # The Stripe Connected Account ID
                },
                # Cancel the subscription after at the end date specified by lease term
                cancel_at=int(
                    datetime.fromisoformat(f"{lease_agreement.end_date}").timestamp()
                ),
                metadata={
                    "type": "revenue",
                    "description": f"{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                    "user_id": user.id,
                    "tenant_id": user.id,
                    "landlord_id": user.id,
                    "rental_property_id": unit.rental_property.id,
                    "rental_unit_id": unit.id,
                    "payment_method_id": payment_method.id,
                },
            )
        else:
            grace_period_end = lease_agreement.start_date
            # Create a stripe subscription for the user and make a default payment method
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": lease_template.stripe_price_id},
                ],
                default_payment_method=payment_method.id,
                transfer_data={
                    "destination": user.stripe_account_id  # The Stripe Connected Account ID
                },
                cancel_at=int(
                    datetime.fromisoformat(f"{lease_agreement.end_date}").timestamp()
                ),
                metadata={
                    "type": "revenue",
                    "description": f"{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                    "user_id": user.id,
                    "tenant_id": user.id,
                    "landlord_id": user.id,
                    "rental_property_id": unit.rental_property.id,
                    "rental_unit_id": unit.id,
                    "payment_method_id": payment_method.id,
                },
            )
            # create a transaction object for the rent payment (stripe subscription)
            subscription_transaction = Transaction.objects.create(
                type="revenue",
                description=f"{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                rental_property=unit.rental_property,
                rental_unit=unit,
                user=user,
                tenant=tenant,
                amount=int(lease_template.rent),
                payment_method_id=payment_method.id,
                payment_intent_id="subscription",
            )
            # Create a notification for the landlord that the tenant has paid the fisrt month's rent
            notification = Notification.objects.create(
                user=user,
                message=f"{tenant.first_name} {tenant.last_name} has paid the first month's rent for the amount of ${lease_template.rent} for unit {unit.name} at {unit.rental_property.name}",
                type="first_month_rent_paid",
                title="First Month's Rent Paid",
            )

            print(f"subscription: {subscription}")
            print(f"lease_agreement: {lease_agreement}")

        # add subscription id to the lease agreement
        lease_agreement.stripe_subscription_id = subscription.id
        if rental_application:
            lease_agreement.rental_application = rental_application
        lease_agreement.save()

        int_count -= 1
    # Return a response
    return Response(
        {"message": "Tenants created", "status": status.HTTP_201_CREATED},
        status=status.HTTP_200_OK,
    )


# Create a function called lease_template_generator that generates a number of lease terms based on the count variable from the request for the requested user
@csrf_exempt
@api_view(["POST"])
def generate_lease_templates(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)

    # create a entries for lease terms with faker data with count number in a loop
    while int_count > 0:
        rent = faker.pyint(min_value=500, max_value=10000)
        term = faker.pyint(min_value=6, max_value=12)
        late_fee = faker.pyint(min_value=50, max_value=500)
        security_deposit = faker.pyint(min_value=500, max_value=5000)
        gas_included = faker.pybool()
        water_included = faker.pybool()
        electric_included = faker.pybool()
        repairs_included = faker.pybool()
        grace_period = faker.pyint(min_value=1, max_value=5)
        lease_cancellation_notice_period = faker.pyint(min_value=1, max_value=10)
        lease_cancellation_fee = faker.pyint(min_value=500, max_value=5000)
        description = faker.text(max_nb_chars=200)
        # Create a lease term for the tenant
        lease_template = LeaseTemplate.objects.create(
            term=term,
            template_id="d13cb236-b3d5-4be9-9ba4-b98468f60bb2",
            rent=rent,
            user=user,
            description=description,
            late_fee=late_fee,
            security_deposit=security_deposit,
            gas_included=gas_included,
            additional_charges="[]",
            water_included=water_included,
            electric_included=electric_included,
            repairs_included=repairs_included,
            grace_period=grace_period,
            lease_cancellation_notice_period=lease_cancellation_notice_period,
            lease_cancellation_fee=lease_cancellation_fee,
        )
        # Create a stripe product for the lease term
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        product = stripe.Product.create(
            name=f"{user.first_name} {user.last_name}'s (User ID: {user.id}) {term} month lease @ ${rent}/month. Lease Term ID: {lease_template.id}",
            type="service",
            metadata={
                "seller_id": user.stripe_account_id
            },  # Associate the product with the connected account
        )

        # Create a stripe price for the lease term
        price = stripe.Price.create(
            unit_amount=rent * 100,
            recurring={"interval": "month"},
            currency="usd",
            product=product.id,
        )

        # update the lease term object with the stripe product and price ids
        lease_template.stripe_product_id = product.id
        lease_template.stripe_price_id = price.id
        lease_template.save()
        int_count -= 1
    # Return a response
    return Response(
        {"message": "Lease Terms generated", "status": status.HTTP_201_CREATED},
        status=status.HTTP_200_OK,
    )


# Create a function that generates rental applications for a tenant based on the count variable from the request and the faker library
@csrf_exempt
@api_view(["POST"])
def generate_rental_applications(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)
    unit = None
    unit_mode = request.data.get(
        "unit_mode"
    )  # Values are 'new', 'random' or 'specific'
    rental_unit_id = request.data.get(
        "rental_unit_id"
    )  # If unit_mode is 'specific' then this is the rental unit id

    # retrieve current landlord users subscriprion
    subscription = stripe.Subscription.retrieve(
        user.stripe_subscription_id,  # Retrieve the subscription from stripe
    )
    # Choose a random property
    property = RentalProperty.objects.all().order_by("?").first()
    # retrieve current landlord users subscriprion
    subscription = stripe.Subscription.retrieve(
        user.stripe_subscription_id,  # Retrieve the subscription from stripe
    )
    # ---------UNIT GENEREATION LOGIC----------------
    # if unit_mode is 'new' create a new unit for the tenant
    if unit_mode == "new":
        # Choose a random lease template
        lease_template = LeaseTemplate.objects.all().order_by("?").first()
        unit = RentalUnit.objects.create(
            name=faker.bothify(
                text="?#"
            ),  # Generate a 2 charachter string that the first character is a random letter and the 2nd character is a random number  using faker
            rental_property=property,
            beds=faker.pyint(min_value=1, max_value=5),
            baths=faker.pyint(min_value=1, max_value=5),
            user=user,
            is_occupied=False,
            lease_template=lease_template,
        )

        # Update the subscriptions quantity to the new number of units
        subscription_item = stripe.SubscriptionItem.modify(
            subscription["items"]["data"][0].id,
            quantity=RentalUnit.objects.filter(user=user).count(),
        )
    # else if unit_mode is 'random' choose a random unoccumpued unit for the tenant
    elif unit_mode == "random":
        # Find a unit where the lease_tempalte field is NOT null
        unit = (
            RentalUnit.objects.filter(
                is_occupied=False, user=user, lease_template__isnull=False
            )
            .order_by("?")
            .first()
        )
    # else if unit_mode is 'specific' assign the tenant to the specific unit
    elif unit_mode == "specific":
        # Retrieve the unit
        unit = RentalUnit.objects.get(id=rental_unit_id)

    # create a entries for rental applications with faker data with count number in a loop
    while int_count > 0:
        first_name = faker.first_name()
        last_name = faker.last_name()
        # Create a username from the first and last name and random number
        username = (
            first_name + last_name + str(faker.pyint(min_value=1, max_value=1000))
        )
        # Create an email from the username
        email = username + "@gmail.com"
        # Create a rental application for the tenant
        rental_application = RentalApplication.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            date_of_birth=faker.date_of_birth(minimum_age=18, maximum_age=65).strftime(
                "%Y-%m-%d"
            ),
            phone_number="3952032953",
            desired_move_in_date=faker.date_between(
                start_date="-1y", end_date="today"
            ).strftime("%Y-%m-%d"),
            unit=unit,
            approval_hash=make_id(64),
            other_occupants=faker.pybool(),
            pets=faker.pybool(),
            vehicles=faker.pybool(),
            convicted=faker.pybool(),
            bankrupcy_filed=faker.pybool(),
            evicted=faker.pybool(),
            employment_history="[]",
            residential_history="[]",
            comments=faker.text(max_nb_chars=200),
            is_approved=False,
            is_archived=False,
            landlord=user,
        )
        int_count -= 1
    # Return a response
    return Response(
        {"message": "Rental Applications generated", "status": status.HTTP_201_CREATED},
        status=status.HTTP_201_CREATED,
    )


# Create a function to generate a number of messages for a user
@csrf_exempt
@api_view(["POST"])
def generate_messages(request):
    count = request.data.get("count", 1)
    int_count = int(count)
    message_mode = request.data.get("message_mode")
    conversation_mode = strtobool(request.data.get("conversation_mode"))
    print("CONVO MODE", conversation_mode)
    tenant_id = request.data.get("tenant_id")
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)

    while int_count > 0:
        body = faker.text(max_nb_chars=200)
        sender = user
        recipient = None

        if message_mode == "specific":
            recipient = User.objects.get(id=tenant_id)
        elif message_mode == "random":
            # Retrieve landlord's properties
            properties = RentalProperty.objects.filter(user_id=user.id)
            # Retrieve units for each property that are occupied
            units = RentalUnit.objects.filter(
                rental_property__in=properties, is_occupied=True
            )
            # Retrieve the tenants for each unit
            tenant_ids = units.values_list("tenant__id", flat=True)
            # Filter tenants belonging to a specific user
            tenants = User.objects.filter(account_type="tenant", id__in=tenant_ids)
            recipient = tenants.order_by("?").first()

        if conversation_mode:
            # Randomly switch the sender and recipient
            if faker.pybool():
                sender = recipient
                recipient = user

        # Create a message for the user
        message = Message.objects.create(
            body=body,
            sender=sender,
            recipient=recipient,
        )
        int_count -= 1

    return Response(
        {"message": "Messages generated", "status": status.HTTP_201_CREATED},
        status=status.HTTP_201_CREATED,
    )


# Create a function to generate a number of maintenance requests for a user
@csrf_exempt
@api_view(["POST"])
def generate_maintenance_requests(request):
    count = request.data.get("count", 1)
    tenant_mode = request.data.get(
        "tenant_mode"
    )  # possible values are 'random' or 'specific'
    int_count = int(count)
    user_id = request.data.get("user_id")
    tenant_id = request.data.get("tenant_id")
    SERVICE_TYPE_CHOICES = (
        ("plumbing", "Plumbling"),
        ("electrical", "Electrical"),
        ("appliance", "Appliance"),
        ("structural", "Structural"),
        ("hvac", "HVAC"),
        ("other", "Other"),
    )
    user = User.objects.get(id=user_id)
    unit = None
    tenant = None
    type = None

    # create a entries for maintenance requests with faker data with count number in a loop
    while int_count > 0:
        description = faker.text(max_nb_chars=200)
        # If type  is 'random' choose a random type from the SERVICE_TYPE_CHOICES
        if request.data.get("type") == "random":
            type = random.choice(SERVICE_TYPE_CHOICES)[0]
        else:
            type = request.data.get("type")
        if tenant_mode == "random":
            # Retreve one of the user's tenants at randome and use them as the recipient
            # Retrieve landlord's properties
            properties = RentalProperty.objects.filter(user_id=user.id)
            # Retrieve units for each property that are occupied
            units = RentalUnit.objects.filter(
                rental_property__in=properties, is_occupied=True
            )
            # Retrieve the tenants for each unit
            tenant_ids = units.values_list("tenant__id", flat=True)
            # Filter tenants belonging to a specific user
            tenants = User.objects.filter(account_type="tenant", id__in=tenant_ids)
            tenant = tenants.order_by("?").first()
        elif tenant_mode == "specific":
            tenant = User.objects.get(id=tenant_id)

        unit = RentalUnit.objects.get(tenant=tenant)

        # Create a maintenance request for the user
        maintenance_request = MaintenanceRequest.objects.create(
            description=description,
            type=type,
            tenant=tenant,
            rental_unit=unit,
            landlord=user,
            rental_property=unit.rental_property,
        )
        int_count -= 1
    # Return a response
    return Response(
        {
            "message": "Maintenance Requests generated",
            "status": status.HTTP_201_CREATED,
        },
        status=status.HTTP_201_CREATED,
    )


# Create a function to generate lease cancellation requests for a number of tenants
@csrf_exempt
@api_view(["POST"])
def generate_lease_cancellation_requests(request):
    count = request.data.get("count", 1)
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)
    int_count = int(count)
    # Fetch all of the reqest.user's tennats by retrieveing all of thier rental units and then all of the tenants for each unit
    landlord_tenants = User.objects.filter(
        id__in=RentalUnit.objects.filter(user=user).values_list(
            "tenant__id", flat=True
        )
    )

    #find all tenants that have an active Lease agreement
    landlord_tenants = landlord_tenants.filter(
        id__in=LeaseAgreement.objects.filter(is_active=True).values_list(
            "tenant__id", flat=True
        )
    )

    #select int_count number of random tenants from the landlord's tenants
    tenants = landlord_tenants.order_by("?")[:int_count]
    # Using a while loop, create a lease cancellation request for each tenant
    while int_count > 0:
        tenant = tenants[int_count - 1]
        unit = RentalUnit.objects.filter(tenant=tenant).first()
        #fetch tenant's lease agreement from the unit
        lease_agreement = LeaseAgreement.objects.get(tenant=tenant)
        lease_cancellation_request = LeaseCancellationRequest.objects.create(
            user=unit.user,
            tenant=tenant,
            rental_unit=unit,
            rental_property=unit.rental_property,
            lease_agreement=lease_agreement,
            reason="Other",
            comments="Created using the  dev tool",
            status="pending",
            request_date=date.today(),
        )
        int_count -= 1

    # Return a response
    return Response(
        {
            "message": "Lease Cancellation Requests generated",
            "status": status.HTTP_201_CREATED,
        },
        status=status.HTTP_201_CREATED,
    )


#Create a function to generate a number of lease renewal requests for a definied number of tenants
@csrf_exempt
@api_view(["POST"])
def generate_lease_renewal_requests(request):
    count = request.data.get("count", 1)
    user_id = request.data.get("user_id")
    user = User.objects.get(id=user_id)
    int_count = int(count)
    # Fetch all of the reqest.user's tennats by retrieveing all of thier rental units and then all of the tenants for each unit
    landlord_tenants = User.objects.filter(
        id__in=RentalUnit.objects.filter(user=user).values_list(
            "tenant__id", flat=True
        )
    )

    #find all tenants that have an active Lease agreement
    landlord_tenants = landlord_tenants.filter(
        id__in=LeaseAgreement.objects.filter(is_active=True).values_list(
            "tenant__id", flat=True
        )
    )

    #select int_count number of random tenants from the landlord's tenants
    tenants = landlord_tenants.order_by("?")[:int_count]
    # Using a while loop, create a lease renewal request for each tenant
    while int_count > 0:
        tenant = tenants[int_count - 1]
        unit = RentalUnit.objects.filter(tenant=tenant).first()

        #fetch tenant's lease agreement from the unit
        lease_agreement = LeaseAgreement.objects.filter(tenant=tenant, is_active=True).first()
        #Create a move_in_date variable whose value is a date that is a random mumber of day after the lease agreement's end date
        move_in_date = lease_agreement.end_date + timedelta(
            days=random.randint(1, 30)
        )
        lease_renewal_request = LeaseRenewalRequest.objects.create(
            user=unit.user,
            tenant=tenant,
            rental_unit=unit,
            rental_property=unit.rental_property,
            move_in_date=move_in_date,
            comments="Created using the  dev tool",
            status="pending",
            request_date=date.today(),
            request_term=request.data.get("request_term"),
        )
        int_count -= 1

    # Return a response
    return Response(
        {
            "message": "Lease Renewal Requests generated",
            "status": status.HTTP_201_CREATED,
        },
        status=status.HTTP_201_CREATED,
    )
