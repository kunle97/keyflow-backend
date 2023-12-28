from rest_framework import serializers
from ..models.transaction import Transaction
from .user_serializer import UserSerializer
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer

class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    class Meta:
        model = Transaction
        fields = '__all__'
