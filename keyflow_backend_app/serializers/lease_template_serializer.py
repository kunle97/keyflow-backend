from rest_framework import serializers
from ..models.lease_template import LeaseTemplate
from  .user_serializer import UserSerializer
from  .rental_unit_serializer import RentalUnitSerializer
#Create serializers for Lease Term
class LeaseTemplateSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    class Meta:
        model = LeaseTemplate
        fields = '__all__'
