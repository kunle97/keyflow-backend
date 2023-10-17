from rest_framework import serializers
from ..models.rental_property import RentalProperty
from .rental_unit_serializer import RentalUnitSerializer
class RentalPropertySerializer(serializers.ModelSerializer):
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    class Meta:
        model = RentalProperty
        fields = '__all__'
