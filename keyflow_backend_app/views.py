from rest_framework import viewsets
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest
from .serializers import UserSerializer, PropertySerializer, UnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = PropertySerializer

class UnitViewSet(viewsets.ModelViewSet):
    queryset = RentalUnit.objects.all()
    serializer_class = UnitSerializer

class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
