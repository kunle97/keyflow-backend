from rest_framework import serializers
from keyflow_backend_app.models.portfolio import Portfolio
from ..models.rental_property import RentalProperty
from .rental_property_serializer import RentalPropertySerializer


class PortfolioSerializer(serializers.ModelSerializer):
    rental_properties = RentalPropertySerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = "__all__"
