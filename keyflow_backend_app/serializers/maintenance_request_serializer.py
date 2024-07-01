from rest_framework import serializers
from ..models.maintenance_request import MaintenanceRequest
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .account_type_serializer import OwnerSerializer, TenantSerializer
from .maintenance_request_event_serializer import MaintenanceRequestEventSerializer

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    tenant = TenantSerializer(many=False, read_only=True)
    owner = OwnerSerializer(many=False, read_only=True)
    events = MaintenanceRequestEventSerializer(many=True, read_only=True, source='maintenance_request_events')
    maintenance_request_events = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = MaintenanceRequest
        fields = '__all__'
