import os
import json
from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from keyflow_backend_app.helpers.helpers import make_id
from postmarker.core import PostmarkClient
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.tenant_invite import TenantInvite
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.models.account_type import Owner
from django_filters.rest_framework import DjangoFilterBackend
from keyflow_backend_app.serializers.tenant_invite_serializer import (
    TenantInviteSerializer,
)
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.parsers import MultiPartParser
from ..permissions.tenant_invite_permissions import IsOwner
load_dotenv()


class TenantInviteViewSet(viewsets.ModelViewSet):
    queryset = TenantInvite.objects.all()
    serializer_class = TenantInviteSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [
        IsAuthenticated,
        IsOwner,
    ]  # TODO: Add IsResourceOwner, PropertyCreatePermission, PropertyDeletePermission permissions
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
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

    # Create a create function that overrides the default create function that creates a tenant invite and sends an email to the tenant
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        owner = Owner.objects.get(user=self.request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(
            raise_exception=True
        )  # TODO: Add validation for email and rental unit
        serializer.save(owner=owner)
        tenant_invite = TenantInvite.objects.get(id=serializer.data["id"])
        # Create Lease Agreement
        rental_unit = RentalUnit.objects.get(id=data["rental_unit"])
        approval_hash = make_id(64)
        tenant_invite.approval_hash = approval_hash
        tenant_invite.save()
        email_content = ""
        redirect_url = ""
        # Set document_id or signed_lease_document_file
        if rental_unit.signed_lease_document_file:
            signed_lease_document_file = rental_unit.signed_lease_document_file
            signed_lease_document_file_metadata = json.loads(rental_unit.signed_lease_document_metadata)
            start_date = signed_lease_document_file_metadata['lease_start_date']
            end_date = signed_lease_document_file_metadata['lease_end_date']
            date_signed = signed_lease_document_file_metadata['date_signed']
            lease_agreement = LeaseAgreement.objects.create(
                owner=owner,
                rental_unit=rental_unit,
                approval_hash=approval_hash,
                signed_lease_document_file=signed_lease_document_file,
                start_date=start_date,
                end_date=end_date,
                signed_date=date_signed,
                is_tenant_invite=True,
                is_active=True,
                tenant_invite=tenant_invite,
                lease_terms=rental_unit.lease_terms
            )
            redirect_url = f"{os.getenv('CLIENT_HOSTNAME')}/dashboard/tenant/register/{lease_agreement.id}/{rental_unit.id}/{approval_hash}/"
            email_content = f"Hi {serializer.data['first_name']},<br><br> You have been invited to join Keyflow and manage your rental in {rental_unit.name} at {rental_unit.rental_property.name}.<br><br> Please click <a href='{redirect_url}'>here</a> to register and manage your lease.<br><br>Thanks,<br>Keyflow Team"

        elif rental_unit.template_id:
            document_id = data["boldsign_document_id"]

            lease_agreement = LeaseAgreement.objects.create(
                owner=owner,
                rental_unit=rental_unit,
                approval_hash=approval_hash,
                is_tenant_invite=True,
                tenant_invite=tenant_invite,
                document_id=document_id,
                lease_terms=rental_unit.lease_terms
            )
            redirect_url = f"{os.getenv('CLIENT_HOSTNAME')}/sign-lease-agreement/{lease_agreement.id}/{approval_hash}"  # TODO: CHANGE THIS TO THE ACTUAL LINK
            email_content = f"Hi {serializer.data['first_name']},<br><br> You have been invited to join Keyflow and manage your rental in {rental_unit.name} at {rental_unit.rental_property.name}.<br><br> Please click <a href='{redirect_url}'>here</a> to sign your lease.<br><br>Thanks,<br>Keyflow Team"


        # Send email to tenant via Postmark
        if os.getenv("ENVIRONMENT") == "production":
            #Create an email notification using postmark for the tenant that a new invoice has been recieved
            postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
            to_email = tenant_invite.email
            if os.getenv("ENVIRONMENT") == "development":
                to_email = "keyflowsoftware@gmail.com"
            else:
                to_email = tenant_invite.email
            postmark.emails.send(
                From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                To=to_email,
                Subject="Your owner has invited to join Keyflow",
                HtmlBody=email_content
            )
        return Response(
            {"data": serializer.data, "redirect_url": redirect_url},
            status=status.HTTP_201_CREATED,
        )
    #Creata a destroy function that will be used to override the DELETE method. In addition to deleting the tenant invite, it will also delete the lease agreement
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        #Check if the lease agreement exists
        if  LeaseAgreement.objects.filter(approval_hash=instance.approval_hash).exists():

            lease_agreement = LeaseAgreement.objects.get(approval_hash=instance.approval_hash)
            document_id = lease_agreement.document_id
            try:
                if document_id:
                    response = lease_agreement.revoke_boldsign_document()
                lease_agreement.delete()
            except Exception as e:
                return Response(
                    {"message": "Error deleting lease agreement"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    


    '''

    # @action(
    #     detail=False, methods=["post"], url_path="upload-csv-tenants"
    # )  # POST: api/tenant-invites/upload-csv-tenants
    # def upload_csv_tenants(self, request, pk=None):
    #     file_obj = request.FILES["file"]

    #     # Assuming your CSV file has columns: name, beds, baths, size
    #     # You might need to adjust the column names based on your actual CSV file structure
    #     try:
    #         decoded_file = TextIOWrapper(file_obj.file, encoding="utf-8")
    #         csv_reader = csv.DictReader(decoded_file)

    #         user = request.user
    #         owner = Owner.objects.get(user=user)

    #         keys_to_handle = ["first_name", "last_name", "email"]

    #         for row in csv_reader:
    #             # Use a dictionary comprehension to handle keys and strip values
    #             tenant_invite_data = {
    #                 key: row.get(key, "").strip() if row.get(key) else None
    #                 for key in keys_to_handle
    #             }

    #             # Create RentalProperty object
    #             tenant_invite = TenantInvite.objects.create(
    #                 owner=owner,
    #                 **tenant_invite_data,  # Unpack the dictionary into keyword arguments
    #             )
    #             rental_unit = tenant_invite.rental_unit
    #             approval_hash = make_id(64)
    #             email_content = ""
    #             redirect_url = ""
    #             # Set document_id or signed_lease_document_file
    #             if rental_unit.signed_lease_document_file:
    #                 signed_lease_document_file = rental_unit.signed_lease_document_file
    #                 signed_lease_document_file_metadata = json.loads(rental_unit.signed_lease_document_metadata)
    #                 start_date = signed_lease_document_file_metadata['lease_start_date']
    #                 end_date = signed_lease_document_file_metadata['lease_end_date']
    #                 date_signed = signed_lease_document_file_metadata['date_signed']
    #                 lease_agreement = LeaseAgreement.objects.create(
    #                     owner=owner,
    #                     rental_unit=rental_unit,
    #                     approval_hash=approval_hash,
    #                     signed_lease_document_file=signed_lease_document_file,
    #                     start_date=start_date,
    #                     end_date=end_date,
    #                     signed_date=date_signed,
    #                     is_tenant_invite=True,
    #                     is_active=True,
    #                     tenant_invite=tenant_invite,
    #                 )
    #                 redirect_url = f"{os.getenv('CLIENT_HOSTNAME')}/dashboard/tenant/register/{lease_agreement.id}/{rental_unit.id}/{approval_hash}/"
    #                 email_content = f"Hi {tenant_invite.first_name},<br><br> You have been invited to join Keyflow and manage your rental in {rental_unit.name} at {rental_unit.rental_property.name}.<br><br> Please click <a href='{redirect_url}'>here</a> to register and manage your lease.<br><br>Thanks,<br>Keyflow Team"

    #             elif rental_unit.template_id:
    #                 document_id = data["boldsign_document_id"]
    #                 lease_agreement = LeaseAgreement.objects.create(
    #                     owner=owner,
    #                     rental_unit=rental_unit,
    #                     approval_hash=approval_hash,
    #                     is_tenant_invite=True,
    #                     tenant_invite=tenant_invite,
    #                     document_id=document_id
    #                 )
    #                 redirect_url = f"{os.getenv('CLIENT_HOSTNAME')}/sign-lease-agreement/{lease_agreement.id}/{approval_hash}"  # TODO: CHANGE THIS TO THE ACTUAL LINK
    #                 email_content = f"Hi {tenant_invite.first_name},<br><br> You have been invited to join Keyflow and manage your rental in {rental_unit.name} at {rental_unit.rental_property.name}.<br><br> Please click <a href='{redirect_url}'>here</a> to sign your lease.<br><br>Thanks,<br>Keyflow Team"


    #             # Send email to tenant via Postmark
    #             if os.getenv("ENVIRONMENT") == "production":
    #                 #Create an email notification using postmark for the tenant that a new invoice has been recieved
    #                 postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
    #                 to_email = tenant_invite.email
    #                 if os.getenv("ENVIRONMENT") == "development":
    #                     to_email = "keyflowsoftware@gmail.com"
    #                 else:
    #                     to_email = tenant_invite.email
    #                 postmark.emails.send(
    #                     From=os.getenv("KEYFLOW_SENDER_EMAIL"),
    #                     To=to_email,
    #                     Subject="Your owner has invited to join Keyflow",
    #                     HtmlBody=email_content
    #                 )

    #                 return Response(
    #                     {"message": "Units created successfully."},
    #                     status=status.HTTP_201_CREATED,
    #                 )

    #     except ValidationError as e:
    #         return Response(
    #             {"message": f"Error processing CSV: {e}"},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
    '''