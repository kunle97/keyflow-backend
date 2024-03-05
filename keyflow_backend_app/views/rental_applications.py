from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from keyflow_backend_app.models.account_type import Owner
from ..models.user import User
from ..models.notification import Notification
from ..models.rental_application import RentalApplication
from ..models.rental_unit import RentalUnit
from ..serializers.rental_application_serializer import RentalApplicationSerializer
from ..permissions import RentalApplicationCreatePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..helpers import strtobool


class RetrieveRentalApplicationByApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
        serializer = RentalApplicationSerializer(rental_application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RentalApplicationViewSet(viewsets.ModelViewSet):
    queryset = RentalApplication.objects.all()
    serializer_class = RentalApplicationSerializer
    permission_classes = [
        IsAuthenticated,
        RentalApplicationCreatePermission,
    ]  # TODO: Investigate why IsResourceOwner is not working
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["first_name", "last_name", "email", "phone_number"]
    ordering_fields =  [ "first_name","last_name", "email","phone_number","created_at","is_approved"]

    def get_queryset(self):
        user = self.request.user  # Get the current user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    def get_permissions(self):
        # Allow unauthenticated users to access the create method
        if self.action == "create":
            return []
        return [IsAuthenticated()]

    # OVerride the defualt create method to create a rental application and send a notification to the landlord
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        unit = RentalUnit.objects.get(id=data["unit_id"])
        user = unit.owner.user
        owner = unit.owner
        rental_application = RentalApplication.objects.create(
            unit=unit,
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=data["date_of_birth"],
            email=data["email"],
            phone_number=data["phone_number"],
            desired_move_in_date=data["desired_move_in_date"],
            other_occupants=strtobool(data["other_occupants"]),
            pets=strtobool(data["pets"]),
            vehicles=strtobool(data["vehicles"]),
            convicted=strtobool(data["convicted"]),
            bankrupcy_filed=strtobool(data["bankrupcy"]),
            evicted=strtobool(data["evicted"]),
            employment_history=data["employment_history"],
            residential_history=data["residential_history"],
            owner=owner,
            comments=data["comments"],
        )
        # Create a notification for the landlord that a new rental application has been submitted
        notification = Notification.objects.create(
            user=user,
            message=f"{data['first_name']} {data['last_name']} has submitted a rental application for unit {rental_application.unit.name} at {rental_application.unit.rental_property.name}",
            type="rental_application_submitted",
            title="Rental Application Submitted",
            resource_url=f"/dashboard/landlord/rental-applications/{rental_application.id}",
        )
        return Response({"message": "Rental application created successfully."})

    # Create method to delete all rental applications for a specific unit
    @action(
        detail=True, methods=["delete"], url_path="delete-remaining-rental-applications"
    )
    def delete_remaining_rental_applications(self, request, pk=None):
        application = self.get_object()
        rental_applications = RentalApplication.objects.filter(
            unit=application.unit, is_archived=False
        )
        rental_applications.delete()
        return Response({"message": "Rental applications deleted successfully."})

    # Create a method to approve a rental application
    @action(detail=True, methods=["post"], url_path="approve-rental-application")
    def approve_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        request_user = request.data.get("user_id")
        user = User.objects.get(id=request_user)
        owner = Owner.objects.get(user=user)
        if rental_application.user == owner:
            rental_application.is_approved = True
            rental_application.save()
            return Response({"message": "Rental application approved successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )

    # Create a method to reject and delete a rental application
    @action(detail=True, methods=["post"], url_path="reject-rental-application")
    def reject_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        if request.user.is_authenticated and rental_application.landlord == owner:
            rental_application.is_approved = False
            rental_application.save()
            rental_application.delete()
            return Response({"message": "Rental application rejected successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )
