from rest_framework import serializers
from ..models.staff_invite import StaffInvite


class StaffInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffInvite
        fields = "__all__"