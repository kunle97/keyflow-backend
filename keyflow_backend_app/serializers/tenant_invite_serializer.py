from rest_framework import serializers
from ..models.tenant_invite import TenantInvite


class TenantInviteSerializer(serializers.ModelSerializer):
    #Createa  field that returns the rental unit name
    rental_unit_name = serializers.SerializerMethodField()

    #Create the get_rental_unit_name function'
    def get_rental_unit_name(self, obj):
        return obj.rental_unit.name
    class Meta:
        model = TenantInvite
        fields = "__all__"