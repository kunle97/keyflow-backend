from rest_framework import serializers
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalProperty
        fields = '__all__'

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalUnit
        fields = '__all__'

class LeaseAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseAgreement
        fields = '__all__'

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = '__all__'

class LeaseCancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseCancellationRequest
        fields = '__all__'
