from rest_framework import serializers
from ..models.rental_application import RentalApplication
from .rental_unit_serializer import RentalUnitSerializer
from .user_serializer import UserSerializer
class RentalApplicationSerializer(serializers.ModelSerializer):
    tenant = UserSerializer(many=False, read_only=True)
    class Meta:
        model = RentalApplication
        fields = '__all__'
