from rest_framework import serializers
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from .user_serializer import UserSerializer
from .rental_unit_serializer import RentalUnitSerializer
from .rental_property_serializer import RentalPropertySerializer
from .lease_agreement_serializer import LeaseAgreementSerializer
class LeaseCancellationRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    unit = RentalUnitSerializer(many=False, read_only=True)
    lease_agreement = LeaseAgreementSerializer(many=False, read_only=True)
    rental_property = RentalPropertySerializer(many=False, read_only=True)
    
    class Meta:
        model = LeaseCancellationRequest
        fields = '__all__'