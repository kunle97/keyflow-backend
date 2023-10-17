from rest_framework import serializers
from ..models.maintenance_request import MaintenanceRequest
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .user_serializer import UserSerializer

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    tenant = UserSerializer(many=False, read_only=True)
    landlord = UserSerializer(many=False, read_only=True)
    class Meta:
        model = MaintenanceRequest
        fields = '__all__'
