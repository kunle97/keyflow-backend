from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.user import User
from ..models.maintenance_request import MaintenanceRequest
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

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
