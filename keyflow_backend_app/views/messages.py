from rest_framework import viewsets
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['body', 'timestamp', 'sender', 'recipient']
    search_fields = ['body', 'sender', 'recipient']
    ordering_fields = ['sender', 'recipient', 'timestamp']

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)