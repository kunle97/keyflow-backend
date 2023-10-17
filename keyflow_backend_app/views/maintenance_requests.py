from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models.maintenance_request import MaintenanceRequest
from ..serializers.maintenance_request_serializer import (MaintenanceRequestSerializer)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    search_fields = ['description', 'status' ]
    ordering_fields = ['status','created_at', 'id']
    filterset_fields = ['status']
    def get_queryset(self):
        user = self.request.user  # Get the current user
        queryset = super().get_queryset().filter(landlord=user)
        return queryset