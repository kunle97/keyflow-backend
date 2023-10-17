from rest_framework import serializers
from ..models.lease_term import LeaseTerm
from  .user_serializer import UserSerializer
#Create serializers for Lease TErm
class LeaseTermSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    class Meta:
        model = LeaseTerm
        fields = '__all__'
