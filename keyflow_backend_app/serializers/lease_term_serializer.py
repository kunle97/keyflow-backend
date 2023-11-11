from rest_framework import serializers
from ..models.lease_term import LeaseTerm
from  .user_serializer import UserSerializer
from  .rental_unit_serializer import RentalUnitSerializer
#Create serializers for Lease Term
class LeaseTermSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    class Meta:
        model = LeaseTerm
        fields = '__all__'
