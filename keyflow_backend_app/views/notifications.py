import os
from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from ..models.notification import Notification
from ..serializers.notification_serializer import NotificationSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

load_dotenv()


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['message', 'is_read', 'type']
    search_fields = ['message']
    ordering_fields = ['user', 'is_read', 'timestamp']

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
