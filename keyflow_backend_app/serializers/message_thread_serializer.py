from rest_framework import serializers
from ..models.message import Message
from .user_serializer import UserSerializer
class MessageThreadSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(many=False, read_only=True)
    sender = UserSerializer(many=False, read_only=True)
    class Meta:
        model = Message
        fields = '__all__'
