from rest_framework import serializers
from ..models.lease_agreement import LeaseAgreement
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .rental_application_serializer import RentalApplicationSerializer
from .lease_template_serializer import LeaseTemplateSerializer
from .account_type_serializer import OwnerSerializer, TenantSerializer
from .tenant_invite_serializer import TenantInviteSerializer

class LeaseAgreementSerializer(serializers.ModelSerializer):
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    rental_application = RentalApplicationSerializer(many=False, read_only=True)
    lease_template = LeaseTemplateSerializer(many=False, read_only=True)
    tenant = TenantSerializer(many=False, read_only=True)
    owner = OwnerSerializer(many=False, read_only=True)
    rental_property = serializers.SerializerMethodField()  # New field for rental_property
    tenant_invite = TenantInviteSerializer(many=False, read_only=True)

    class Meta:
        model = LeaseAgreement
        fields = '__all__'

    def get_rental_property(self, obj):
        # Assuming rental_unit has a field named rental_property
        rental_property_obj = obj.rental_unit.rental_property
        rental_property_serializer = RentalPropertySerializer(rental_property_obj)  # Adjust serializer as per your project
        return rental_property_serializer.data