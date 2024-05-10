
from django.shortcuts import redirect
from dotenv import load_dotenv
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from keyflow_backend_app.models.account_type import Owner, Staff, Tenant
from keyflow_backend_app.models.user import User
from keyflow_backend_app.serializers.task_serializer import TaskSerializer
from keyflow_backend_app.serializers.tenant_invite_serializer import (
    TenantInviteSerializer,
)
from keyflow_backend_app.models.task import Task
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
import csv
from rest_framework.parsers import MultiPartParser
from django.core.exceptions import ValidationError
from io import TextIOWrapper

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [
        IsAuthenticated
    ]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "staff__user__first_name",
        "staff__user__last_name",
        "title",
        "description",
        "status",
    ]
    ordering_fields = ["status", "created_at", "due_date", "start_date", "completed_date"]
    filterset_fields = ["status", "due_date", "start_date", "completed_date"]

    def get_queryset(self):
        user = self.request.user  # Get the current user
        user = User.objects.get(id=user.id)
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            # REturn the queryset with the ordering_fields]
            return queryset
        elif user.account_type == "staff":
            staff = Staff.objects.get(user=user)
            queryset = super().get_queryset().filter(staff=staff)
            return queryset