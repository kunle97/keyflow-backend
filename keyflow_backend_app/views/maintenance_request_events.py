from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated 
from rest_framework.response import Response
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.maintenance_request_event import MaintenanceRequestEvent
from keyflow_backend_app.models.user import User
from keyflow_backend_app.serializers.maintenance_request_event_serializer import MaintenanceRequestEventSerializer
from ..models.maintenance_request import MaintenanceRequest
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.decorators import action

class MaintenanceRequestEventViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "tenant__user__first_name",
        "tenant__user__last_name",
        "description",
        "status",
    ]
    ordering_fields = ["status", "created_at", "id"]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user  # Get the current user
        user = User.objects.get(id=user.id)
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            # REturn the queryset with the ordering_fields]
            return queryset
        elif user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(tenant=tenant)
            return queryset
