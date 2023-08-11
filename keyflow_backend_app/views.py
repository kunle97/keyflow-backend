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
from rest_framework.permissions import IsAuthenticated, BasePermission
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest
from .serializers import UserSerializer, PropertySerializer, UnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer, LeaseCancellationRequestSerializer
from .permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import TenantApplicationSerializer

#Custom  classes
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CustomUpdatePermission(BasePermission):
    """
    Permission class to check that a user can update his own resource only
    """

    # check that its an update request and user is modifying his resource only
    def has_permission(self, request, view):
        request_id = request.user.id #id of the user making the request
        #check if view.kwargs.get('pk', None) is a string
        if type(view.kwargs.get('pk', None)) is str: 
            url_id = int(view.kwargs.get('pk', None)) #id in the url
        else:
            url_id = view.kwargs.get('pk', None) #id in the url converted to int
        if (request.method  == 'PUT' or request.method =='PATCH') and url_id != request_id:
            return False # not grant access
        return True # grant access otherwise


#create a custom permission class that does not allow the creation of a User
class DisallowUserCreatePermission(BasePermission):
    """
    Permission class to check that a user can create his own resource only
    """

    def has_permission(self, request, view):
        # check that its a create request and user is creating a resource only
        if request.method  == 'CREATE':
            return False # not grant access

#create a custom permission class for creating a resource
class CustomCreatePermission(BasePermission):
    """
    Permission class to check that a user can create his own resource only
    """

    def has_permission(self, request, view):
        # check that its a create request and user is creating a resource only
        request_id = request.user.id #id of the user making the request
        #create variable for request body
        request_body_user = request.data.get('user')
         #check if view.kwargs.get('pk', None) is a string

        if type(request_body_user) is str: 
            user_id = int(request_body_user) #id in the url converted from string to int
        else:
            user_id = view.kwargs.get('pk', None) #id in the url as an int


        if request.method  == 'POST' and (user_id != int(request_id)):
            return False # not grant access
        return True # grant access otherwise

class CustomDeletePermission(BasePermission):
    """
    Permission class to check that a user can delete his own resource only
    """
        
    def has_permission(self, request, view):
        request_id = request.user.id #id of the user making the request
        #check if view.kwargs.get('pk', None) is a string
        if type(view.kwargs.get('pk', None)) is str: 
            url_id = int(view.kwargs.get('pk', None)) #id in the url
        else:
            url_id = view.kwargs.get('pk', None) #id in the url converted to int
        if (request.method == 'DELETE' and url_id != request_id):
            if not request.user.is_authenticated:
                return False
        return True


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
        return Response({'message': 'User logged in successfully.','user':serializer.data,'token':token.key}, status=status.HTTP_200_OK)
    
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
            user.is_active = True
            user.save()
            token=Token.objects.create(user=user)
            return Response({'message': 'User registered successfully.', 'user':serializer.data, 'token':token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, CustomUpdatePermission, CustomDeletePermission, DisallowUserCreatePermission]


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [CustomUpdatePermission, IsAuthenticated, IsLandlordOrReadOnly,CustomCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        property = self.get_object()
        units = property.units.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tenants(self, request, pk=None):
        property = self.get_object()
        tenants = User.objects.filter(unit__property=property, account_type='tenant')
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)

class UnitViewSet(viewsets.ModelViewSet):
    queryset = RentalUnit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [CustomUpdatePermission, IsAuthenticated, IsLandlordOrReadOnly,CustomCreatePermission, CustomDeletePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    pagination_class = CustomPagination

    #manage leases (mianly used by landlords)
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

class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer
    permission_classes = [IsAuthenticated, IsLandlordOrReadOnly]

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated, IsTenantOrReadOnly]
    
    @action(detail=True, methods=['post'])
    def mark_resolved(self, request, pk=None):
        maintenance_request = self.get_object()
        maintenance_request.resolved = True
        maintenance_request.save()
        return Response({'message': 'Maintenance request marked as resolved.'})

#Handle Lease
class TenantViewSet(viewsets.ModelViewSet):
    # ... (existing code)

    @action(detail=True, methods=['post'])
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
    permission_classes = [IsAuthenticated, IsTenantOrReadOnly]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def perform_create(self, serializer):
        tenant = self.request.user
        unit = tenant.unit
        if unit.lease_agreement and not unit.lease_agreement.is_active:
            raise serializers.ValidationError("Cannot request cancellation for an inactive lease.")
        serializer.save(tenant=tenant, unit=unit, request_date=timezone.now())

class TenantApplicationView(APIView):
    def post(self, request):
        data = request.data.copy()
        data['landlord'] = request.user.id  # Assign the logged-in landlord user
        serializer = TenantApplicationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application submitted successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#test to see if tooken is valid and return user info
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def test_token(request):
    return Response("passed for {}".format(request.user.username))