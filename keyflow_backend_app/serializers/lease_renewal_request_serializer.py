from rest_framework import serializers
from keyflow_backend_app.models.lease_renewal_request import LeaseRenewalRequest
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .account_type_serializer import OwnerSerializer, TenantSerializer

class LeaseRenewalRequestSerializer(serializers.ModelSerializer):
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    tenant = TenantSerializer(many=False, read_only=True)
    owner = OwnerSerializer(many=False, read_only=True)
    class Meta:
        model = LeaseRenewalRequest
        fields = "__all__"