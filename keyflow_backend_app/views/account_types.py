# Standard library imports
import json
import os
from datetime import timedelta, datetime, time
from dotenv import load_dotenv
# Third-party library imports
from pkg_resources import require
import stripe
from postmarker.core import PostmarkClient
from dateutil.relativedelta import relativedelta
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

# Model imports
from keyflow_backend_app.helpers import calculate_final_price_in_cents
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.models.notification import Notification
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.account_type import Owner, Staff, Tenant
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.maintenance_request import MaintenanceRequest
from keyflow_backend_app.models.transaction import Transaction
from keyflow_backend_app.models.rental_application import RentalApplication
from keyflow_backend_app.models.account_activation_token import AccountActivationToken

# Serializer imports
from keyflow_backend_app.serializers.lease_agreement_serializer import (
    LeaseAgreementSerializer,
)
from keyflow_backend_app.serializers.user_serializer import UserSerializer
from keyflow_backend_app.serializers.rental_property_serializer import (
    RentalPropertySerializer,
)
from keyflow_backend_app.serializers.rental_unit_serializer import RentalUnitSerializer
from keyflow_backend_app.serializers.maintenance_request_serializer import (
    MaintenanceRequestSerializer,
)
from keyflow_backend_app.serializers.transaction_serializer import TransactionSerializer
from keyflow_backend_app.serializers.account_type_serializer import (
    OwnerSerializer,
    StaffSerializer,
    TenantSerializer,
)

load_dotenv()


