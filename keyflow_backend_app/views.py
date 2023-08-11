from datetime import timedelta, timezone
from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest
from .serializers import UserSerializer, PropertySerializer, UnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer, LeaseCancellationRequestSerializer
from .permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, serializers

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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
    # permission_classes = [IsAuthenticated, IsLandlordOrReadOnly]
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

    def perform_create(self, serializer):
        tenant = self.request.user
        unit = tenant.unit
        if unit.lease_agreement and not unit.lease_agreement.is_active:
            raise serializers.ValidationError("Cannot request cancellation for an inactive lease.")
        serializer.save(tenant=tenant, unit=unit, request_date=timezone.now())
