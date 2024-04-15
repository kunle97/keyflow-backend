from rest_framework import serializers
from ..models.expiring_token import ExpiringToken

class TokenValidationSerializer(serializers.Serializer):
    token = serializers.CharField()
