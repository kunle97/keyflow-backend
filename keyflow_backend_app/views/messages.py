from rest_framework import viewsets
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.response import Response
from rest_framework import status
from ..models.user import User
from ..models.notification import Notification


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["body", "timestamp", "sender", "recipient"]
    search_fields = ["body", "sender", "recipient"]
    ordering_fields = ["sender", "recipient", "timestamp"]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(
            recipient=user
        )

    # override post method uising create method to create a message
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        recipient = User.objects.get(id=data["recipient"])
        sender = User.objects.get(id=data["sender"])
        body = data["body"]
        message = Message.objects.create(sender=sender, recipient=recipient, body=body)
        # Create notification for the recipient
        notification_title = f"New Message from {sender.first_name} {sender.last_name}"

        notification = Notification.objects.create(
            title=notification_title, message=body, user=recipient, type="message"
        )
        # return a response with a success message and status code
        return Response(
            {"message": "Message sent successfully", "status": status.HTTP_201_CREATED},
            status=status.HTTP_201_CREATED,
        )
