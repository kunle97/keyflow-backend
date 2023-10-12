from rest_framework import serializers
from .models import User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest, RentalApplication, Transaction, LeaseTerm,PasswordResetToken, Notification
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalProperty
        fields = '__all__'

class RentalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalUnit
        fields = '__all__'

class LeaseAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseAgreement
        fields = '__all__'

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = '__all__'

class LeaseCancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseCancellationRequest
        fields = '__all__'

class RentalApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalApplication
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

#Create serializers for Lease TErm
class LeaseTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseTerm
        fields = '__all__'

#Create serializers for PasswordResetToken
class PasswordResetTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetToken
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'