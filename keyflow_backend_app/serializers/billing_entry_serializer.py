from os import read
from ..models.billing_entry import BillingEntry
from rest_framework import serializers
from .account_type_serializer import TenantSerializer


class BillingEntrySerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=False)

    class Meta:
        model = BillingEntry
        fields = "__all__"
