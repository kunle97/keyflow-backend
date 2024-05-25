from rest_framework import serializers
from ..models.lease_template import LeaseTemplate
from  .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .portfolio_serializer import PortfolioSerializer
from .account_type_serializer import OwnerSerializer

#Create serializers for Lease Template
class LeaseTemplateSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(many=False, read_only=True)
    units = RentalUnitSerializer(many=True, read_only=True, source='rental_units')
    rental_properties = RentalPropertySerializer(many=True, read_only=True)
    portfolios = PortfolioSerializer(many=True, read_only=True)
    class Meta:
        model = LeaseTemplate
        fields = '__all__'
