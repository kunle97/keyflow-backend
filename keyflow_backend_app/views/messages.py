from rest_framework import viewsets
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from ..serializers.user_serializer import UserSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.response import Response
from rest_framework import status
from ..models.user import User
from ..models.notification import Notification
from ..models.uploaded_file import UploadedFile
from rest_framework.views import APIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.core import serializers
from django.db.models import Q
from datetime import datetime
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
class UserThreadsListView(APIView):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["sender", "recipient"]  # Add fields you want to filter on
    search_fields = ["body"]  # Add fields you want to search on
    ordering_fields = ["timestamp"]  # Add fields you want to order on
    ordering = ["-timestamp"]  # Default ordering


    def get(self, request):
        logged_in_user = request.user

        # Get messages where the logged-in user is either the sender or recipient
        messages = Message.objects.filter(
            Q(sender=logged_in_user) | Q(recipient=logged_in_user)
        )

        # Group messages by sender and recipient
        conversations = {}
        for message in messages:
            other_user = (
                message.sender
                if message.recipient == logged_in_user
                else message.recipient
            )
            conversation_key = f"{min(logged_in_user.id, other_user.pk)}-{max(logged_in_user.id, other_user.pk)}"

            if conversation_key not in conversations:
                conversations[conversation_key] = {
                    "id": conversation_key,
                    "recipient_id": other_user.pk,
                    "user_data": UserSerializer(other_user).data,
                    "name": other_user.get_full_name(),  # Assuming get_full_name() retrieves the user's full name
                    "messages": [],
                    "latest_message_timestamp": None,  # Initialize latest message timestamp
                }

            # Update the latest message timestamp within the conversation
            message_timestamp = message.timestamp.replace(tzinfo=timezone.utc)  # Assuming message.timestamp is naive
            conversations[conversation_key]['latest_message_timestamp'] = max(
                conversations[conversation_key]['latest_message_timestamp'] or message_timestamp,
                message_timestamp
            )

            # Serializing file or providing file URL, modify as per your file handling
            file_info = None
            if message.file:
                file_info = UploadedFileSerializer(message.file).data

            conversations[conversation_key]["messages"].append(
                {
                    "id": message.pk,
                    "text": message.body,
                    "timestamp": message_timestamp,
                    "isSender": message.sender == logged_in_user,
                    "file": file_info,
                }
            )

        # Sort conversations by the latest message timestamp in each conversation (descending)
        sorted_conversations = sorted(
            conversations.values(),
            key=lambda x: x['latest_message_timestamp'] or timezone.datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        return Response(sorted_conversations)

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
        sender = User.objects.get(id=data["user"])
        body = data["body"]
        # CHeck if payload has a file attached and upload it then add the file to a variable
        if request.FILES:
            uploaded_file = request.FILES["file"]
            # Create a new uploaded file
            uploaded_file = UploadedFile.objects.create(
                user=sender, file=uploaded_file, subfolder="message"
            )
            # Add the uploaded file to the message
            message = Message.objects.create(
                sender=sender, recipient=recipient, body=body, file=uploaded_file
            )

        else:
            message = Message.objects.create(
                sender=sender, recipient=recipient, body=body
            )
            # Create notification for the recipient
            notification_title = (
                f"New Message from {sender.first_name} {sender.last_name}"
            )

        # Create notification for the recipient
        notification_title = f"New Message from {sender.first_name} {sender.last_name}"
        notification = Notification.objects.create(
            title=notification_title, message=body, user=recipient, type="message", resource_url=f"/dashboard/messages/"
        )
        # return a response with a success message and status code
        return Response(
            {"message": "Message sent successfully", "status": status.HTTP_201_CREATED},
            status=status.HTTP_201_CREATED,
        )
