import os
import json
from postmarker.core import PostmarkClient
from rest_framework import viewsets
from keyflow_backend_app.models.account_type import Owner, Tenant
from ..models.message import Message
from ..serializers.message_serializer import MessageSerializer
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from ..serializers.user_serializer import UserSerializer
from rest_framework.authentication import SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
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
from django.db.models import Q,Max
from django.utils import timezone
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
                    # "user_data": UserSerializer(other_user).data,
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
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)

    def create(self, request, *args, **kwargs):
        # Existing create method logic
        data = request.data.copy()
        recipient = None
        sender = User.objects.get(id=data["sender"])
        body = data["body"]
        preferences = {}

        if request.user.account_type == "owner":
            tenant_user = User.objects.get(id=data["recipient"])
            tenant = Tenant.objects.get(user=tenant_user)
            preferences = json.loads(tenant.preferences)
            recipient = tenant_user
        elif request.user.account_type == "tenant":
            owner_user = User.objects.get(id=data["recipient"])
            owner = Owner.objects.get(user=owner_user)
            preferences = json.loads(owner.preferences)
            recipient = owner_user

        if request.FILES:
            uploaded_file = request.FILES["file"]
            uploaded_file = UploadedFile.objects.create(
                user=sender, file=uploaded_file, subfolder="message"
            )
            message = Message.objects.create(
                sender=sender, recipient=recipient, body=body, file=uploaded_file
            )
        else:
            message = Message.objects.create(
                sender=sender, recipient=recipient, body=body
            )
        notification_title = f"New Message from {sender.first_name} {sender.last_name}"

        try:
            message_recieved_preferences = next(
                (item for item in preferences if item["name"] == "message_received"), None
            )
            message_recieved_preferences_values = message_recieved_preferences["values"]
            for value in message_recieved_preferences_values:
                if value["name"] == "push" and value["value"] == True:
                    notification = Notification.objects.create(
                        title=notification_title, message=body, user=recipient, type="message", resource_url=f"/dashboard/messages/"
                    )
                if value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = recipient.email if os.getenv("ENVIRONMENT") != "development" else "keyflowsoftware@gmail.com"
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject=f"New Message from {sender.first_name} {sender.last_name}",
                        HtmlBody=f"<p>{body}</p><p><a href='{client_hostname}/dashboard/messages/'>View Message</a></p>",
                    )
        except (StopIteration, KeyError):
            pass

        return Response(
            {"message": "Message sent successfully", "status": status.HTTP_201_CREATED},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="retrieve-unread-messages-count")
    def retrieve_unread_messages_count(self, request):
        user = request.user
        unread_messages_count = Message.objects.filter(recipient=user, is_read=False).count()
        return Response({"unread_messages_count": unread_messages_count})

    @action(detail=False, methods=["patch"], url_path="set-messages-thread-as-read")
    def set_messages_thread_as_read(self, request):
        user = request.user
        other_user = User.objects.get(id=request.data.get("other_user_id"))
        unread_messages = Message.objects.filter(recipient=user, sender=other_user, is_read=False)
        unread_messages.update(is_read=True)
        return Response({"message": "Messages set as read successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="list-threads")
    def list_threads(self, request):
        logged_in_user = request.user
        messages = Message.objects.filter(Q(sender=logged_in_user) | Q(recipient=logged_in_user)).values('sender', 'recipient').annotate(latest_message_timestamp=Max('timestamp'))
        threads = {}
        for msg in messages:
            other_user_id = msg['recipient'] if msg['sender'] == logged_in_user.id else msg['sender']
            other_user = User.objects.get(pk=other_user_id)
            thread_id = f"{min(logged_in_user.id, other_user.pk)}-{max(logged_in_user.id, other_user.pk)}"
            #Retrieve most recent message in the thread
            most_recent_message = Message.objects.filter(Q(sender=logged_in_user, recipient=other_user) | Q(sender=other_user, recipient=logged_in_user)).order_by('-timestamp').first()
            #Retrieve number of unread messages in the thread
            unread_messages_count = Message.objects.filter(sender=other_user, recipient=logged_in_user, is_read=False).count()
            if thread_id not in threads:
                threads[thread_id] = {
                    "id": thread_id,
                    "recipient_id": other_user.pk,
                    "name": other_user.get_full_name(),
                    "latest_message_timestamp": msg['latest_message_timestamp'],
                    "latest_message": most_recent_message.body,
                    "unread_messages_count": unread_messages_count,
                }
        sorted_threads = sorted(threads.values(), key=lambda x: x['latest_message_timestamp'] or timezone.datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return Response(sorted_threads)

    @action(detail=False, methods=["get"], url_path="list-thread-messages")
    def list_thread_messages(self, request, pk=None):
        logged_in_user = request.user
        thread_id = request.query_params.get("thread_id")
        
        if not thread_id:
            return Response({"error": "Thread ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_ids = thread_id.split('-')
        if len(user_ids) != 2:
            return Response({"error": "Invalid thread ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user1_id = int(user_ids[0])
            user2_id = int(user_ids[1])
        except ValueError:
            return Response({"error": "Invalid user IDs in thread ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        if logged_in_user.id not in [user1_id, user2_id]:
            return Response({"error": "User not part of the conversation"}, status=status.HTTP_403_FORBIDDEN)
        
        messages = Message.objects.filter(
            (Q(sender_id=user1_id) & Q(recipient_id=user2_id)) | 
            (Q(sender_id=user2_id) & Q(recipient_id=user1_id))
        ).order_by('timestamp')
        
        serialized_messages = []
        for message in messages:
            file_info = None
            if message.file:
                file_info = UploadedFileSerializer(message.file).data
            serialized_messages.append({
                "id": message.pk,
                "text": message.body,
                "timestamp": message.timestamp.replace(tzinfo=timezone.utc),
                "isSender": message.sender == logged_in_user,
                "isRead": message.is_read,
                "file": file_info,
            })
        
        return Response(serialized_messages)