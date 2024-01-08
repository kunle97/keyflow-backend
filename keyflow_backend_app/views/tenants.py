from operator import is_
import os
from dotenv import load_dotenv
from datetime import timedelta, timezone, datetime
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 

from keyflow_backend_app.models.account_type import Tenant
from ..models.notification import Notification
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from ..models.transaction import Transaction
from ..models.rental_application import RentalApplication
from ..models.account_activation_token import AccountActivationToken
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.lease_agreement_serializer import LeaseAgreementSerializer
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import stripe

load_dotenv()


class TenantVerificationView(APIView):
    # Create a function that verifies the lease agreement id and approval hash
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        lease_agreement_id = request.data.get("lease_agreement_id")

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        # check if the approval hash is valid with the lease agreement
        if lease_agreement.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # return a response for the lease being signed successfully
        return Response(
            {"message": "Approval hash valid.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


class OldTenantViewSet(viewsets.ModelViewSet):
    # ... (existing code)
    @action(detail=True, methods=["post"], url_path="make-payment")
    @authentication_classes([TokenAuthentication, SessionAuthentication])
    def make_payment_intent(self, request, pk=None):
        data = request.data.copy()
        user_id = request.data.get("user_id")  # retrieve user id from the request
        tenant = User.objects.get(id=user_id)  # retrieve the user object
        unit = RentalUnit.objects.get(tenant=tenant)  # retrieve the unit object
        landlord = unit.owner  # Retrieve landlord object from unit object
        lease_template = (
            unit.lease_template
        )  # Retrieve lease term object from unit object
        amount = lease_template.rent  # retrieve the amount from the lease term object

        # Call Stripe API to create a payment
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            payment_method_types=["card"],
            customer=tenant.stripe_customer_id,
            payment_method=data["payment_method_id"],
            transfer_data={
                "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
            },
            confirm=True,
        )

        # create a transaction object
        transaction = Transaction.objects.create(
            type="rent_payment",
            description=f"{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name} for landlord {landlord.first_name} {landlord.last_name}",
            rental_property=unit.rental_property,
            rental_unit=unit,
            user=landlord.user,
            tenant=tenant,
            amount=amount,
            payment_method_id=data["payment_method_id"],
            payment_intent_id=payment_intent.id,
        )

        # Create a notification for the landlord that the tenant has paid the rent
        notification = Notification.objects.create(
            user=landlord.user,
            message=f"{tenant.first_name} {tenant.last_name} has paid rent for the amount of ${amount} for unit {unit.name} at {unit.rental_property.name}",
            type="rent_paid",
            title="Rent Paid",
            resource_url=f"/dashboard/landlord/transactions/{transaction.id}",
        )

        # serialize transaction object and return it
        serializer = TransactionSerializer(transaction)
        transaction_data = serializer.data

        return Response(
            {
                "payment_intent": payment_intent,
                "transaction": transaction_data,
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )


class RetrieveTenantDashboardData(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(user=user)
        lease_agreement = LeaseAgreement.objects.get(tenant=tenant, is_active=True)
        unit = lease_agreement.rental_unit
        lease_template = unit.lease_template

        unit_serializer = RentalUnitSerializer(unit)
        lease_template_serializer = LeaseTemplateSerializer(lease_template)
        lease_agreement_serializer = LeaseAgreementSerializer(lease_agreement)

        unit_data = unit_serializer.data
        lease_template_data = lease_template_serializer.data
        lease_agreement_data = lease_agreement_serializer.data

        return Response(
            {
                "unit": unit_data,
                "lease_template": lease_template_data,
                "lease_agreement": lease_agreement_data,
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )


# Create an endpoint that registers a tenant
class TenantRegistrationView(APIView):
    def post(self, request):
        data = request.data.copy()

        # Hash the password before saving the user
        data["password"] = make_password(data["password"])

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            tenant_user = User.objects.get(email=data["email"])
            
            # Initialize unit here to get the larndlord object
            unit_id = data["unit_id"]
            unit = RentalUnit.objects.get(id=unit_id)

            # retrieve landlord from the unit
            landlord = unit.owner

            # set the account type to tenant
            tenant_user.account_type = "tenant"
            # Create a stripe customer id for the user
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            customer = stripe.Customer.create(
                email=tenant_user.email,
                metadata={
                    "landlord_id": landlord.id,
                },
            )
            

            tenant_user.is_active = False
            tenant_user.save()

            tenant = Tenant.objects.create(  
                user=tenant_user,
                stripe_customer_id=customer.id,
                owner=landlord,
            )

            # Create a notification for the landlord that a tenant has been added
            notification = Notification.objects.create(
                user=landlord.user,
                message=f"{tenant_user.first_name} {tenant_user.last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                type="tenant_registered",
                title="Tenant Registered",
                resource_url=f"/dashboard/landlord/tenants/{tenant_user.id}",
            )

            # Retrieve unit from the request unit_id parameter

            unit.tenant = tenant
            unit.save()

            # Retrieve lease agreement from the request lease_agreement_id parameter
            lease_agreement_id = data["lease_agreement_id"]
            lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
            lease_agreement.tenant = tenant
            lease_agreement.save()

            # Retrieve rental application from the request approval_hash parameter
            approval_hash = data["approval_hash"]
            rental_application = RentalApplication.objects.get(
                approval_hash=approval_hash
            )
            rental_application.tenant = tenant
            rental_application.save()

            # Retrieve price id from lease term using lease_agreement
            lease_template = unit.lease_template

            # Attach payment method to the customer adn make it default
            payment_method_id = data["payment_method_id"]
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            landlord = unit.owner
            landlord_user = landlord.user
            # TODO: implement secutrity deposit flow here. Ensure subsicption is sety to a trial period of 30 days and then charge the security deposit immeediatly
            if lease_template.security_deposit > 0:
                # Retrieve landlord from the unit
                security_deposit_payment_intent = stripe.PaymentIntent.create(
                    amount=int(lease_template.security_deposit * 100),
                    currency="usd",
                    payment_method_types=["card"],
                    customer=customer.id,
                    payment_method=data["payment_method_id"],
                    transfer_data={
                        "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
                    },
                    confirm=True,
                    # Add Metadata to the transaction signifying that it is a security deposit
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": landlord_user.id,
                        "tenant_id": tenant.id,
                        "landlord_id": landlord.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )

                # create a transaction object for the security deposit
                security_deposit_transaction = Transaction.objects.create(
                    type="security_deposit",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    user=landlord_user,
                    tenant=tenant_user,
                    amount=int(lease_template.security_deposit),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id=security_deposit_payment_intent.id,
                )
                # Create a notification for the landlord that the security deposit has been paid
                notification = Notification.objects.create(
                    user=landlord_user,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the security deposit for the amount of ${lease_template.security_deposit} for unit {unit.name} at {unit.rental_property.name}",
                    type="security_deposit_paid",
                    title="Security Deposit Paid",
                    resource_url=f"/dashboard/landlord/transactions/{security_deposit_transaction.id}",
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
                    default_payment_method=payment_method_id,
                    trial_end=grace_period_end,
                    transfer_data={
                        "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
                    },
                    # Cancel the subscription after at the end date specified by lease term
                    cancel_at=int(
                        datetime.fromisoformat(
                            f"{lease_agreement.end_date}"
                        ).timestamp()
                    ),
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant_user.id,
                        "landlord_id": landlord.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
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
                    transfer_data={
                        "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
                    },
                    cancel_at=int(
                        datetime.fromisoformat(
                            f"{lease_agreement.end_date}"
                        ).timestamp()
                    ),
                    default_payment_method=payment_method_id,
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant.id,
                        "landlord_id": landlord.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )

                # create a transaction object for the rent payment (stripe subscription)
                subscription_transaction = Transaction.objects.create(
                    type="rent_payment",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    user=landlord,
                    tenant=tenant_user,
                    amount=int(lease_template.rent),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id="subscription",
                )
                # Create a notification for the landlord that the tenant has paid the fisrt month's rent
                notification = Notification.objects.create(
                    user=landlord,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the first month's rent for the amount of ${lease_template.rent} for unit {unit.name} at {unit.rental_property.name}",
                    type="first_month_rent_paid",
                    title="First Month's Rent Paid",
                    resource_url=f"/dashboard/landlord/transactions/{subscription_transaction.id}",
                )
            # add subscription id to the lease agreement
            lease_agreement.stripe_subscription_id = subscription.id
            lease_agreement.save()
            account_activation_token = AccountActivationToken.objects.create(
                user=tenant_user,
                email=tenant_user.email,
                token=data["activation_token"],
            )
            return Response(
                {
                    "message": "Tenant registered successfully.",
                    "user": serializer.data,
                    "isAuthenticated": True,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
