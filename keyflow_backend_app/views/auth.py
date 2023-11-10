import os
from dotenv import load_dotenv
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from ..models.notification  import Notification
from ..models.user  import User
from ..models.rental_property  import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.maintenance_request  import MaintenanceRequest
from ..models.lease_term  import LeaseTerm
from ..models.transaction  import Transaction
from ..models.rental_application  import RentalApplication
from ..models.account_activation_token  import AccountActivationToken
from ..serializers.notification_serializer import NotificationSerializer
from ..serializers.user_serializer import UserSerializer 
from ..serializers.rental_property_serializer   import RentalPropertySerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from ..serializers.lease_term_serializer import LeaseTermSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from ..serializers.rental_application_serializer import RentalApplicationSerializer

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import stripe
load_dotenv()
#create a login endpoint
class UserLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({'message': 'Error logging you in.', 'status':status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        if not user.check_password(password):
            return Response({'message': 'Invalid email or password.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        #Check if user accoun is active
        if user.is_active is False:
            return Response({'message': 'User account is not active. Please check your email for an activation link.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        #create a token for the user on success full login
        token=Token.objects.create(user=user)
        serializer = UserSerializer(instance=user)
        return Response({'message': 'User logged in successfully.','user':serializer.data,'token':token.key,'statusCode':status.HTTP_200_OK, 'isAuthenticated':True}, status=status.HTTP_200_OK)

#create a logout endpoint that deletes the token
class UserLogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'User logged out successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

class UserRegistrationView(APIView):

    def post(self, request):
        User = get_user_model()
        data = request.data.copy()
        print(f'zx Data: {data}')
        # Hash the password before saving the user
        data['password'] = make_password(data['password'])
        
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=data['email'])

        #     #TODO: send email to the user to verify their email address
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
   
            # update the user with the stripe account id
            user.stripe_account_id = stripe_account.id

            #Create a customer id for the user
            customer = stripe.Customer.create(
                email=user.email
            )
            user.stripe_customer_id = customer.id

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
            user.stripe_subscription_id = subscription.id
            #obtain stripe account link for the user to complete the onboarding process
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url='http://localhost:3000/dashboard/landlord/login',
                return_url='http://localhost:3000/dashboard/activate-account/',
                type='account_onboarding',
            )
            user.is_active = False #TODO: Remove this for activation flow implementation
            user.save()
            #Create an account activation token for the user
            account_activation_token = AccountActivationToken.objects.create(
                user=user,
                email=user.email,
                token=data['activation_token'],
            )
            return Response({'message': 'User registered successfully.', 'user':serializer.data, 'isAuthenticated':True, "onboarding_link":account_link}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#Create a class that retrieve a price from stripe subscriptions for landlords and returns it in the response

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['first_name', 'last_name', 'email', 'created_at']

    #Create a function to change password
    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        user = self.get_object()
        print(f'zx User is auth: {user.is_authenticated}')
        data = request.data.copy()
        old_password = data['old_password']
        new_password = data['new_password']
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password changed successfully.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
        return Response({'message': 'Error changing password.'}, status=status.HTTP_400_BAD_REQUEST)
        
    #Create a function to retrieve a landlord user's stripe subscription using the user's stripe customer id
    #GET: api/users/{id}/landlord-subscriptions
    @action(detail=True, methods=['get'], url_path='landlord-subscriptions')
    def landlord_subscriptions(self, request, pk=None):
        user = self.get_object()
        #check if user is landlord. If not return error
        if user.account_type != 'landlord':
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        customer_id = user.stripe_customer_id
        customer = stripe.Customer.retrieve(customer_id)
        # Retrieve the customer's subscriptions using the list method
        subscriptions = stripe.Subscription.list(customer=customer_id)
        landlord_subscription = None
        for subscription in  subscriptions.auto_paging_iter():
            if subscription.status == "active":  # You can use any criteria to identify the subscription
                 # This is the customer's active subscription
                landlord_subscription = subscription
                break
        if(landlord_subscription):
            return Response({'subscriptions': landlord_subscription}, status=status.HTTP_200_OK)
        else:
            return Response({'subscriptions': None, "message":"No active subscription found for this customer."}, status=status.HTTP_200_OK)

    #GET: api/users/{id}/properties
    @action(detail=True, methods=['get'])
    def properties(self, request, pk=None): 
        user = self.get_object()
        properties = RentalProperty.objects.filter(user_id=user.id)
        serializer = RentalPropertySerializer(properties, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
    #GET: api/users/{id}/units
    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        user = self.get_object()
        units = RentalUnit.objects.filter(user_id=user.id)
        serializer = RentalUnitSerializer(units, many=True)
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
    
    #Create a function to retrieve one speceiofic tenant
    @action(detail=True, methods=['post'], url_path='tenant')
    def tenant(self, request, pk=None):
        user = self.get_object()
        tenant = User.objects.get(id=request.data.get('tenant_id'))
        serializer = UserSerializer(tenant)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    #Create a function to retrieve all of the tenants for a specific landlord
    #GET: api/users/{id}/tenants
    @action(detail=True, methods=['get'], url_path='tenants')
    def tenants(self, request, pk=None):
        qs = self.filter_queryset(self.get_queryset())
        user = self.get_object()
        #Verify user is a landlord
        if user.account_type != 'landlord':
           return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        #Retrieve landlord's properties
        properties = RentalProperty.objects.filter(user_id=user.id)
        #retrieve units for each property that are occupied
        units = RentalUnit.objects.filter(rental_property__in=properties, is_occupied=True)
        #Retrieve the tenants for each unit
        tenants = qs.filter(id__in=units.values_list('tenant', flat=True))
        #Create a user serializer for the tenants object
        serializer = UserSerializer(tenants, many=True)
        if user.id == request.user.id:
           return Response(serializer.data)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    #Create a function to retrieve a users Notifications
    @action(detail=True, methods=['get'], url_path='notifications')
    def notifications(self, request, pk=None):
        user = self.get_object()
        notifications = Notification.objects.filter(user=user)
        serializer = NotificationSerializer(notifications, many=True)
        if user.id == request.user.id:
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
 
#create an endpoint to activate the account of a new user that will set the  is_active field to true
class UserActivationView(APIView):
    def post(self, request):
        #Verify that the account activation token is valid
        account_activation_token = AccountActivationToken.objects.get(token=request.data.get('activation_token'))
        if account_activation_token is None:
            return Response({'message': 'Invalid token.','status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        #retrieve user via account activation token
        user = User.objects.get(email=account_activation_token.email)

        if user is None:
            return Response({'message': 'Error activating user.'}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = True
        user.save()
        #Delete the account activation token
        account_activation_token.delete()
        return Response({'account_type':user.account_type, 'message': 'User activated successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
