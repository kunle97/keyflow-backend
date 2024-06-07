import os
import json
from requests import delete
import stripe
from postmarker.core import PostmarkClient
from django.http import JsonResponse
from dotenv import load_dotenv
from datetime import datetime, timedelta
from django.utils import timezone 
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 
from keyflow_backend_app.models import lease_renewal_request
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.uploaded_file import UploadedFile

from keyflow_backend_app.models.user import User
from ..models.notification import Notification
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.rental_application import RentalApplication
from ..models.notification import Notification
from ..models.lease_template import LeaseTemplate
from ..models.lease_renewal_request import LeaseRenewalRequest
from ..serializers.lease_agreement_serializer import LeaseAgreementSerializer
from ..permissions import (
    IsOwnerOrReadOnly,
    IsResourceOwner,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


load_dotenv()


class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly, IsResourceOwner]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "tenant__first_name",
        "tenant__last_name",
        "is_active",
        "start_date",
        "end_date",
    ]
    ordering_fields = [
        "tenant__first_name",
        "tenant__last_name",
        "is_active",
        "start_date",
        "end_date",
        "created_at",
    ]
    filterset_fields = ["is_active", "start_date", "end_date", "created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            return queryset
        if user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(tenant=tenant)
            return queryset


    # Create a function to override the create method to create a lease agreement
    def create(self, request, *args, **kwargs):
        owner = Owner.objects.get(user=request.user)
        lease_agreement = None
        # Retrieve rental_application from the request
        rental_application_id = request.data.get("rental_application")
        # Retrieve the unit id from the request
        unit_id = request.data.get("rental_unit")
        # Retrieve the unit object from the database
        unit = RentalUnit.objects.get(id=unit_id)
        approval_hash = request.data.get("approval_hash")
        # Check if  request.data.get("lease_renewal_request") exists if not set it to none
        lease_renewal_request = None
        if request.data.get("lease_renewal_request"):
            lease_renewal_request = LeaseRenewalRequest.objects.get(
                id=request.data.get("lease_renewal_request")
            )

        # Check if tenant exists if lease is being created on a lease renewal request
        tenant = None
        if request.data.get("tenant"):
            tenant = Tenant.objects.get(id=request.data.get("tenant"))

        # Check if start_date exists if lease is being created on a lease renewal request
        start_date = None
        if request.data.get("start_date"):
            start_date = request.data.get("start_date")

        # Check if end_date exists if lease is being created on a lease renewal request
        end_date = None
        if request.data.get("end_date"):
            end_date = request.data.get("end_date")

        if request.data.get("document_id"):
            # retriueve document_id from the request
            document_id = request.data.get("document_id")
            # Create a lease agreement object
            lease_agreement = LeaseAgreement.objects.create(
                owner=owner,
                tenant=tenant,
                rental_unit=unit,
                approval_hash=approval_hash,
                document_id=document_id,
                rental_application_id=rental_application_id,
                start_date=start_date,
                end_date=end_date,
                lease_renewal_request=lease_renewal_request,
            )

        if request.data.get("signed_lease_document_file"):
            signed_lease_document_file = request.data.get("signed_lease_document_file")
            # file = UploadedFile.objects.get(id=signed_lease_document_file)
            # Create a lease agreement object
            lease_agreement = LeaseAgreement.objects.create(
                owner=owner,
                tenant=tenant,
                rental_unit=unit,
                approval_hash=approval_hash,
                signed_lease_document_file=signed_lease_document_file,
                rental_application_id=rental_application_id,
                start_date=start_date,
                end_date=end_date,
                lease_renewal_request=lease_renewal_request,
                is_active=True,
            )

        # Return a success response containing the lease agreement object as well as a message and a 201 stuats code
        serializer = LeaseAgreementSerializer(lease_agreement)
        return Response(
            {
                "message": "Lease agreement created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # Create a function to retrieeve all lease agreement by that are linked to a specific tenant
    @action(detail=False, methods=["get"], url_path="get-lease-agreements-by-tenant")
    def get_lease_agreements_by_tenant(self, request):
        # Retrieve the tenant id from the request
        tenant_id = request.query_params.get("tenant_id")
        # Retrieve the tenant object from the database
        tenant = Tenant.objects.get(user=tenant_id)
        # Retrieve all lease agreements that are linked to the tenant
        lease_agreements = LeaseAgreement.objects.filter(tenant=tenant)
        # Return a success response containing the lease agreements as well as a message and a 200 status code
        serializer = LeaseAgreementSerializer(lease_agreements, many=True)
        return Response(
            {
                "message": "Lease agreements retrieved successfully.",
                "data": serializer.data,
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    # Create a function to reterieve a lease agreement by the lease_renewal_request
    @action(
        detail=False,
        methods=["get"],
        url_path="get-lease-agreement-by-lease-renewal-request",
    )
    def get_lease_agreement_by_lease_renewal_request(self, request):
        # Retrieve the lease_renewal_request id from the request
        lease_renewal_request_id = request.query_params.get("lease_renewal_request_id")
        # Retrieve the lease_renewal_request object from the database
        lease_renewal_request = LeaseRenewalRequest.objects.get(
            id=lease_renewal_request_id
        )
        # Retrieve the lease agreement object from the database
        lease_agreement = LeaseAgreement.objects.filter(
            lease_renewal_request=lease_renewal_request
        ).first()
        # Return a success response containing the lease agreement as well as a message and a 200 status code
        serializer = LeaseAgreementSerializer(lease_agreement)
        return Response(
            {
                "message": "Lease agreement retrieved successfully.",
                "data": serializer.data,
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )
    
    #Create a function that cancells a lease and resets the unit to unoccupied and the tenant to null. It sould also void all invoices
    @action(detail=False, methods=["post"], url_path="cancel-lease-agreement")
    def cancel_lease(self, request):
        #Check if request user owns the lease agreement
        owner = Owner.objects.get(user=request.user)
        lease_agreement_id = request.data.get("lease_agreement_id")
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        if lease_agreement.owner != owner:
            return Response(
                {"message": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tenant = Tenant.objects.get(id=lease_agreement.tenant.id)
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

        #Retrieve all customers invoices
        invoices = stripe.Invoice.list(customer=customer.id, limit=100)["data"]
        #fetch invoice with the metadata's lease_agreement_id property equal to the lease_agreement_id and void each invoice
        for invoice in invoices:
            if invoice.metadata["type"] == "rent_payment" and int(invoice.metadata["lease_agreement_id"]) == lease_agreement.id and invoice.status == "open":
                #Retrieve the invoice using the invoice's id attribute and void it
                stripe.Invoice.void_invoice(invoice.id)

        lease_agreement.is_active = False
        lease_agreement.save()
        unit = RentalUnit.objects.get(id=lease_agreement.rental_unit.id)
        unit.is_occupied = False
        unit.tenant = None
        unit.save()
        lease_agreement.delete()
        return Response(
            {
                "message": "Lease cancelled successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

# Create an endpoint that will handle when a person signs a lease agreement
class SignLeaseAgreementView(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        lease_agreement_id = request.data.get("lease_agreement_id")
        unit_id = request.data.get("unit_id")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        # check if the approval hash is valid with the lease agreement
        if lease_agreement.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST
            )

        # retrieve the lease agreement object and update the start_date and end_date and set is_active to true
        lease_agreement.start_date = start_date
        lease_agreement.end_date = end_date
        # lease_agreement.is_active = True
        #Set the signed date to the current date
        lease_agreement.signed_date = timezone.now().date()
        # document_id = request.data.get('document_id') TODO
        lease_agreement.save()

        # retrieve the unit object and set the is_occupied field to true
        unit = RentalUnit.objects.get(id=unit_id)
        unit.is_occupied = True
        unit.save()

        tenant_first_name = ""
        tenant_last_name = ""
        if lease_agreement.tenant_invite:
            tenant_first_name = lease_agreement.tenant_invite.first_name
            tenant_last_name = lease_agreement.tenant_invite.last_name
        elif lease_agreement.rental_application:
            tenant_first_name = lease_agreement.rental_application.first_name
            tenant_last_name = lease_agreement.rental_application.last_name

        try:
            #Retrieve the owner's preferences
            owner_preferences = json.loads(lease_agreement.owner.preferences)
            #Retrieve the object in the array who's "name" key value is "tenant_signed_lease_agreement"
            tenant_signed_lease_agreement = next(
                item for item in owner_preferences if item["name"] == "tenant_lease_agreement_signed"
            )
            #Retrieve the "values" key value of the object
            tenant_signed_lease_agreement_values = tenant_signed_lease_agreement["values"]

            #loop through the values array and check if the value is "email" or "push"
            for value in tenant_signed_lease_agreement_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a notification for the owner that the tenant has signed the lease agreement
                    notification = Notification.objects.create(
                        user=lease_agreement.owner.user,
                        message=f"{tenant_first_name} {tenant_last_name} has signed the lease agreement for unit {unit.name} at {unit.rental_property.name}",
                        type="lease_agreement_signed",
                        title="Lease Agreement Signed",
                        resource_url=f"/dashboard/owner/lease-agreements/{lease_agreement.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the tenant that the lease agreement has been signed
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = lease_agreement.owner.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Agreement Signed",
                        HtmlBody=f"{tenant_first_name} {tenant_last_name} has signed the lease agreement for unit {unit.name} at {unit.rental_property.name}",
                    )
        except StopIteration:
            # Handle case where "tenant_lease_agreement_signed" is not found
            print("tenant_lease_agreement_signed not found. Notification not sent.")
            pass
        except KeyError:
            # Handle case where "values" key is missing in "tenant_lease_agreement_signed"
            print("values key not found in tenant_lease_agreement_signed. Notification not sent.")
            pass

        # return a response for the lease being signed successfully
        return Response(
            {"message": "Lease signed successfully.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


# Create a function to retrieve a lease agreement by the id without the need for a token
class RetrieveLeaseAgreementByIdAndApprovalHashView(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        lease_agreement_id = request.data.get("lease_agreement_id")

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        # check if the approval hash is valid with the lease agreement
        if lease_agreement.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LeaseAgreementSerializer(lease_agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)
