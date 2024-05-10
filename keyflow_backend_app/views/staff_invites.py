import os
import json
from postmarker.core import PostmarkClient
from django.shortcuts import redirect
from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from keyflow_backend_app.helpers import make_id
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.staff_invite import StaffInvite
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.models.account_type import Owner
from django_filters.rest_framework import DjangoFilterBackend
from keyflow_backend_app.serializers.staff_invite_serializer import StaffInviteSerializer
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
import csv
from rest_framework.parsers import MultiPartParser
from django.core.exceptions import ValidationError
from io import TextIOWrapper

load_dotenv()


class StaffInviteViewSet(viewsets.ModelViewSet):
    queryset = StaffInvite.objects.all()
    serializer_class = StaffInviteSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [
        IsAuthenticated
    ]  # TODO: Add IsResourceOwner, PropertyCreatePermission, PropertyDeletePermission permissions
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["first_name", "last_name", "email", "created_at"]
    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["first_name", "last_name", "email"]

    def get_queryset(self):
        owner = Owner.objects.get(user=self.request.user)
        return super().get_queryset().filter(owner=owner)

    # Create a create function that overrides the default create function that creates a staff invite and sends an email to the staff
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        owner = Owner.objects.get(user=self.request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(
            raise_exception=True
        )  # TODO: Add validation for email and rental unit
        serializer.save(owner=owner)
        staff_invite = StaffInvite.objects.get(id=serializer.data["id"])
        # Create Lease Agreement
        approval_hash = make_id(64)
        staff_invite.approval_hash = approval_hash
        staff_invite.save()
        email_subject = "Registration Link for Keyflow Staff Portal"
        registration_url = f"{os.getenv('CLIENT_HOSTNAME')}/dashboard/staff/register/{owner.id}/{staff_invite.id}/{approval_hash}/"
        email_content = f"Hi {serializer.data['first_name']},<br><br> You have been invited to join Keyflow as a staff member.<br><br> Please click <a href='{registration_url}'>here</a> to register and manage your lease.<br><br>Thanks,<br>Keyflow Team"
        # Send email to staff using postmark 
        if os.getenv("ENVIRONMENT") == "production":
            #Send Activation Email
            postmark = PostmarkClient(server_token=os.getenv('POSTMARK_SERVER_TOKEN'))
            postmark.emails.send(
                From=os.getenv('POSTMARK_SENDER_EMAIL'),
                To=serializer.data["email"],
                Subject=email_subject,
                HtmlBody=email_content,
            )
        return Response(
            {"data": serializer.data, "redirect_url": registration_url},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False, methods=["post"], url_path="upload-csv-staff"
    )  # POST: api/staff-invites/upload-csv-staff
    def upload_csv_staff(self, request, pk=None):
        file_obj = request.FILES["file"]

        # Assuming your CSV file has columns: name, beds, baths, size
        # You might need to adjust the column names based on your actual CSV file structure
        try:
            decoded_file = TextIOWrapper(file_obj.file, encoding="utf-8")
            csv_reader = csv.DictReader(decoded_file)

            user = request.user
            owner = Owner.objects.get(user=user)

            keys_to_handle = ["first_name", "last_name", "email"]

            for row in csv_reader:
                # Use a dictionary comprehension to handle keys and strip values
                staff_invite_data = {
                    key: row.get(key, "").strip() if row.get(key) else None
                    for key in keys_to_handle
                }

                # Create RentalProperty object
                StaffInvite.objects.create(
                    owner=owner,
                    **staff_invite_data,  # Unpack the dictionary into keyword arguments
                )

                # Send email to staff using postmark
                if os.getenv("ENVIRONMENT") == "production":
                    # Send Activation Email
                    postmark = PostmarkClient(
                        server_token=os.getenv("POSTMARK_SERVER_TOKEN")
                    )
                    postmark.emails.send(
                        From=os.getenv("POSTMARK_SENDER_EMAIL"),
                        To=staff_invite_data["email"],
                        Subject="Registration Link for Keyflow Staff Portal",
                        HtmlBody=f"Hi {staff_invite_data['first_name']},<br><br> You have been invited to join Keyflow and manage your rental.<br><br> Please click <a href='{os.getenv('CLIENT_HOSTNAME')}/dashboard/staff/register/'>here</a> to register and manage your lease.<br><br>Thanks,<br>Keyflow Team",
                    )


            return Response(
                {"message": "Staff invites created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {"message": f"Error processing CSV: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
