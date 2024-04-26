from rest_framework import serializers
from ..models.rental_property import RentalProperty
from .rental_unit_serializer import RentalUnitSerializer
class RentalPropertySerializer(serializers.ModelSerializer):
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    #Create a variable to show all the units related to the property
    rental_units = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = RentalProperty
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': True},  # example: set read_only for fields if needed
            'other_nullable_field': {'allow_null': True},  # adjust as needed
        }