from rest_framework import serializers
from ..models.lease_agreement import LeaseAgreement
from .rental_unit_serializer import RentalUnitSerializer
from .rental_application_serializer import RentalApplicationSerializer
from .lease_term_serializer import LeaseTermSerializer
from .user_serializer import UserSerializer
class LeaseAgreementSerializer(serializers.ModelSerializer):
    unit = RentalUnitSerializer(many=False, read_only=True)
    rental_application = RentalApplicationSerializer(many=False, read_only=True)
    lease_term = LeaseTermSerializer(many=False, read_only=True)
    tenant = UserSerializer(many=False, read_only=True)
    user = UserSerializer(many=False, read_only=True)


    class Meta:
        model = LeaseAgreement
        fields = '__all__'
