from os import read
from ..models.billing_entry import BillingEntry
from rest_framework import serializers
from .account_type_serializer import TenantSerializer
from .rental_unit_serializer import RentalUnitSerializer


class BillingEntrySerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(many=False, read_only=False)
    rental_unit = RentalUnitSerializer(many=False, read_only=False)

    class Meta:
        model = BillingEntry
        fields = "__all__"
