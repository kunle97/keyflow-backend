import os
import json
from postmarker.core import PostmarkClient
from rest_framework import viewsets
from keyflow_backend_app.models.account_type import Owner, Tenant
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from ..serializers.user_serializer import UserSerializer
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated 
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
from rest_framework.decorators import action

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
                    "isRead": message.is_read,
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
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
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
        recipient = None
        sender = User.objects.get(id=data["sender"])
        body = data["body"]
        preferences = {}

        if request.user.account_type == "owner":#If owner is sending a message
            tenant_user = User.objects.get(id=data["recipient"])
            tenant = Tenant.objects.get(user=tenant_user)
            preferences = json.loads(tenant.preferences)
            recipient = tenant_user
        elif request.user.account_type == "tenant":#If tenant is sending a message
            owner = Owner.objects.get(id=data["recipient"])
            preferences = json.loads(owner.preferences)
            recipient = owner.user

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
        

        try:
            message_recieved_preferences = next(
                (item for item in preferences if item["name"] == "message_received"), None
            )
            message_recieved_preferences_values = message_recieved_preferences["values"]
            for value in message_recieved_preferences_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create notification for the recipient
                    notification_title = f"New Message from {sender.first_name} {sender.last_name}"

                    notification = Notification.objects.create(
                        title=notification_title, message=body, user=recipient, type="message", resource_url=f"/dashboard/messages/"
                    )
                if value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the recipient
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = recipient.email
                    # Send email to recipient
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject=f"New Message from {sender.first_name} {sender.last_name}",
                        HtmlBody=f"<p>{body}</p><p><a href='{client_hostname}/dashboard/messages/'>View Message</a></p>",
                    )
        except StopIteration:
            # Handle case where "message_received" is not found
            print("message_received not found. Notification not sent.")
            pass
        except KeyError:
            # Handle case where "values" key is missing in "message_received"
            print("values key not found in message_received. Notification not sent.")
            pass
        
        # return a response with a success message and status code
        return Response(
            {"message": "Message sent successfully", "status": status.HTTP_201_CREATED},
            status=status.HTTP_201_CREATED,
        )

    #Create a function that returns the users number of unread messages. call the function name retrieve_unread_messages_count and url_path retrieve-unread-messages-count
    @action(detail=False, methods=["get"], url_path="retrieve-unread-messages-count")
    def retrieve_unread_messages_count(self, request):
        user = request.user
        unread_messages_count = Message.objects.filter(
            recipient=user, is_read=False
        ).count()
        return Response({"unread_messages_count": unread_messages_count})
     
     #Create a function that sets messages to read. call the function name set_messages_as_read and url_path set-messages-as-read
    @action(detail=False, methods=["patch"], url_path="set-messages-thread-as-read")
    def set_messages_thread_as_read(self, request):
        user = request.user
        other_user = User.objects.get(id=request.data.get("other_user_id"))
        #GEt unread messages from when the user is the recipient and the sender is the recipient_user and when the user is the sender and the recipient is the recipient_user
        unread_messages = Message.objects.filter(
            recipient=user, sender=other_user, is_read=False
        ) 

        unread_messages.update(is_read=True)
        return Response(
            {"message": "Messages set as read successfully"},
            status=status.HTTP_200_OK,
        )