from rest_framework import serializers

class TokenValidationSerializer(serializers.Serializer):
    token = serializers.CharField()
