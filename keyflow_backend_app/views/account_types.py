# Standard library imports
import os
from datetime import timedelta, datetime
from dotenv import load_dotenv

# Third-party library imports
import stripe
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
from keyflow_backend_app.serializers.lease_agreement_serializer import LeaseAgreementSerializer
from keyflow_backend_app.serializers.user_serializer import UserSerializer
from keyflow_backend_app.serializers.rental_property_serializer import RentalPropertySerializer
from keyflow_backend_app.serializers.rental_unit_serializer import RentalUnitSerializer
from keyflow_backend_app.serializers.maintenance_request_serializer import MaintenanceRequestSerializer
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

    #Replaces the UserREgistrationView(endpoint api/auth/register/)
    @action(detail=False, methods=['post'], url_path="register")  #New url path for the register endpoint: api/owners/register
    def register(self, request):
        User = get_user_model()
        data = request.data.copy()
        # Hash the password before saving the user
        data['password'] = make_password(data['password'])
         
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=data['email'])

            #TODO: send email to the user to verify their email address
            stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
            
            # create stripe account for the user
            stripe_account = stripe.Account.create(
                type='express', 
                country='US', 
                email=user.email, 
                capabilities={
                    'card_payments': {'requested': True}, 
                    'transfers': {'requested': True}, 
                    'bank_transfer_payments': {'requested': True}
                }
            )

            #Create a customer id for the user
            customer = stripe.Customer.create(
                email=user.email
            )

            # attach payment method to the customer adn make it default
            payment_method_id = data['payment_method_id']
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            #Subscribe landlord to thier selected plan using product id and price id
            product_id = data['product_id']
            price_id = data['price_id']
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": price_id},
                ],
                default_payment_method=payment_method_id,
                metadata={
                    "type": "revenue",
                    "description": f'{user.first_name} {user.last_name} Landlord Subscrtiption',
                    "product_id": product_id,
                    "user_id": user.id,
                    "tenant_id": user.id,
                    "payment_method_id": payment_method_id,
                }
            )
            client_hostname = os.getenv('CLIENT_HOSTNAME')
            refresh_url = f'{client_hostname}/dashboard/landlord/login'
            return_url = f'{client_hostname}/dashboard/activate-account/'
            #obtain stripe account link for the user to complete the onboarding process
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            user.is_active = False #TODO: Remove this for activation flow implementation
            user.save()

            Owner.objects.create(
                user=user,
                stripe_account_id=stripe_account.id,
                stripe_customer_id=customer.id,
                stripe_subscription_id=subscription.id,
            )

            #Create an account activation token for the user
            account_activation_token = AccountActivationToken.objects.create(
                user=user,
                email=user.email,
                token=data['activation_token'],
            )
            return Response({'message': 'User registered successfully.', 'user':serializer.data, 'isAuthenticated':True, "onboarding_link":account_link}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


    #Replacing the LandlordTenantDetailView post method (TODO: Delelete the LandlordTenantDetailView post method and the landlord.py file when done)
    @action(detail=True, methods=['get'])
    def get_tenant(self, request, pk=None):
        # Create variable for LANDLORD id
        landlord_id = request.data.get("landlord_id")
        tenant_id = request.data.get("tenant_id")

        landlord = Owner.objects.get(id=landlord_id)
        tenant = Tenant.objects.filter(id=tenant_id).first()

        # Find a lease agreement matching the landlord and tenant

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
        if LeaseAgreement.objects.filter(user=landlord, tenant=tenant).exists():
            lease_agreement = LeaseAgreement.objects.get(user=landlord, tenant=tenant)
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
        if landlord_id == request.user.id:
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )


     #GET: api/users/{id}/properties

    #Create a function to retrieve a landlord user's stripe subscription using the user's stripe customer id
    @action(detail=True, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request, pk=None):
        owner = self.get_object()
        
        # Assuming 'user' is the foreign key field linking Owner to User
        user_instance = owner.user  # Access the User instance associated with Owner
        
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        customer_id = owner.stripe_customer_id
        
        subscriptions = stripe.Subscription.list(customer=customer_id)
        landlord_subscription = None
        
        for subscription in subscriptions.auto_paging_iter():
            if subscription.status == "active":
                landlord_subscription = subscription
                break
        
        if landlord_subscription:
            return Response({'subscriptions': landlord_subscription}, status=status.HTTP_200_OK)
        else:
            return Response({'subscriptions': None, "message": "No active subscription found for this customer."}, status=status.HTTP_200_OK)
    #Create a function to retrieve one speceiofic tenant
    @action(detail=True, methods=['post'], url_path='tenant')
    def tenant(self, request, pk=None):
        user = self.get_object()
        owner = Owner.objects.get(user=user)
        tenant = Tenant.objects.get(id=request.data.get('tenant_id'))
        
        serializer = TenantSerializer(tenant)
        #check if the user is the owner of the tenant
        if owner.id == tenant.owner.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

    
    #Create a function to chagne a user's stripe susbcription plan
    @action(detail=True, methods=['post'], url_path='change-subscription-plan')
    def change_subscription_plan(self, request, pk=None):
        user = self.get_object()
        data = request.data.copy()
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        #retrieve the customer's subscription
        subscription = stripe.Subscription.retrieve(data['subscription_id'])
        current_product_id = subscription['items']['data'][0]['price']['product']

        #Check if the product id from the current subscription matches the product id from the request and return an error that this current plan is already active
        if current_product_id == data['product_id']:
            return Response({'message': 'This subscription is already active.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        #Check if the product id from the current subscription is equal to os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID') then check if the user has 10 or more units. If they do return an error that they cannot downgrade to the standard plan 
        if current_product_id == os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID') and data['product_id'] == os.getenv('STRIPE_STANDARD_PLAN_PRODUCT_ID'):
            #Retrieve the user's units
            units = RentalUnit.objects.filter(user=user)
            if units.count() > 10:
                return Response({'message': 'You cannot downgrade to the standard plan with more than 10 units.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        #check if the product id from the request is equal to os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID') and update the subscription item to the new price id and quantity of units
        if data['product_id'] == os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID'):
            #Retrieve the user's units
            units = RentalUnit.objects.filter(user=user)
            #Update the subscription item to the new price id and quantity of units
            stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                price=data['price_id'],
                quantity=units.count(),
            )
            #modify the subscription metadata field product_id
            stripe.Subscription.modify(
                subscription.id,
                metadata={'product_id': data['product_id']},
            )
            #Return a success message
            return Response({'subscription': subscription,'message': 'Subscription plan changed successfully.',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)


        stripe.SubscriptionItem.modify(
            subscription['items']['data'][0].id,
            price=data['price_id'],
        )

        #modify the subscription metadata field product_id
        stripe.Subscription.modify(
            subscription.id,
            metadata={'product_id': data['product_id']},
        )

        return Response({'subscription': subscription,'message': 'Subscription plan changed successfully.',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StaffSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    #Create a queryset to retrieve all tenants for a specific landlord
    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = TenantSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['user__first_name', 'user__last_name']
    search_fields = ['user__first_name', 'user__last_name']
    filterset_fields = ['user__first_name', 'user__last_name']

    #Create a queryset to retrieve all tenants for a specific landlord
    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    #Createa a register endpoint for tenants
    @action(detail=False, methods=["post"], url_path="register")  #New url path for the register endpoint: api/tenants/register
    def register(self, request):
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

            # retrieve owner from the unit
            owner = unit.owner

            # set the account type to tenant
            tenant_user.account_type = "tenant"
            # Create a stripe customer id for the user
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

            # Create a notification for the owner that a tenant has been added
            notification = Notification.objects.create(
                user=owner.user,
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

            owner = unit.owner
            owner_user = owner.user
            # TODO: implement secutrity deposit flow here. Ensure subsicption is sety to a trial period of 30 days and then charge the security deposit immeediatly
            if lease_template.security_deposit > 0:
                # Retrieve owner from the unit
                security_deposit_payment_intent = stripe.PaymentIntent.create(
                    amount=int(lease_template.security_deposit * 100),
                    currency="usd",
                    payment_method_types=["card"],
                    customer=customer.id,
                    payment_method=data["payment_method_id"],
                    transfer_data={
                        "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                    },
                    confirm=True,
                    # Add Metadata to the transaction signifying that it is a security deposit
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": owner_user.id,
                        "tenant_id": tenant.id,
                        "owner_id": owner.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )

                # create a transaction object for the security deposit
                owner_security_deposit_transaction = Transaction.objects.create(
                    type="security_deposit",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    user=owner_user,
                    amount=int(lease_template.security_deposit),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id=security_deposit_payment_intent.id,
                )
                # create a transaction object for the security deposit
                tenant_security_deposit_transaction = Transaction.objects.create(
                    type="security_deposit",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    user=tenant_user,
                    amount=int(lease_template.security_deposit),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id=security_deposit_payment_intent.id,
                )
                # Create a notification for the owner that the security deposit has been paid
                notification = Notification.objects.create(
                    user=owner_user,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the security deposit for the amount of ${lease_template.security_deposit} for unit {unit.name} at {unit.rental_property.name}",
                    type="security_deposit_paid",
                    title="Security Deposit Paid",
                    resource_url=f"/dashboard/landlord/transactions/{owner_security_deposit_transaction.id}",
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
                        "type": "rent_payment",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant_user.id,
                        "owner_id": owner.id,
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
                        "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                    },
                    cancel_at=int(
                        datetime.fromisoformat(
                            f"{lease_agreement.end_date}"
                        ).timestamp()
                    ),
                    default_payment_method=payment_method_id,
                    metadata={
                        "type": "security_deposit",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant.id,
                        "owner_id": owner.id,
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
                    user=owner_user,
                    amount=int(lease_template.rent),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id="subscription",
                )
                # Create a notification for the owner that the tenant has paid the fisrt month's rent
                notification = Notification.objects.create(
                    user=owner_user,
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

    #Create a function for a tenant to retrieve their unit. If no unit is assigned, return a 404
    @action(detail=True, methods=["get"], url_path="unit")#GET: api/tenants/{id}/unit
    def get_unit(self, request, pk=None):
        tenant = self.get_object()
        unit = RentalUnit.objects.get(tenant=tenant)
        if unit is None:
            return Response(status=404)
        serializer = RentalUnitSerializer(unit, many=False)
        return Response(serializer.data)
    #Create a function to retrieve all maintenance requests for a specific tenant user
    @action(detail=True, methods=['get'], url_path='maintenance-requests')#GET: api/tenants/{id}/maintenance-requests
    def maintenance_requests(self, request, pk=None):
        tenant = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=tenant)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #Create a function to retrieve all transactions for a specific tenant user
    @action(detail=True, methods=['get'], url_path='transactions') #get: api/tenants/{id}/transactions
    def transactions(self, request, pk=None):
        tenant = self.get_object()
        transactions = Transaction.objects.filter(user=tenant.user)
        serializer = TransactionSerializer(transactions, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #Create a function to retrieve all active lease agreements for a specific tenant user
    @action(detail=True, methods=['get'], url_path='lease-agreements') #get: api/tenants/{id}/lease-agreements
    def lease_agreements(self, request, pk=None):
        tenant = self.get_object()
        lease_agreements = LeaseAgreement.objects.filter(tenant=tenant, is_active=True)
        serializer = LeaseAgreementSerializer(lease_agreements, many=True)
        if tenant.user.id == request.user.id or tenant.owner.user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #------------Tenant Subscription Methods (Should replace the Function in the ManageTenantSubscriptionView in manage_subscriptions.py)-----------------
    @action(detail=False, methods=["post"], url_path="turn-off-autopay")
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
            lease_agreement = LeaseAgreement.objects.filter(tenant=tenant, is_active=True).first()
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
    @action(detail=False, methods=["post"], url_path="payment-dates")#POST: api/tenants/payment-dates
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
            payment_dates = [
            ]

            # Calculate the next payment date
            while lease_start_date <= lease_end_date:
                # Check for transaction in database to see if payment has been made
                transaction_paid = Transaction.objects.filter(
                    rental_unit=unit,
                    timestamp__date=lease_start_date.date()  # Extracts only the date part for comparison
                ).exists()
                
                event_title = "Rent Due"  # Default title
                
                if transaction_paid:
                    event_title = "Rent Paid"
                #check if the 
                payment_dates.append({
                    "title": event_title,
                    "payment_date": lease_start_date,
                    "transaction_paid": transaction_paid,
                })
                
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
                    timestamp__date=lease_start_date.date()  # Extracts only the date part for comparison
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
