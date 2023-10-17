from rest_framework import serializers
from ..models.password_reset_token import PasswordResetToken
#Create serializers for PasswordResetToken
class PasswordResetTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetToken
        fields = '__all__'
