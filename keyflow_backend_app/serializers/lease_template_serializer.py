from rest_framework import serializers
from ..models.lease_template import LeaseTemplate
from  .rental_unit_serializer import RentalUnitSerializer
from .account_type_serializer import OwnerSerializer

#Create serializers for Lease Template
class LeaseTemplateSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(many=False, read_only=True)
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    class Meta:
        model = LeaseTemplate
        fields = '__all__'
