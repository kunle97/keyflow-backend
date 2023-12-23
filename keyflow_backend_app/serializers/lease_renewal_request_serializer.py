from rest_framework import serializers
from keyflow_backend_app.models import rental_unit
from keyflow_backend_app.models.lease_renewal_request import LeaseRenewalRequest
from .rental_unit_serializer import RentalUnitSerializer
from .user_serializer import UserSerializer
from .lease_agreement_serializer import LeaseAgreementSerializer
from .rental_property_serializer import RentalPropertySerializer

class LeaseRenewalRequestSerializer(serializers.ModelSerializer):
    rental_unit = RentalUnitSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    tenant = UserSerializer(many=False, read_only=True)
    user = UserSerializer(many=False, read_only=True)
    class Meta:
        model = LeaseRenewalRequest
        fields = "__all__"