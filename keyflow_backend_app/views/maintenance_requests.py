from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.user import User
from ..models.maintenance_request import MaintenanceRequest
from ..models.maintenance_request_event import MaintenanceRequestEvent
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
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
    ordering_fields = ["tenant__user__last_name","status","description", "type", "priority", "created_at"]
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

        # Create a maintenance request event for the new maintenance request
        MaintenanceRequestEvent.objects.create(
            maintenance_request=maintenance_request,
            title="Maintenance Request Created",
            type="maintenance_request_created",
            description=f"A maintenance request has been created for {rental_unit.name} in {rental_property.name} by {tenant.user.first_name} {tenant.user.last_name}",
        )

        # Return a response with the new maintenance request
        return Response(
            MaintenanceRequestSerializer(maintenance_request).data,
            status=status.HTTP_201_CREATED,
        )

    # Create a function (partial update) to handle the PATCH requests for the maintenance request. It should create a maintenance request event only if the status or priority is changed.
    def partial_update(self, request, *args, **kwargs):
        user = self.request.user  # Get the current user
        user = User.objects.get(id=user.id)
        data = request.data.copy()
        maintenance_request = self.get_object()
        if "status" in data or "priority" in data:
            title = "Maintenance Request Updated"
            type = "maintenance_request_updated"
            description = ""
            if "status" in data:
                title = f"Status Update"
                #Remove underscores from the status
                data["status"] = data["status"].replace("_", " ")
                description = f"The status of this maintenance request has been updated to {data['status']}"
            elif "priority" in data:
                title = f"Priority Update"
                priority = ""
                if data["priority"] == "1":
                    priority = "Low"
                elif data["priority"] == "2":
                    priority = "Moderate"
                elif data["priority"] == "3":
                    priority = "High"
                elif data["priority"] == "4":
                    priority = "Urgent"
                elif data["priority"] == "5":
                    priority = "Emergency"
                print(data["priority"])
                print(f"Priorty: {priority}")
                description = f"The priority of this maintenance request has been updated to {priority}"
            MaintenanceRequestEvent.objects.create(
                maintenance_request=maintenance_request,
                title=title,
                type=type,
                description=description,
            )
        return super().partial_update(request, *args, **kwargs)
