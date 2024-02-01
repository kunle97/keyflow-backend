from ..models.billing_entry import BillingEntry
from rest_framework import serializers

class BillingEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingEntry
        fields = '__all__'