class OwnerViewSet(viewsets.ModelViewSet):
    queryset = Owner.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = OwnerSerializer

    # Replaces the UserREgistrationView(endpoint api/auth/register/)
    @action(
        detail=False, methods=["post"], url_path="register"
    )  # New url path for the register endpoint: api/owners/register
    def register(self, request):
        User = get_user_model()
        data = request.data.copy()
        # Hash the password before saving the user
        data["password"] = make_password(data["password"])

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=data["email"])

            # TODO: send email to the user to verify their email address
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")

            # create stripe account for the user
            stripe_account = stripe.Account.create(
                type="express",
                country="US",
                email=user.email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                    "bank_transfer_payments": {"requested": True},
                },
            )

            # Create a customer id for the user
            customer = stripe.Customer.create(email=user.email)

            # attach payment method to the customer adn make it default
            payment_method_id = data["payment_method_id"]
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            # Subscribe owner to thier selected plan using product id and price id
            product_id = data["product_id"]
            price_id = data["price_id"]
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": price_id},
                ],
                default_payment_method=payment_method_id,
                metadata={
                    "type": "revenue",
                    "description": f"{user.first_name} {user.last_name} Owner Subscrtiption",
                    "product_id": product_id,
                    "user_id": user.id,
                    "tenant_id": user.id,
                    "payment_method_id": payment_method_id,
                },
            )
            client_hostname = os.getenv("CLIENT_HOSTNAME")
            refresh_url = f"{client_hostname}/dashboard/owner/login"
            return_url = f"{client_hostname}/dashboard/activate-account/"
            # obtain stripe account link for the user to complete the onboarding process
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type="account_onboarding",
            )
            user.is_active = (
                False  # TODO: Remove this for activation flow implementation
            )
            user.save()
            
            Owner.objects.create(
                user=user,
                stripe_account_id=stripe_account.id,
                stripe_customer_id=customer.id,
                stripe_subscription_id=subscription.id,
            )

            # Create an account activation token for the user
            account_activation_token = AccountActivationToken.objects.create(
                user=user,
                email=user.email,
                token=data["activation_token"],
            )

            if os.getenv("ENVIRONMENT") == "production":
                #Send Activation Email
                postmark = PostmarkClient(server_token=os.getenv('POSTMARK_SERVER_TOKEN'))
                activation_link = f'{client_hostname}/dashboard/activate-user-account/{account_activation_token.token}'
                postmark.emails.send(
                    From="info@keyflow.co",
                    To=user.email,
                    # To="info@keyflow.co", #TODO: Change this to user.email when postmark account is approved
                    Subject='Activate your Keyflow account',
                    HtmlBody=f'Hi {user.first_name},<br/><br/>Thank you for registering with KeyFlow. Please click the link below to activate your account.<br/><br/><a href="{activation_link}">Activate Account</a><br/><br/>Regards,<br/>KeyFlow Team',
                )

            return Response(
                {
                    "message": "User registered successfully.",
                    "user": serializer.data,
                    "isAuthenticated": True,
                    "onboarding_link": account_link,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    #Create a function to create and return a stripe account link using the endpoint api/owners/{id}/stripe-account-link
    @action(detail=True, methods=["get"], url_path="stripe-account-link")
    def account_link(self, request, pk=None):
        owner = self.get_object()
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        client_hostname = os.getenv("CLIENT_HOSTNAME")
        refresh_url = f"{client_hostname}/dashboard/owner/login"
        return_url = f"{client_hostname}/dashboard/activate-account/"
        account_link = stripe.Account.create_login_link(
            id=owner.stripe_account_id,
        )

        return Response(
            {"account_link": account_link.url}, status=status.HTTP_200_OK
        )

    #Create a function to create and return a stripe account link using the endpoint api/owners/{id}/stripe-account-link
    @action(detail=True, methods=["get"], url_path="stripe-onboarding-account-link")
    def onboarding_account_link(self, request, pk=None):
        owner = self.get_object()
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        client_hostname = os.getenv("CLIENT_HOSTNAME")
        refresh_url = f"{client_hostname}/dashboard/owner/login"
        return_url = f"{client_hostname}/dashboard/owner/"
        # obtain stripe account link for the user to complete the onboarding process
        account_link = stripe.AccountLink.create(
            account=owner.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )

        return Response(
            {"account_link": account_link.url}, status=status.HTTP_200_OK
        )

    #Create a function to retrieve the owners stripe account requirements using the endpoint api/owners/{id}/stripe-account-requirements
    @action(detail=True, methods=["get"], url_path="stripe-account-requirements")
    def stripe_account_requirements (self, request, pk=None):
        owner = self.get_object()
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        account = stripe.Account.retrieve(owner.stripe_account_id)
        requirements = account.requirements
        return Response({"requirements": requirements}, status=status.HTTP_200_OK)
    
    # Create an action method to retrieve all tenants for a given owner. have the url_path be tenants (Replacing the LAndlordTenantList Vieew post method)
    @action(detail=True, url_path="tenants")
    def get_tenants(self, request, pk=None):
        try:
            owner = self.get_object()
            tenants = Tenant.objects.filter(owner=owner)
            serializer = TenantSerializer(tenants, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    # Replacing the OwnerTenantDetailView post method (TODO: Delelete the OwnerTenantDetailView post method and the owner.py file when done)
    @action(detail=True, methods=["get"])
    def get_tenant(self, request, pk=None):
        # Create variable for LANDLORD id
        owner_id = request.data.get("owner_id")
        tenant_id = request.data.get("tenant_id")

        owner = Owner.objects.get(id=owner_id)
        tenant = Tenant.objects.filter(id=tenant_id).first()

        # Find a lease agreement matching the owner and tenant

        # Retrieve the unit from the tenant
        unit = RentalUnit.objects.get(tenant=tenant)
        rental_property = RentalProperty.objects.get(id=unit.rental_property.id)

        # Retrieve transactions for the tenant
        transactions = Transaction.objects.filter(user=tenant.user)
        # Retrieve maintenance request
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=tenant)

        user_serializer = UserSerializer(tenant, many=False)
        unit_serializer = RentalUnitSerializer(unit, many=False)
        rental_property_serializer = RentalPropertySerializer(
            rental_property, many=False
        )
        transaction_serializer = TransactionSerializer(transactions, many=True)
        maintenance_request_serializer = MaintenanceRequestSerializer(
            maintenance_requests, many=True
        )

        lease_agreement = None
        lease_agreement_serializer = None
        if LeaseAgreement.objects.filter(user=owner, tenant=tenant).exists():
            lease_agreement = LeaseAgreement.objects.get(user=owner, tenant=tenant)
            lease_agreement_serializer = LeaseAgreementSerializer(
                lease_agreement, many=False
            )

        if lease_agreement:
            response_data = {
                "tenant": user_serializer.data,
                "unit": unit_serializer.data,
                "property": rental_property_serializer.data,
                "lease_agreement": lease_agreement_serializer.data,
                "transactions": transaction_serializer.data,
                "maintenance_requests": maintenance_request_serializer.data,
                "status": status.HTTP_200_OK,
            }
        else:
            response_data = {
                "tenant": user_serializer.data,
                "unit": unit_serializer.data,
                "property": rental_property_serializer.data,
                "transactions": transaction_serializer.data,
                "maintenance_requests": maintenance_request_serializer.data,
                "status": status.HTTP_200_OK,
            }
        if owner_id == request.user.id:
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # GET: api/users/{id}/properties

    # Create a function to retrieve a owner user's stripe subscription using the user's stripe customer id
    @action(detail=True, methods=["get"], url_path="subscriptions")
    def subscriptions(self, request, pk=None):
        owner = self.get_object()

        # Assuming 'user' is the foreign key field linking Owner to User
        user_instance = owner.user  # Access the User instance associated with Owner

        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        customer_id = owner.stripe_customer_id

        subscriptions = stripe.Subscription.list(customer=customer_id)
        owner_subscription = None

        for subscription in subscriptions.auto_paging_iter():
            if subscription.status == "active":
                owner_subscription = subscription
                break

        if owner_subscription:
            return Response(
                {"subscriptions": owner_subscription}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "subscriptions": None,
                    "message": "No active subscription found for this customer.",
                },
                status=status.HTTP_200_OK,
            )

    # Create a function to retrieve one speceiofic tenant
    @action(detail=True, methods=["post"], url_path="tenant")
    def tenant(self, request, pk=None):
        user = self.get_object()
        owner = Owner.objects.get(user=user)
        tenant = Tenant.objects.get(id=request.data.get("tenant_id"))

        serializer = TenantSerializer(tenant)
        # check if the user is the owner of the tenant
        if owner.id == tenant.owner.id:
            return Response(serializer.data)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Create a function to chagne a user's stripe susbcription plan
    @action(detail=True, methods=["post"], url_path="change-subscription-plan")
    def change_subscription_plan(self, request, pk=None):
        user = self.get_object()
        data = request.data.copy()
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        # retrieve the customer's subscription
        subscription = stripe.Subscription.retrieve(data["subscription_id"])
        current_product_id = subscription["items"]["data"][0]["price"]["product"]

        # Check if the product id from the current subscription matches the product id from the request and return an error that this current plan is already active
        if current_product_id == data["product_id"]:
            return Response(
                {
                    "message": "This subscription is already active.",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the product id from the current subscription is equal to os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID') then check if the user has 10 or more units. If they do return an error that they cannot downgrade to the standard plan
        if current_product_id == os.getenv("STRIPE_PRO_PLAN_PRODUCT_ID") and data[
            "product_id"
        ] == os.getenv("STRIPE_STANDARD_PLAN_PRODUCT_ID"):
            # Retrieve the user's units
            units = RentalUnit.objects.filter(user=user)
            if units.count() > 10:
                return Response(
                    {
                        "message": "You cannot downgrade to the standard plan with more than 10 units.",
                        "status": status.HTTP_400_BAD_REQUEST,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # check if the product id from the request is equal to os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID') and update the subscription item to the new price id and quantity of units
        if data["product_id"] == os.getenv("STRIPE_PRO_PLAN_PRODUCT_ID"):
            # Retrieve the user's units
            units = RentalUnit.objects.filter(user=user)
            # Update the subscription item to the new price id and quantity of units
            stripe.SubscriptionItem.modify(
                subscription["items"]["data"][0].id,
                price=data["price_id"],
                quantity=units.count(),
            )
            # modify the subscription metadata field product_id
            stripe.Subscription.modify(
                subscription.id,
                metadata={"product_id": data["product_id"]},
            )
            # Return a success message
            return Response(
                {
                    "subscription": subscription,
                    "message": "Subscription plan changed successfully.",
                    "status": status.HTTP_200_OK,
                },
                status=status.HTTP_200_OK,
            )

        stripe.SubscriptionItem.modify(
            subscription["items"]["data"][0].id,
            price=data["price_id"],
        )

        # modify the subscription metadata field product_id
        stripe.Subscription.modify(
            subscription.id,
            metadata={"product_id": data["product_id"]},
        )

        return Response(
            {
                "subscription": subscription,
                "message": "Subscription plan changed successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    #Create a function that retireves the owner's preferences
    @action(detail=True, methods=["get"], url_path="preferences") #GET: api/owners/{id}/preferences
    def preferences(self, request, pk=None):
        owner = self.get_object()
        preferences = json.loads(owner.preferences)
        return Response({"preferences":preferences},status=status.HTTP_200_OK)
   
    #Create a function that handles updates to the owner's preferences
    @action(detail=True, methods=["post"], url_path="update-preferences") #POST: api/owners/{id}/update-preferences
    def update_preferences(self, request, pk=None):
        owner = self.get_object()
        preferences = request.data.get("preferences")
        owner.preferences = json.dumps(preferences)
        owner.save()
        return Response({"preferences":preferences},status=status.HTTP_200_OK)
    
class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StaffSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    # Create a queryset to retrieve all tenants for a specific owner
    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = TenantSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["user__first_name", "user__last_name", "date_joined"]
    search_fields = ["user__first_name", "user__last_name"]
    filterset_fields = ["user__first_name", "user__last_name"]

    # Create a queryset to retrieve all tenants for a specific owner
    def get_queryset(self):
        user = self.request.user

        if user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(user=tenant.user)
            return queryset

        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    def calculate_rent_periods(self, lease_start_date, rent_frequency, term):
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
        self,
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
        return invoice
    def create_rent_invoices(
        self,
        lease_start_date,
        rent_amount,
        rent_frequency,
        lease_term,
        customer_id,
        unit,
        additional_charges_dict,
        lease_agreement
    ):
        rent_periods = self.calculate_rent_periods(
            lease_start_date, rent_frequency, lease_term
        )
        grace_period_days = 0  # Assuming a 5-day grace period; adjust as needed

        for period_start, period_end in rent_periods:
            # Assuming the due date is at the start of the period plus a grace period
            due_date = period_start + relativedelta(days=+grace_period_days)

            # Create Stripe invoice for each rent payment period
            self.create_invoice_for_period(
                period_start,
                rent_amount,
                customer_id,
                due_date,
                unit,
                additional_charges_dict,
                lease_agreement
            )

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        data = request.data.copy()

        data["password"] = make_password(data["password"])

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            tenant_user = User.objects.get(email=data["email"])

            unit_id = data["unit_id"]
            unit = RentalUnit.objects.get(id=unit_id)

            owner = unit.owner
            tenant_user.account_type = "tenant"

            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            customer = stripe.Customer.create(
                email=tenant_user.email,
                metadata={
                    "owner_id": owner.id,
                },
            )

            tenant_user.is_active = False
            tenant_user.save()

            tenant = Tenant.objects.create(
                user=tenant_user,
                stripe_customer_id=customer.id,
                owner=owner,
            )
            try: 
                owner_preferences = json.loads(owner.preferences)
                new_tenant_registration_complete = next(
                    item for item in owner_preferences if item["name"] == "new_tenant_registration_complete"
                )
                new_tenant_registration_complete_values = new_tenant_registration_complete["values"]
                for value in new_tenant_registration_complete_values:
                    if value["name"] == "push" and value["value"] == True:
                        notification = Notification.objects.create(
                            user=owner.user,
                            message=f"{tenant_user.first_name} {tenant_user.last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                            type="tenant_registered",
                            title="Tenant Registered",
                            resource_url=f"/dashboard/owner/tenants/{tenant_user.id}",
                        )
                    elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                        #Create a postmark email notification to the Owner
                        postmark = PostmarkClient(server_token=os.getenv('POSTMARK_SERVER_TOKEN'))
                        to_email = ""
                        if os.getenv("ENVIRONMENT") == "development":
                            to_email = "keyflowsoftware@gmail.com"
                        else:
                            to_email = owner.user.email
                        postmark.emails.send(
                            From=os.getenv('KEYFLOW_SENDER_EMAIL'), 
                            To=to_email,
                            Subject='Tenant Registration',
                            HtmlBody=f'Hi {owner.user.first_name},<br/><br/>{tenant_user.first_name} {tenant_user.last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}.<br/><br/>Regards,<br/>KeyFlow Team',
                        )
            except StopIteration:
                # Handle case where "new_tenant_registration_complete" is not found
                print("new_tenant_registration_complete not found. Notification not sent")
                pass
            except KeyError:
                # Handle case where "values" key is missing in "new_tenant_registration_complete"
                print("values key not found in new_tenant_registration_complete. Notification not sent")
                pass
            unit.tenant = tenant
            unit.is_occupied = True
            unit.save()

            lease_agreement =  LeaseAgreement.objects.filter(rental_unit=unit).first()
            lease_agreement = LeaseAgreement.objects.get(id=lease_agreement.id)
            lease_agreement.tenant = tenant
            lease_agreement.save()

            if lease_agreement.signed_lease_document_file:
                # REtreieve the signed lease document file metadata from the unit
                signed_lease_document_file_metadata = json.loads(
                    unit.signed_lease_document_metadata
                )
                start_date = signed_lease_document_file_metadata["lease_start_date"]
                end_date = signed_lease_document_file_metadata["lease_end_date"]
                date_signed = signed_lease_document_file_metadata["date_signed"]
                lease_agreement.start_date = start_date
                lease_agreement.end_date = end_date
                lease_agreement.signed_date = date_signed
                lease_agreement.save()

            if lease_agreement.rental_application:
                approval_hash = data["approval_hash"]
                rental_application = RentalApplication.objects.get(
                    approval_hash=approval_hash
                )
                rental_application.tenant = tenant
                rental_application.save()

            payment_method_id = data["payment_method_id"]
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            owner_user = owner.user
            lease_terms = json.loads(unit.lease_terms)
            # Retreive the object with the name of security_deposit from the preferences list
            security_deposit = next(
                (item for item in lease_terms if item["name"] == "security_deposit"),
                None,
            )
            # Get the value property from the security_deposit object
            security_deposit_value = float(security_deposit["value"])
            # Retrieve rent frequency from the preferences list
            rent = next(
                (item for item in lease_terms if item["name"] == "rent"),
                None,
            )
            # Get the value property from the rent object
            rent_value = float(rent["value"])
            # Get the rent frequency from the preferences list
            rent_frequency = next(
                (item for item in lease_terms if item["name"] == "rent_frequency"),
                None,
            )
            # Get the value property from the rent_frequency object
            rent_frequency_value = rent_frequency["value"]

            # Get the value of the grace period from the preferences list
            grace_period = next(
                (item for item in lease_terms if item["name"] == "grace_period"),
                None,
            )
            # Get the value property from the grace object
            grace_period_value = int(grace_period["value"])

            term = next(
                (item for item in lease_terms if item["name"] == "term"),
                None,
            )
            term_value = int(term["value"])

            if security_deposit_value > 0:
                security_deposit_invoice = stripe.Invoice.create(
                    customer=customer.id,
                    auto_advance=True,
                    collection_method="send_invoice",
                    # Set duedate for today
                    due_date=int(datetime.now().timestamp())+1000,
                    metadata={
                        "type": "security_deposit",
                        "description": "Security Deposit Payment",
                        "tenant_id": tenant.id,
                        "owner_id": owner.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "lease_agreement_id": lease_agreement.id,
                    },
                    transfer_data={"destination": unit.owner.stripe_account_id},
                )
                # Create stripe price for security deposit
                price = stripe.Price.create(
                    unit_amount=int(security_deposit_value * 100),
                    currency="usd",
                    product_data={
                        "name": str(
                            f"Security Deposit for unit {unit.name} at {unit.rental_property.name}"
                        )
                    },
                )
                stripe.InvoiceItem.create(
                    customer=customer.id,
                    price=price.id,
                    currency="usd",
                    description=f"{tenant.user.first_name} {tenant.user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    invoice=security_deposit_invoice.id,
                )
                stripe.Invoice.finalize_invoice(security_deposit_invoice.id)

            # security_deposit_payment_intent = stripe.PaymentIntent.create(#Change to invoice
            #     amount=int(security_deposit_value * 100),
            #     currency="usd",
            #     payment_method_types=["card"],
            #     customer=customer.id,
            #     payment_method=data["payment_method_id"],
            #     transfer_data={"destination": owner.stripe_account_id},
            #     confirm=True,
            #     metadata={
            #         "type": "revenue",
            #         "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
            #         "user_id": owner_user.id,
            #         "tenant_id": tenant.id,
            #         "owner_id": owner.id,
            #         "rental_property_id": unit.rental_property.id,
            #         "rental_unit_id": unit.id,
            #         "payment_method_id": data["payment_method_id"],
            #     },
            # )

            # owner_security_deposit_transaction = Transaction.objects.create(
            #     type="security_deposit",
            #     description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
            #     rental_property=unit.rental_property,
            #     rental_unit=unit,
            #     user=owner_user,
            #     amount=security_deposit_value,
            #     payment_method_id=data["payment_method_id"],
            #     payment_intent_id=security_deposit_payment_intent.id,
            # )

            # tenant_security_deposit_transaction = Transaction.objects.create(
            #     type="security_deposit",
            #     description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
            #     rental_property=unit.rental_property,
            #     rental_unit=unit,
            #     user=tenant_user,
            #     amount=security_deposit_value,
            #     payment_method_id=data["payment_method_id"],
            #     payment_intent_id=security_deposit_payment_intent.id,
            # )

            # notification = Notification.objects.create(
            #     user=owner_user,
            #     message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the security deposit for the amount of ${security_deposit_value} for unit {unit.name} at {unit.rental_property.name}",
            #     type="security_deposit_paid",
            #     title="Security Deposit Paid",
            #     resource_url=f"/dashboard/owner/transactions/{owner_security_deposit_transaction.id}",
            # )

            if grace_period_value != 0:
                start_date = datetime.fromisoformat(str(lease_agreement.start_date))
                time_to_add = grace_period_value
                end_date = 0
                if rent_frequency_value == "day":
                    end_date = start_date + relativedelta(days=time_to_add)
                elif rent_frequency_value == "month":
                    end_date = start_date + relativedelta(months=time_to_add)
                elif rent_frequency_value == "week":
                    end_date = start_date + relativedelta(weeks=time_to_add)
                elif rent_frequency_value == "year":
                    end_date = start_date + relativedelta(years=time_to_add)

                lease_agreement_product_name = (
                    f"Rent for unit {unit.name} at {unit.rental_property.name}"
                )
                lease_agreement_product = stripe.Product.create(
                    name=lease_agreement_product_name,
                    type="service",
                )
                lease_agreement_price = stripe.Price.create(
                    unit_amount=int(rent_value * 100),
                    currency="usd",
                    recurring={"interval": rent_frequency_value},
                    product=lease_agreement_product.id,
                    metadata={
                        "type": "rent_payment",
                        "lease_agreement_id": lease_agreement.id,
                        "owner_id": owner.id,
                        "tenant_id": tenant.id,
                    },
                )

                items = [{"price": lease_agreement_price.id}]
                additional_charges_dict = json.loads(unit.additional_charges)
                for charge in additional_charges_dict:
                    charge_product_name = f"{charge['name']} for unit {unit.name} at {unit.rental_property.name}"
                    charge_product = stripe.Product.create(
                        name=charge_product_name,
                        type="service",
                    )
                    additional_charge_price = stripe.Price.create(
                        unit_amount=int(charge["amount"]) * 100,
                        currency="usd",
                        recurring={"interval": charge["frequency"]},
                        product=charge_product.id,
                    )
                    items.append({"price": additional_charge_price.id})

                grace_period_end = int(end_date.timestamp())
                # subscription = stripe.Subscription.create(
                #     customer=customer.id,
                #     items=items,
                #     default_payment_method=payment_method_id,
                #     trial_end=grace_period_end,
                #     transfer_data={"destination": owner.stripe_account_id},
                #     cancel_at=int(
                #         datetime.fromisoformat(str(lease_agreement.end_date)).timestamp()
                #     ),
                #     metadata={
                #         "type": "rent_payment",
                #         "description": f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                #         "tenant_id": tenant.id,
                #         "owner_id": owner.id,
                #         "rental_property_id": unit.rental_property.id,
                #         "rental_unit_id": unit.id,
                #         "payment_method_id": data["payment_method_id"],
                #     },
                # )
                print(f"ZX register function rent_Frequency: {rent_frequency_value}")
                self.create_rent_invoices(
                    lease_agreement.start_date,
                    rent_value,
                    rent_frequency_value,
                    term_value,
                    customer.id,
                    unit,
                    additional_charges_dict,
                    lease_agreement
                )
            else:
                start_date = datetime.fromisoformat(str(lease_agreement.start_date))
                rent = next(
                    (item for item in lease_terms if item["name"] == "rent"),
                    None,
                )
                rent_value = float(rent["value"])
                rent_frequency = next(
                    (item for item in lease_terms if item["name"] == "rent_frequency"),
                    None,
                )
                rent_frequency_value = rent_frequency["value"]
                lease_agreement_product_name = str(
                    f"Rent for unit {unit.name} at {unit.rental_property.name}"
                )
                lease_agreement_product = stripe.Product.create(
                    name=lease_agreement_product_name,
                    type="service",
                )
                lease_agreement_price = stripe.Price.create(
                    unit_amount=int(rent_value * 100),
                    currency="usd",
                    recurring={"interval": rent_frequency_value},
                    product=lease_agreement_product.id,
                    metadata={
                        "type": "rent_payment",
                        "lease_agreement_id": lease_agreement.id,
                        "owner_id": owner.id,
                        "tenant_id": tenant.id,
                    },
                )

                # items = []

                # for charge in additional_charges_dict:
                #     charge_product_name = str(f"{charge['name']} for unit {unit.name} at {unit.rental_property.name}")
                #     print(charge_product_name)
                #     charge_product = stripe.Product.create(
                #         name=charge_product_name,
                #         type="service",
                #     )
                #     additional_charge_price = stripe.Price.create(
                #         unit_amount=int(charge["amount"]) * 100,
                #         currency="usd",
                #         recurring={"interval": charge["frequency"]},
                #         product=charge_product.id,
                #     )
                #     items.append({"price": additional_charge_price.id})

                # subscription = stripe.Subscription.create(
                #     customer=customer.id,
                #     items=items,
                #     transfer_data={"destination": owner.stripe_account_id},
                #     cancel_at=int(
                #         datetime.fromisoformat(str(lease_agreement.end_date)).timestamp()
                #     ),
                #     default_payment_method=payment_method_id,
                #     metadata={
                #         "type": "security_deposit",
                #         "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                #         "user_id": tenant_user.id,
                #         "tenant_id": tenant.id,
                #         "owner_id": owner.id,
                #         "rental_property_id": unit.rental_property.id,
                #         "rental_unit_id": unit.id,
                #         "payment_method_id": data["payment_method_id"],
                #     },
                # )
                # Create as stripe  invoice for security deposit


                additional_charges_dict = json.loads(unit.additional_charges)
                self.create_rent_invoices(
                    start_date,
                    rent_value,
                    rent_frequency_value,
                    term_value,
                    customer.id,
                    unit,
                    additional_charges_dict,
                    lease_agreement
                )

                if os.getenv("ENVIROMENT") == "development":
                    subscription_transaction = Transaction.objects.create(
                        type="rent_payment",
                        description=f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                        rental_property=unit.rental_property,
                        rental_unit=unit,
                        tenant=tenant,
                        owner=owner,
                        user=owner_user,
                        amount=int(rent_value),
                        payment_method_id=data["payment_method_id"],
                        payment_intent_id="subscription",
                    )

                    notification = Notification.objects.create(
                        user=owner_user,
                        message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the first month's rent for the amount of ${rent_value} for unit {unit.name} at {unit.rental_property.name}",
                        type="rent_payment",
                        title="Rent Payment",
                        resource_url=f"/dashboard/owner/transactions/{subscription_transaction.id}",
                    )

                    # #Create a postmark email notification to the Owner
                    # postmark = PostmarkClient(server_token=os.getenv('POSTMARK_SERVER_TOKEN'))
                    # to_email = ""
                    # if os.getenv("ENVIRONMENT") == "development":
                    #     to_email = "keyflowsoftware@gmail.com"
                    # else:
                    #     to_email = owner_user.email
                    # postmark.emails.send(
                    #     From=os.getenv('KEYFLOW_SENDER_EMAIL'),
                    #     To=owner_user.email,
                    #     Subject='Rent Payment',
                    #     HtmlBody=f'Hi {owner_user.first_name},<br/><br/>{tenant_user.first_name} {tenant_user.last_name} has paid the first month\'s rent for the amount of ${rent_value} for unit {unit.name} at {unit.rental_property.name}.<br/><br/>Regards,<br/>KeyFlow Team',
                    # )


            account_activation_token = AccountActivationToken.objects.create(
                user=tenant_user,
                email=tenant_user.email,
                token=data["activation_token"],
            )
            if os.getenv("ENVIRONMENT") == "production":
                postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                client_hostname = os.getenv("CLIENT_HOSTNAME")
                to_email = ""
                if os.getenv("ENVIRONMENT") == "development":
                    to_email = "keyflowsoftware@gmail.com"
                else:
                    to_email = tenant_user.email 
                activation_link = f'{client_hostname}/dashboard/activate-user-account/{account_activation_token.token}'
                postmark.emails.send(
                    From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                    To=to_email,
                    # To="info@keyflow.co", #TODO: Change this to user.email when postmark is verified
                    Subject='Activate your Keyflow account',
                    HtmlBody=f'Hi {tenant_user.first_name},<br/><br/>Thank you for registering with KeyFlow. Please click the link below to activate your account.<br/><br/><a href="{activation_link}">Activate Account</a><br/><br/>Regards,<br/>KeyFlow Team',
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

    # Create a function for a tenant to retrieve their unit. If no unit is assigned, return a 404
    @action(detail=True, methods=["get"], url_path="unit")  # GET: api/tenants/{id}/unit
    def get_unit(self, request, pk=None):
        tenant = self.get_object()
        try:
            unit = RentalUnit.objects.get(tenant=tenant)
        except RentalUnit.DoesNotExist:
            return Response({"data":None},status=status.HTTP_404_NOT_FOUND)
        serializer = RentalUnitSerializer(unit, many=False)
        return Response(serializer.data)

    # Create a function to retrieve all maintenance requests for a specific tenant user
    @action(
        detail=True, methods=["get"], url_path="maintenance-requests"
    )  # GET: api/tenants/{id}/maintenance-requests
    def maintenance_requests(self, request, pk=None):
        tenant = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=tenant)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Create a function to retrieve all transactions for a specific tenant user
    @action(
        detail=True, methods=["get"], url_path="transactions"
    )  # get: api/tenants/{id}/transactions
    def transactions(self, request, pk=None):
        tenant = self.get_object()
        transactions = Transaction.objects.filter(tenant=tenant)
        serializer = TransactionSerializer(transactions, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Create a function to retrieve all active lease agreements for a specific tenant user
    @action(
        detail=True, methods=["get"], url_path="lease-agreements"
    )  # get: api/tenants/{id}/lease-agreements
    def lease_agreements(self, request, pk=None):
        tenant = self.get_object()
        lease_agreements = LeaseAgreement.objects.filter(tenant=tenant, is_active=True)
        serializer = LeaseAgreementSerializer(lease_agreements, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # ------------Tenant Subscription Methods (Should replace the Function in the ManageTenantSubscriptionView in manage_subscriptions.py)-----------------
    @action(
        detail=False, methods=["post"], url_path="turn-off-autopay"
    )  # POST: api/tenants/turn-off-autopay
    def turn_off_autopay(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(user=user)
        # Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=tenant)
        # Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        # Retrieve the subscription id from the lease agreement object
        subscription_id = lease_agreement.stripe_subscription_id
        stripe.Subscription.modify(
            subscription_id,
            pause_collection={"behavior": "void"},
        )
        lease_agreement.auto_pay_is_enabled = False
        lease_agreement.save()
        # Return a response
        return Response(
            {
                "message": "Subscription paused successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    # Create a method to create a subscription called turn_on_autopay
    @action(detail=False, methods=["post"], url_path="turn-on-autopay")
    def turn_on_autopay(self, request, pk=None):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(user=user)
        # Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=tenant)
        # Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        subscription_id = lease_agreement.stripe_subscription_id

        stripe.Subscription.modify(
            subscription_id,
            pause_collection="",
        )
        lease_agreement.auto_pay_is_enabled = True
        lease_agreement.save()
        # Return a response
        return Response(
            {
                "message": "Subscription resumed successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    # Create a get function to retrieve the next payment date for rent for a specific user
    @action(detail=False, methods=["post"], url_path="next-payment-date")
    def next_payment_date(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(user=user)

        if LeaseAgreement.objects.filter(tenant=tenant, is_active=True).exists():
            lease_agreement = LeaseAgreement.objects.filter(
                tenant=tenant, is_active=True
            ).first()
            # Retrieve the lease agreement object from the unit object

            # Input lease start date (replace with your actual start date)
            lease_start_date = datetime.fromisoformat(
                f"{lease_agreement.start_date}"
            )  # Example: February 28, 2023

            # Calculate the current date
            current_date = datetime.now()

            # Calculate the next payment date
            while lease_start_date < current_date:
                next_month_date = lease_start_date + timedelta(
                    days=30
                )  # Assuming monthly payments
                # Ensure that the result stays on the same day even if the next month has fewer days
                # For example, if input_date is January 31, next_month_date would be February 28 (or 29 in a leap year)
                # This code snippet adjusts it to February 28 (or 29)
                if lease_start_date.day != next_month_date.day:
                    next_month_date = next_month_date.replace(day=lease_start_date.day)
                    lease_start_date = next_month_date
                else:
                    lease_start_date += timedelta(days=30)  # Assuming monthly payments

            next_payment_date = lease_start_date
            # Return a response
            return Response(
                {"next_payment_date": next_payment_date, "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"next_payment_date": None, "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )

    # Create a method to retrieve all payment dates for a specific user's subscription
    @action(
        detail=False, methods=["post"], url_path="payment-dates"
    )  # POST: api/tenants/payment-dates
    def payment_dates(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        tenant = Tenant.objects.get(user=user)

        if LeaseAgreement.objects.filter(tenant=tenant, is_active=True).exists():
            lease_agreement = LeaseAgreement.objects.get(tenant=tenant, is_active=True)
            # Retrieve the unit object from the user object
            unit = lease_agreement.rental_unit
            # Retrieve the lease agreement object from the unit object

            # Input lease start date (replace with your actual start date)
            lease_start_date = datetime.fromisoformat(
                f"{lease_agreement.start_date}"
            )  # Example: February 28, 2023

            # Calculate the lease end date
            lease_end_date = datetime.fromisoformat(
                f"{lease_agreement.end_date}"
            )  # Example: February 28, 2023

            # Create a payment dates list
            payment_dates = []

            # Calculate the next payment date
            while lease_start_date <= lease_end_date:
                # Check for transaction in database to see if payment has been made
                transaction_paid = Transaction.objects.filter(
                    rental_unit=unit,
                    timestamp__date=lease_start_date.date(),  # Extracts only the date part for comparison
                ).exists()

                event_title = "Rent Due"  # Default title

                if transaction_paid:
                    event_title = "Rent Paid"
                # check if the
                payment_dates.append(
                    {
                        "title": event_title,
                        "payment_date": lease_start_date,
                        "transaction_paid": transaction_paid,
                    }
                )

                # Move to the next month's payment date
                lease_start_date += timedelta(days=30)  # Assuming monthly payments

                # Ensure that the next month's date doesn't exceed the lease_end_date
                if lease_start_date > lease_end_date:
                    break

                # Check if the next month's date exceeds the lease_end_date
                # If so, set the payment date to the lease_end_date
                if lease_start_date + timedelta(days=30) > lease_end_date:
                    lease_start_date = lease_end_date

                # Check if the payment for the next month has already been made
                # If so, update the lease_start_date to that payment date
                transaction_paid_next_month = Transaction.objects.filter(
                    rental_unit=unit,
                    timestamp__date=lease_start_date.date(),  # Extracts only the date part for comparison
                ).exists()

                if transaction_paid_next_month:
                    lease_start_date += timedelta(days=30)

            # Return a response with the payment dates list
            return Response(
                {"payment_dates": payment_dates, "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"payment_dates": [], "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )

    # Create a method to retrieve all stripe invoices for a specific tenant
    @action(
        detail=True, methods=["post"], url_path="invoices"
    )  # POST: api/tenants/{id}/invoices
    def invoices(self, request, pk=None):
        tenant = self.get_object()
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        invoices = stripe.Invoice.list(limit=25, customer=tenant.stripe_customer_id)
        return Response({"invoices": invoices}, status=status.HTTP_200_OK)

    # Create A method to pay an invoice
    @action(
        detail=True, methods=["post"], url_path="pay-invoice"
    )  # POST: api/tenants/{id}/pay-invoice
    def pay_invoice(self, request, pk=None):
        unit = RentalUnit.objects.get(tenant=self.get_object())
        #Check if unit exists
        if unit is None:
            return Response(
                {"status": 404, "message": "Unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        invoice_id = request.data.get("invoice_id")
        invoice = stripe.Invoice.retrieve(invoice_id)
        payment_method_id = request.data.get("payment_method_id")
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")

        #Check if the invoice is past due and charge the late fee if it is
        # if invoice.status == "open" and invoice.due_date < int(datetime.now().timestamp()):
        #     #retrieve the late fee from the unit's lease terms
        #     lease_terms = json.loads(unit.lease_terms)
        #     late_fee = next(
        #         (item for item in lease_terms if item["name"] == "late_fee"),
        #         None,
        #     )
        #     late_fee_value = float(late_fee["value"])
        #     #Charge the late fee by creating payment intent
        #     stripe.PaymentIntent.create(
        #         amount=int(late_fee_value * 100),
        #         currency="usd",
        #         customer=invoice.customer,
        #         payment_method=payment_method_id,
        #         off_session=True,
        #         confirm=True,
        #         metadata={
        #             "type": "late_fee",
        #             "description": "Late Fee Payment",
        #             "tenant_id": invoice.metadata["tenant_id"],
        #             "owner_id": invoice.metadata["owner_id"],
        #             "rental_property_id": invoice.metadata["rental_property_id"],
        #             "rental_unit_id": invoice.metadata["rental_unit_id"],
        #             "payment_method_id": payment_method_id,
        #         },
        #     )

        # Pay the invoice
        stripe.Invoice.pay(invoice_id, payment_method=payment_method_id)


        return Response(
            {
                "invoice": invoice,
                "status": 200,
                "message": "Invoice paid successfully.",
            },
            status=status.HTTP_200_OK,
        )
    #Create a method to retrieve a specific invoice
    @action(
        detail=True, methods=["post"], url_path="retrieve-invoice"
    )  # POST: api/tenants/{id}/retrieve-invoice
    def retrieve_invoice(self, request, pk=None):
        invoice_id = request.data.get("invoice_id")
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        invoice = stripe.Invoice.retrieve(invoice_id)
        return Response(
            {
                "invoice": invoice,
                "status": 200,
                "message": "Invoice retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )
    #Create a function that retireves the owner's preferences
    @action(detail=True, methods=["get"], url_path="preferences") #GET: api/tenants/{id}/preferences
    def preferences(self, request, pk=None):
        tenant = self.get_object()
        print(tenant.preferences)
        preferences = json.loads(tenant.preferences)
        return Response({"preferences":preferences},status=status.HTTP_200_OK)
   
    #Create a function that handles updates to the owner's preferences
    @action(detail=True, methods=["post"], url_path="update-preferences") #POST: api/tenants/{id}/update-preferences
    def update_preferences(self, request, pk=None):
        tenant = self.get_object()
        preferences = request.data.get("preferences")
        tenant.preferences = json.dumps(preferences)
        tenant.save()
        return Response({"preferences":preferences},status=status.HTTP_200_OK)
    
    #Crreate a function that allows an owner to update a tenant's auto renew status using the endpoint /tenants/{tenant_id}/update-auto-renew-status/
    @action(detail=True, methods=["post"], url_path="update-auto-renew-status") #POST: api/tenants/{id}/update-auto-renew-status
    def update_auto_renew_status(self, request, pk=None):
        tenant = self.get_object()
        auto_renew_lease_is_enabled = request.data.get("auto_renew_lease_is_enabled")
        tenant.auto_renew_lease_is_enabled = auto_renew_lease_is_enabled
        tenant.save()
        return Response({"auto_renew_lease_is_enabled":auto_renew_lease_is_enabled},status=status.HTTP_200_OK)