from rest_framework import viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.user import User
from ..models.maintenance_request import MaintenanceRequest
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    authentication_classes = [JWTAuthentication]
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

    # Creat a function that handles the POST requests for the maintenance request. use the create function with request as a paramerter
    def create(self, request, *args, **kwargs):
        user = self.request.user  # Get the current user
        user = User.objects.get(id=user.id)
        data = request.data.copy()
        print(data)
        rental_unit = RentalUnit.objects.get(id=data["rental_unit"])
        rental_property = RentalProperty.objects.get(id=data["rental_property"])
        description = data["description"]
        tenant = Tenant.objects.get(id=data["tenant"])
        type = data["type"]
        owner = Owner.objects.get(id=data["owner"])

        # Create a new maintenance request
        maintenance_request = MaintenanceRequest.objects.create(
            rental_property=rental_property,
            rental_unit=rental_unit,
            description=description,
            tenant=tenant,
            type=type,
            owner=owner,
        )

        # Return a response with the new maintenance request
        return Response(
            MaintenanceRequestSerializer(maintenance_request).data,
            status=status.HTTP_201_CREATED,
        )
