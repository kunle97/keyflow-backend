from rest_framework import serializers

from keyflow_backend_app.models import rental_property
from ..models.rental_unit import RentalUnit
from ..models.rental_property import RentalProperty


class RentalUnitSerializer(serializers.ModelSerializer):
    rental_property_name = serializers.SerializerMethodField()

    class Meta:
        model = RentalUnit
        fields = "__all__"

    # 
    def get_rental_property_name(self, obj):
        return obj.rental_property.name  # Replace 'name' with the field you want to display
