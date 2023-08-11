from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest
from .serializers import UserSerializer, PropertySerializer, UnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer
from .permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserRegistrationView(APIView):
    def post(self, request):
        User = get_user_model()
        data = request.data.copy()
        
        # Hash the password before saving the user
        data['password'] = make_password(data['password'])
        
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'message': 'User registered successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = PropertySerializer
    # permission_classes = [IsAuthenticated, IsLandlordOrReadOnly]


class UnitViewSet(viewsets.ModelViewSet):
    queryset = RentalUnit.objects.all()
    serializer_class = UnitSerializer
    # permission_classes = [IsAuthenticated, IsLandlordOrReadOnly]


class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer
    # permission_classes = [IsAuthenticated, IsLandlordOrReadOnly]

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    # permission_classes = [IsAuthenticated, IsTenantOrReadOnly]
    
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
        # Logic for renewing lease
        return Response({'message': 'Lease renewed successfully.'})

    @action(detail=True, methods=['post'])
    def request_cancellation(self, request, pk=None):
        tenant = self.get_object()
        # Logic for requesting lease cancellation
        return Response({'message': 'Lease cancellation requested.'})

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