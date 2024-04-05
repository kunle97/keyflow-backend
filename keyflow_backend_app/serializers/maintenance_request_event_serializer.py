from rest_framework import serializers
from ..models.maintenance_request_event import MaintenanceRequestEvent

class MaintenanceRequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequestEvent
        fields = '__all__'