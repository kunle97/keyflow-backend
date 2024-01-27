from rest_framework import serializers
from ..models.tenant_invite import TenantInvite


class TenantInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInvite
        fields = "__all__"