from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
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


class RetrieveRentalApplicationByApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
        serializer = RentalApplicationSerializer(rental_application)
        return Response(serializer.data, status=status.HTTP_200_OK)

def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))
class RentalApplicationViewSet(viewsets.ModelViewSet):
    queryset = RentalApplication.objects.all()
    serializer_class = RentalApplicationSerializer
    permission_classes = [
        RentalApplicationCreatePermission
    ]  # TODO: Investigate why IsResourceOwner is not working
    authentication_classes = [JWTAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["first_name", "last_name", "email", "phone_number"]
    ordering_fields = ["first_name", "last_name", "email", "phone_number", "created_at"]

    def get_queryset(self):
        user = self.request.user  # Get the current user
        queryset = super().get_queryset().filter(landlord=user)
        return queryset

    # OVerride the defualt create method to create a rental application and send a notification to the landlord
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        unit = RentalUnit.objects.get(id=data["unit_id"])
        user = unit.user
        rental_application = RentalApplication.objects.create(
            unit=unit,
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=data["date_of_birth"],
            email=data["email"],
            phone_number=data["phone_number"],
            desired_move_in_date=data["desired_move_in_date"],
            other_occupants=strtobool(data["other_occupants"]),
            pets= strtobool(data["pets"]),
            vehicles= strtobool(data["vehicles"]),
            convicted= strtobool(data["convicted"]),
            bankrupcy_filed= strtobool(data["bankrupcy"]),
            evicted= strtobool(data["evicted"]),
            employment_history=data["employment_history"],
            residential_history=data["residential_history"],
            landlord=user,
            comments=data["comments"],
        )
        # Create a notification for the landlord that a new rental application has been submitted
        notification = Notification.objects.create(
            user=user,
            message=f"{data['first_name']} {data['last_name']} has submitted a rental application for unit {rental_application.unit.name} at {rental_application.unit.rental_property.name}",
            type="rental_application_submitted",
            title="Rental Application Submitted",
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
        print(f"Reqeust User id: {request_user}")
        print(f"Landlord id: {rental_application.landlord.id}")
        if rental_application.landlord == request_user:
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
        if (
            request.user.is_authenticated
            and rental_application.landlord == request.user
        ):
            rental_application.is_approved = False
            rental_application.save()
            rental_application.delete()
            return Response({"message": "Rental application rejected successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )
