from rest_framework import serializers
from ..models.rental_unit import RentalUnit 

class RentalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalUnit
        fields = '__all__'
