
import os
from shutil import move
import stat
from tracemalloc import start
import stripe
from django.http import JsonResponse
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from django.utils import timezone as dj_timezone
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from keyflow_backend_app.models import lease_renewal_request

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
    IsLandlordOrReadOnly,
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
    permission_classes = [IsLandlordOrReadOnly, IsResourceOwner]
    authentication_classes = [JWTAuthentication]
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
        "tenant",
        "is_active",
        "start_date",
        "end_date",
        "created_at",
    ]
    filterset_fields = ["is_active", "start_date", "end_date", "created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(user=user)
        return queryset

    # Create a function to override the create method to create a lease agreement
    def create(self, request, *args, **kwargs):
        # Retrieve rental_application from the request
        rental_application_id = request.data.get("rental_application")
        # Retrieve the unit id from the request
        unit_id = request.data.get("rental_unit")
        # Retrieve the unit object from the database
        unit = RentalUnit.objects.get(id=unit_id)
        # Retrieve the lease term id from the request
        lease_template_id = request.data.get("lease_template")
        # Retrieve the lease term object from the database
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        approval_hash = request.data.get("approval_hash")
        #Check if  request.data.get("lease_renewal_request") exists if not set it to none
        lease_renewal_request=None
        if request.data.get("lease_renewal_request"):
            lease_renewal_request = LeaseRenewalRequest.objects.get(id=request.data.get("lease_renewal_request"))
        
        # retriueve document_id from the request
        document_id = request.data.get("document_id")
        
        #Check if tenant exists if lease is being created on a lease renewal request
        tenant=None
        if request.data.get("tenant"):
            tenant = User.objects.get(id=request.data.get("tenant"))

        #Check if start_date exists if lease is being created on a lease renewal request
        start_date=None
        if request.data.get("start_date"):
            start_date = request.data.get("start_date")

        #Check if end_date exists if lease is being created on a lease renewal request
        end_date=None
        if request.data.get("end_date"):
            end_date = request.data.get("end_date")

        # Create a lease agreement object
        lease_agreement = LeaseAgreement.objects.create(
            user=request.user,
            rental_unit=unit,
            tenant=tenant,
            lease_template=lease_template,
            approval_hash=approval_hash,
            document_id=document_id,
            rental_application_id=rental_application_id,
            start_date=start_date,
            end_date=end_date,
            lease_renewal_request=lease_renewal_request,
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

    #Create a function to retrieeve all lease agreement by that are linked to a specific tenant
    @action(detail=False, methods=["get"], url_path="get-lease-agreements-by-tenant")
    def get_lease_agreements_by_tenant(self, request):
        # Retrieve the tenant id from the request
        tenant_id = request.query_params.get("tenant_id")
        # Retrieve the tenant object from the database
        tenant = User.objects.get(id=tenant_id)
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

    #Create a function to reterieve a lease agreement by the lease_renewal_request 
    @action(detail=False, methods=["get"], url_path="get-lease-agreement-by-lease-renewal-request")
    def get_lease_agreement_by_lease_renewal_request(self, request):
        # Retrieve the lease_renewal_request id from the request
        lease_renewal_request_id = request.query_params.get("lease_renewal_request_id")
        # Retrieve the lease_renewal_request object from the database
        lease_renewal_request = LeaseRenewalRequest.objects.get(id=lease_renewal_request_id)
        # Retrieve the lease agreement object from the database
        lease_agreement = LeaseAgreement.objects.filter(lease_renewal_request=lease_renewal_request).first()
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


# Create an endpoint that will handle when a person signs a lease agreement
class SignLeaseAgreementView(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        lease_agreement_id = request.data.get("lease_agreement_id")
        unit_id = request.data.get("unit_id")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        signed_date = request.data.get("signed_date")

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        # check if the approval hash is valid with the lease agreement
        if lease_agreement.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data."}, status=status.HTTP_400_BAD_REQUEST
            )

        # retrieve the lease agreement object and update the start_date and end_date and set is_active to true
        lease_agreement.start_date = start_date
        lease_agreement.end_date = end_date
        lease_agreement.is_active = True
        lease_agreement.signed_date = signed_date
        # document_id = request.data.get('document_id') TODO
        lease_agreement.save()

        # retrieve the unit object and set the is_occupied field to true
        unit = RentalUnit.objects.get(id=unit_id)
        unit.is_occupied = True
        unit.save()

        # Retrieve tenantfirst and last name from the rental application using  the approval hash
        rental_application = RentalApplication.objects.filter(
            approval_hash=approval_hash
        ).first()
    
        # Create a notification for the landlord that the tenant has signed the lease agreement
        notification = Notification.objects.create(
            user=lease_agreement.user,
            message=f"{rental_application.first_name} {rental_application.last_name} has signed the lease agreement for unit {unit.name} at {unit.rental_property.name}",
            type="lease_agreement_signed",
            title="Lease Agreement Signed",
            resource_url=f"/dashboard/landlord/lease-agreements/{lease_agreement.id}",
        )

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