from rest_framework import generics
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView

class MessageThreadListView(APIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sender', 'recipient']