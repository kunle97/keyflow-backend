from rest_framework import serializers
from ..models.account_type import Owner, Staff, Tenant
from .user_serializer import UserSerializer
from .rental_property_serializer import RentalPropertySerializer

class OwnerSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    # Create a field for the owner's tenants
    rental_properties = RentalPropertySerializer(many=True, read_only=True) 
    class Meta:
        model = Owner
        fields = "__all__"


class StaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    owner = OwnerSerializer(many=False, read_only=True)

    class Meta:
        model = Staff
        fields = "__all__"


class TenantSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    owner = OwnerSerializer(many=False, read_only=True)

    class Meta:
        model = Tenant
        fields = "__all__"
