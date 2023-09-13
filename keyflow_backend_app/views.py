from datetime import timedelta, timezone
from rest_framework import viewsets, permissions
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action, authentication_classes, permission_classes, api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest, LeaseTerm, Transaction, RentalApplication
from .serializers import UserSerializer, PropertySerializer, UnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer, LeaseCancellationRequestSerializer, LeaseTermSerializer, TransactionSerializer
from .permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly, IsResourceOwner, DisallowUserCreatePermission, PropertyCreatePermission, ResourceCreatePermission,RentalApplicationCreatePermission
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import RentalApplicationSerializer
import stripe
import plaid
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
#Custom  classes
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


#create a login endpoint
class UserLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({'message': 'Error logging you in.'}, status=status.HTTP_404_NOT_FOUND)
        if not user.check_password(password):
            return Response({'message': 'Error logging you in.'}, status=status.HTTP_400_BAD_REQUEST)
        
        #create a token for the user on success full login
        token=Token.objects.create(user=user)
        serializer = UserSerializer(instance=user)
        return Response({'message': 'User logged in successfully.','user':serializer.data,'token':token.key,'statusCode':status.HTTP_200_OK, 'isAuthenticated':True}, status=status.HTTP_200_OK)

#create a logout endpoint that deletes the token
class UserLogoutView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'User logged out successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

class UserRegistrationView(APIView):

    def post(self, request):
        User = get_user_model()
        data = request.data.copy()
        
        # Hash the password before saving the user
        data['password'] = make_password(data['password'])
        
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=data['email'])

            #TODO: send email to the user to verify their email address
            #create stripe account for the user
            stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
            
            stripe_account = stripe.Account.create(
                type='express', 
                country='US', 
                email=user.email, 
                capabilities={
                    'card_payments': {'requested': True}, 
                    'transfers': {'requested': True}, 
                    'bank_transfer_payments': {'requested': True}
                })
            # stripe_account = stripe.Account.create(type='standard', country='US', email=user.email)
   
            #update the user with the stripe account id
            user.stripe_account_id = stripe_account.id

            #Create a customer id for the user
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id


            #obtain stripe account link for the user to complete the onboarding process
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url='http://localhost:3000/dashboard/landlord/login',
                return_url='http://localhost:3000/dashboard/landlord/',
                type='account_onboarding',
            )
            user.is_active = True #TODO: Remove this for activation flow implementation
            user.save()
            token=Token.objects.create(user=user)
            return Response({'message': 'User registered successfully.', 'user':serializer.data, 'token':token.key,'isAuthenticated':True, "onboarding_link":account_link}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DisallowUserCreatePermission]

    #GET: api/users/{id}/properties
    @action(detail=True, methods=['get'])
    def properties(self, request, pk=None): 
        user = self.get_object()
        properties = RentalProperty.objects.filter(user_id=user.id)
        serializer = PropertySerializer(properties, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/rental-applications
    @action(detail=True, methods=['get'], url_path='rental-applications')
    def rental_applications(self, request, pk=None):
        user = self.get_object()
        rental_applications = RentalApplication.objects.filter(landlord=user.id)
        serializer = RentalApplicationSerializer(rental_applications, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
   
    #GET: api/users/{id}/lease-terms
    @action(detail=True, methods=['get'], url_path='lease-terms')
    def lease_terms(self, request, pk=None):
        user = self.get_object()
        lease_terms = LeaseTerm.objects.filter(user_id=user.id)
        serializer = LeaseTermSerializer(lease_terms, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/transactions
    #Create a function to retrieve all transactions for a specific user
    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions(self, request, pk=None):
        user = self.get_object()
        transactions = Transaction.objects.filter(user_id=user.id)
        serializer = TransactionSerializer(transactions, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/transactions
    #Create a function to retrieve all transactions for a specific tenant user
    @action(detail=True, methods=['get'], url_path='tenant-transactions')
    def tenant_transactions(self, request, pk=None):
        user = self.get_object()
        transactions = Transaction.objects.filter(tenant_id=user.id)
        serializer = TransactionSerializer(transactions, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/tenant-maintenance-requests
    #Create a function to retrieve all maintenance requests for a specific tenant user
    @action(detail=True, methods=['get'], url_path='tenant-maintenance-requests')
    def tenant_maintenance_requests(self, request, pk=None):
        user = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=user)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/landlord-maintenance-requests
    #Create a function to retrieve all maintenance requests for a specific landlord user
    @action(detail=True, methods=['get'], url_path='landlord-maintenance-requests')
    def landlord_maintenance_requests(self, request, pk=None):
        user = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(landlord=user)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #POST: api/users/{id}/tenant
    #Create a function to retrieve a specific tenant for a specific landlord
    @action(detail=True, methods=['get'], url_path='tenant')
    def tenants(self, request, pk=None):
        user = self.get_object()
        #Create variable for tenant id
        tenant_id = request.data.get('tenant_id')
        tenant = User.objects.filter(id=tenant_id, account_type='tenant')
        
        #Find a lease agreement matching the landlord and tenant
        lease_agreement = LeaseAgreement.objects.filter(user=user, tenant=tenant_id)
        
        #Check if lease agreement does not exist
        if lease_agreement is None:
            return Response({'detail': 'Landlord Tenant relationship does not exist'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(tenant, many=True)
        print(f'zx Tenant: {tenant}')
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    

#Create an endpoint that registers a tenant
class TenantRegistrationView(APIView):
    def post(self, request):
        User = get_user_model()
        data = request.data.copy()
        
        # Hash the password before saving the user
        data['password'] = make_password(data['password'])
        
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=data['email'])

            #set the account type to tenant
            user.account_type = 'tenant' 
            
            #Create a stripe customer id for the user
            stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
            customer = stripe.Customer.create(email=user.email)
            print(f'Stripe customer id: {customer.id}')
            user.stripe_customer_id = customer.id
            print(f'User customer id: {user.stripe_customer_id}')

            user.is_active = True
            user.save()

            #Retrieve unit from the request unit_id parameter
            unit_id = data['unit_id']
            unit = RentalUnit.objects.get(id=unit_id)
            unit.tenant = user
            unit.save()

            #Retrieve lease agreement from the request lease_agreement_id parameter
            lease_agreement_id = data['lease_agreement_id']
            lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
            lease_agreement.tenant = user
            lease_agreement.save()

            #Retrieve rental application from the request approval_hash parameter
            approval_hash = data['approval_hash']
            rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
            rental_application.tenant = user
            rental_application.save()

            #Retrieve price id from lease term using lease_agreement
            lease_term = unit.lease_term

            #Attach payment method to the customer adn make it default
            payment_method_id = data['payment_method_id']
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            #TODO: implement secutrity deposit flow here. Ensure subsicption is sety to a trial period of 30 days and then charge the security deposit immeediatly


            #Create a stripe subscription for the user and make a default payment method
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {"price": lease_term.stripe_price_id},
                ],
                default_payment_method=payment_method_id,
                # trial_period_days=30,
            )

            #add subscription id to the lease agreement
            lease_agreement.stripe_subscription_id = subscription.id

            token=Token.objects.create(user=user)
            return Response({'message': 'Tenant registered successfully.', 'user':serializer.data, 'token':token.key,'isAuthenticated':True}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Create a class that retrieves a rental application by the approval_hash
class RetrieveRentalApplicationByApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
        serializer = RentalApplicationSerializer(rental_application)
        return Response(serializer.data, status=status.HTTP_200_OK)
class TenantVerificationView(APIView):
    #Create a function that verifies the lease agreement id and approval hash
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement_id = request.data.get('lease_agreement_id')

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        #check if the approval hash is valid with the lease agreement 
        if lease_agreement.approval_hash != approval_hash:
            return Response({'message': 'Invalid data.','status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        #return a response for the lease being signed successfully
        return Response({'message': 'Approval hash valid.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

#Create an endpoint that will handle when a person signs a lease agreement
class SignLeaseAgreementView(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement_id = request.data.get('lease_agreement_id')
        unit_id = request.data.get('unit_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        signed_date = request.data.get('signed_date')

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        #check if the approval hash is valid with the lease agreement 
        if lease_agreement.approval_hash != approval_hash:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        
        #retrieve the lease agreement object and update the start_date and end_date and set is_active to true
        lease_agreement.start_date = start_date
        lease_agreement.end_date = end_date
        lease_agreement.is_active = True
        lease_agreement.signed_date = signed_date
        #document_id = request.data.get('document_id') TODO
        lease_agreement.save()



        #retrieve the unit object and set the is_occupied field to true
        unit = RentalUnit.objects.get(id=unit_id)
        unit.is_occupied = True
        unit.save()


        #return a response for the lease being signed successfully
        return Response({'message': 'Lease signed successfully.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
       
#Create a function to retrieve a lease agreement by the id without the need for a token
class RetrieveLeaseAgreementByIdAndApprovalHashView(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement_id = request.data.get('lease_agreement_id')
        
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        #check if the approval hash is valid with the lease agreement 
        if lease_agreement.approval_hash != approval_hash:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = LeaseAgreementSerializer(lease_agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)

#create an endpoint to activate the account of a new user that will set the  is_active field to true
class UserActivationView(APIView):
    def post(self, request):
        User = get_user_model()
        data = request.data.copy()
        user = User.objects.get(email=data['email'])
        if user is None:
            return Response({'message': 'Error activating user.'}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = True
        user.save()
        return Response({'message': 'User activated successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
    #Create a get request to activate the user 
    def get(self, request):
        User = get_user_model()
        data = request.data.copy()
        user = User.objects.get(email=data['email'])
        if user is None:
            return Response({'message': 'Error activating user.'}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = True
        user.save()
        return Response({'message': 'User activated successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [ IsAuthenticated, IsResourceOwner, PropertyCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    #GET: api/properties/{id}/units
    @action(detail=True, methods=['get'])
    def units(self, request, pk=None): 
        property = self.get_object()
        units = RentalUnit.objects.filter(rental_property_id=property.id)
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)
   
    #GET: api/properties/{id}/tenants
    @action(detail=True, methods=['get'])
    def tenants(self, request, pk=None):
        property = self.get_object()
        tenants = User.objects.filter(unit__property=property, account_type='tenant')
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)

class UnitViewSet(viewsets.ModelViewSet):
    queryset = RentalUnit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated, IsResourceOwner, ResourceCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    pagination_class = CustomPagination

    #Create a function that sets the is occupied field to true
    @action(detail=True, methods=['post'])
    def set_occupied(self, request, pk=None):
        unit = self.get_object()
        unit.is_occupied = True
        unit.save()
        return Response({'message': 'Unit set to occupied successfully.'})

    #Create a function to retireve all rental applications for a specific unit
    @action(detail=True, methods=['get'], url_path='rental-applications')
    def rental_applications(self, request, pk=None):
        unit = self.get_object()
        rental_applications = RentalApplication.objects.filter(unit=unit)
        serializer = RentalApplicationSerializer(rental_applications, many=True)
        return Response(serializer.data)

    #manage leases (mainly used by landlords)
    @action(detail=True, methods=['post'])
    def assign_lease(self, request, pk=None):
        unit = self.get_object()
        lease_id = request.data.get('lease_id')
        lease = LeaseAgreement.objects.get(id=lease_id)
        unit.lease_agreement = lease
        unit.save()
        return Response({'message': 'Lease assigned successfully.'})

    @action(detail=True, methods=['post'])
    def remove_lease(self, request, pk=None):
        unit = self.get_object()
        unit.lease_agreement = None
        unit.save()
        return Response({'message': 'Lease removed successfully.'})  
    
    #Create a function to retrieve maintenance requests for a specific unit
    @action(detail=True, methods=['get'], url_path='maintenance-requests')
    def maintenance_requests(self, request, pk=None):
        unit = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(unit=unit)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        return Response(serializer.data)

    #Retrieve the lease term for a specific unit endpoint: api/units/{id}/lease-term
    @action(detail=True, methods=['get'], url_path='lease-term')
    def lease_term(self, request, pk=None):
        unit = self.get_object()
        lease_term = unit.lease_term
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data)

#Create a class to retrieve one specific unit by its id
class RetrieveTenantDashboardData(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        user= User.objects.get(id=user_id)
        unit = RentalUnit.objects.get(tenant=user)
        lease_term = unit.lease_term
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        
        
        unit_serializer = UnitSerializer(unit)
        lease_term_serializer = LeaseTermSerializer(lease_term)
        lease_agreement_serializer = LeaseAgreementSerializer(lease_agreement)

        unit_data = unit_serializer.data
        lease_term_data = lease_term_serializer.data
        lease_agreement_data = lease_agreement_serializer.data

        return Response({'unit':unit_data,'lease_term':lease_term_data,'lease_agreement':lease_agreement_data, 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

class RetrieveUnitUserId(APIView):
    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        serializer = UnitSerializer(unit)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)

class RetrievePropertyByIdView(APIView):
    def post(self, request):
        property_id = request.data.get('property_id')
        print(f'zx Property id: {property_id}')
        property = RentalProperty.objects.get(id=property_id)
        print(f'zx Property: {property}')
        serializer = PropertySerializer(property)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)


#Create a classs to retrieve one lease term from one specific unit
class RetrieveLeaseTermByUnitView(APIView):
    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        lease_term = unit.lease_term
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer
    permission_classes = [IsAuthenticated, IsLandlordOrReadOnly, IsResourceOwner]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

#Handle Lease
class TenantViewSet(viewsets.ModelViewSet):
    # ... (existing code)
    @action(detail=True, methods=['post'], url_path='make-payment')
    @permission_classes([IsAuthenticated])
    @authentication_classes([TokenAuthentication, SessionAuthentication])
    def make_payment_intent(self, request, pk=None):
        data= request.data.copy()
        user_id = request.data.get('user_id')#retrieve user id from the request
        tenant = User.objects.get(id=user_id)#retrieve the user object
        unit = RentalUnit.objects.get(tenant=tenant)#retrieve the unit object
        landlord = unit.user#Retrieve landlord object from unit object
        lease_term = unit.lease_term #Retrieve lease term object from unit object
        amount=lease_term.rent #retrieve the amount from the lease term object
        
        # Call Stripe API to create a payment
        stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount*100),
            currency='usd',
            payment_method_types=['card'],
            customer=tenant.stripe_customer_id,
            payment_method=data['payment_method_id'],
            transfer_data={
                "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
            },
            confirm=True,
        )

        #create a transaction object
        transaction = Transaction.objects.create(
            type = 'revenue',
            description = f'{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name} for landlord {landlord.first_name} {landlord.last_name}',
            rental_property = unit.rental_property,
            rental_unit = unit,
            user=landlord,
            tenant=tenant,
            amount=amount,
            payment_method_id=data['payment_method_id'],
            payment_intent_id=payment_intent.id,
        )

        #serialize transaction object and return it
        serializer = TransactionSerializer(transaction)
        transaction_data = serializer.data


        return Response({'payment_intent': payment_intent, 'transaction':transaction_data, "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @permission_classes([IsAuthenticated])
    @authentication_classes([TokenAuthentication, SessionAuthentication])
    def renew_lease(self, request, pk=None):
        tenant = self.get_object()
        if tenant.user != request.user:
            return Response({'detail': 'You do not have permission to renew this lease.'}, status=status.HTTP_403_FORBIDDEN)

        # Logic for renewing lease
        lease = LeaseAgreement.objects.create(
            property=tenant.unit.property,
            unit=tenant.unit,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=365),  # Example: Renew for one year
            monthly_rent=tenant.unit.monthly_rent,
            security_deposit=tenant.unit.security_deposit,
            terms="Renewed lease terms",
            signed_date=timezone.now(),
            is_active=True,
        )
        tenant.unit.lease_agreement = lease
        tenant.unit.save()
        return Response({'detail': 'Lease renewed successfully.'}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'])
    @permission_classes([IsAuthenticated])
    @authentication_classes([TokenAuthentication, SessionAuthentication])
    def request_cancellation(self, request, pk=None):
        tenant = self.get_object()
        if tenant.user != request.user:
            return Response({'detail': 'You do not have permission to request lease cancellation.'}, status=status.HTTP_403_FORBIDDEN)

        if tenant.unit.lease_agreement is None:
            return Response({'detail': 'No active lease to cancel.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate the remaining lease period
        remaining_days = (tenant.unit.lease_agreement.end_date - timezone.now()).days

        if remaining_days <= 30:
            # If there's less than 30 days remaining, the lease can't be cancelled
            return Response({'detail': 'Lease cannot be cancelled with less than 30 days remaining.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a cancellation request
        cancellation_request = LeaseCancellationRequest.objects.create(
            tenant=tenant,
            unit=tenant.unit,
            request_date=timezone.now(),
        )

        return Response({'detail': 'Lease cancellation request submitted successfully.'}, status=status.HTTP_200_OK)
    #Handle Payments (Stripe Concept)    
    # @action(detail=True, methods=['post'])
    # def make_payment(self, request, pk=None):
    #     tenant = self.get_object()
    #     amount = 1000  # Sample amount in cents
    #     # Call Stripe API to create a payment
    #     stripe.api_key = 'your_stripe_secret_key'
    #     payment_intent = stripe.PaymentIntent.create(
    #         amount=amount,
    #         currency='usd',
    #         payment_method_types=['card'],
    #         customer=tenant.stripe_account_id,
    #     )
    #     return Response({'client_secret': payment_intent.client_secret})

class LeaseCancellationRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaseCancellationRequest.objects.all()
    serializer_class = LeaseCancellationRequestSerializer
    permission_classes = [IsAuthenticated, IsTenantOrReadOnly, IsResourceOwner, ResourceCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def perform_create(self, serializer):
        tenant = self.request.user
        unit = tenant.unit
        if unit.lease_agreement and not unit.lease_agreement.is_active:
            raise serializers.ValidationError("Cannot request cancellation for an inactive lease.")
        serializer.save(tenant=tenant, unit=unit, request_date=timezone.now())

class RentalApplicationViewSet(viewsets.ModelViewSet):
    queryset = RentalApplication.objects.all()
    serializer_class = RentalApplicationSerializer
    permission_classes =[ RentalApplicationCreatePermission]#TODO: Investigate why IsResourceOwner is not working
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    #Create method to delete all rental applications for a specific unit
    @action(detail=True, methods=['delete'], url_path='delete-remaining-rental-applications')
    def delete_remaining_rental_applications(self, request, pk=None):
        application = self.get_object()
        rental_applications = RentalApplication.objects.filter(unit=application.unit,is_archived=False)
        rental_applications.delete()
        return Response({'message': 'Rental applications deleted successfully.'})

    #Create a method to approve a rental application
    @action(detail=True, methods=['post'], url_path='approve-rental-application')
    def approve_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        request_user = request.data.get('user_id')
        print(f'Reqeust User id: {request_user}')
        print(f'Landlord id: {rental_application.landlord.id}')
        if rental_application.landlord == request_user:
            rental_application.is_approved = True
            rental_application.save()
            return Response({'message': 'Rental application approved successfully.'})
        return Response({'message': 'You do not have the permissions to access this resource'})
    
    #Create a method to reject and delete a rental application
    @action(detail=True, methods=['post'], url_path='reject-rental-application')
    def reject_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        if request.user.is_authenticated and rental_application.landlord == request.user:
            rental_application.is_approved = False
            rental_application.save()
            rental_application.delete()
            return Response({'message': 'Rental application rejected successfully.'})
        return Response({'message': 'You do not have the permissions to access this resource'})
    

#make a viewset for lease terms
class LeaseTermCreateView(APIView):
    def post(self, request):
        user = User.objects.get(id=request.data.get('user_id'))
        data = request.data.copy()
        if user.is_authenticated and user.account_type == 'landlord':
            lease_term = LeaseTerm.objects.create(
                user=user,
                rent=data['rent'],
                term=data['term'],
                security_deposit=data['security_deposit'],
                late_fee=data['late_fee'],
                gas_included=data['gas_included'],
                water_included=data['water_included'],
                electric_included=data['electric_included'],
                repairs_included=data['repairs_included'],
                lease_cancellation_fee=data['lease_cancellation_fee'],
                lease_cancellation_notice_period=data['lease_cancellation_notice_period'],
            )
            #Create a stripe product for the lease term
            stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
            product = stripe.Product.create(
                name=f'{user.first_name} {user.last_name}\'s (User ID: {user.id}) {data["term"]} month lease @ ${data["rent"]}/month. Lease Term ID: {lease_term.id}',
                type='service',
                metadata={"seller_id": user.stripe_account_id},  # Associate the product with the connected account
            )

            #Create a stripe price for the lease term
            price = stripe.Price.create(
                unit_amount=data['rent']*100,
                recurring={"interval": "month"},
                currency='usd',
                product=product.id,
            )


            #update the lease term object with the stripe product and price ids
            lease_term.stripe_product_id = product.id
            lease_term.stripe_price_id = price.id
            lease_term.save()

            return Response({'message': 'Lease term created successfully.'})
        return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)   

    #Create a method to retrive all lease terms for a specific user
    @action(detail=True, methods=['get'])
    def user_lease_terms(self, request, pk=None):
        user = self.get_object()
        lease_terms = LeaseTerm.objects.filter(user_id=user.id)
        serializer = LeaseTermSerializer(lease_terms, many=True)
        return Response(serializer.data,  status=status.HTTP_200_OK)

#Create a class tto retrieve a lease term by its id and approval hash
class RetrieveLeaseTermByIdViewAndApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement = LeaseAgreement.objects.filter(approval_hash=approval_hash)
        #Check if a lease agreement with the approval hash exists
        if lease_agreement.exists() == False:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)

        lease_term_id = request.data.get('lease_term_id')
        print(f'Lease term id: {lease_term_id}')
        lease_term = LeaseTerm.objects.get(id=lease_term_id)
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
#Create a class tto retrieve a lease term by its id
class RetrieveLeaseTermByIdView(APIView):
    def post(self, request):
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        lease_term_id = request.data.get('lease_term_id')
        lease_term = LeaseTerm.objects.get(id=lease_term_id)
        #Check if user is the owner of the lease term
        if lease_term.user != user:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)

#Create a class to retrieve a unit by its id using the class name RetrieveUnitByIdView
class RetrieveUnitByIdView(APIView):
    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        serializer = UnitSerializer(unit)
        return Response(serializer.data, status=status.HTTP_200_OK) 

#Create a viewset for transactions model
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsResourceOwner, ResourceCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]


#Create a class that adds a card payment method for a user
class AddCardPaymentMethodView(APIView):
    def post(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        user_id = request.data.get('user_id')
        print(f'Req User id: {user_id}')
        print(f'User first name: {user.first_name}')
        print(f'user last name: {user.last_name}')
        print(f'Stripe customer id: {user.stripe_customer_id}')
        # Retrieve the payment method id from the request
        payment_method_id = request.data.get('payment_method_id')
        # Create a payment method for the user
        stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id,
        )
        # Return a response
        return Response({'message': 'Payment method added successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

#Create a class that lists the users payment methods
class ListPaymentMethodsView(APIView):
    def post(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        # Retrieve the payment method id from the request
        payment_method_id = request.data.get('payment_method_id')
        # Create a payment method for the user
        stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card",
        )
        # Return a response
        return Response(payment_methods, status=status.HTTP_200_OK)

class StripeViewSet(viewsets.ModelViewSet):
    #create a method to create price for a product
    @action(detail=True, methods=['post'], url_path='create-price')
    def create_rent_product(self, request, pk=None):
        stripe.api_key = "sk_test_51LkoD8EDNRYu93CIBSaakI9e31tBUi23aObcNPMUdVQH2UvzaYl6uVIbTUGbSJzjUOoReHsRU8AusmDRzW7V87wi00hHSSqjhl"
        
        product = stripe.Product.create(name=request.data.get('lease_term_name'))
        price = stripe.Price.create(
            unit_amount=request.data.get('unit_amount'),
            currency='usd',
            product=product.id,
        )
        
        return Response(price, status=status.HTTP_200_OK)

#Create a class that handles creating a plaid link token for a user
class PlaidLinkTokenView(APIView):
    def post(self, request):
        # Initialize the Plaid API client

        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id) 
        # Retrieve the client_user_id from the request and store it as a variable
        client_user_id = user.id
        # Create a link_token for the given user
        request = LinkTokenCreateRequest(
                products=[Products("auth")],
                client_name="Plaid Test App",
                country_codes=[CountryCode('US')],
                redirect_uri='https://domainname.com/oauth-page.html',
                language='en',
                webhook='https://webhook.example.com',
                user=LinkTokenCreateRequestUser(
                    # client_user_id=client_user_id
                    client_user_id="1"
                )
            )
        response = client.link_token_create(request)
        # Send the data to the client
        return Response(response.to_dict(), status=status.HTTP_200_OK)





#test to see if tooken is valid and return user info
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def test_token(request):
    return Response("passed for {}".format(request.user.username))

