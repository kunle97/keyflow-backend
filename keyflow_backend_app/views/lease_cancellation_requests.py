import os
import stripe
import json
from postmarker.core import PostmarkClient
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated 
from keyflow_backend_app.models import account_type
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.user import User
from ..models.notification import Notification
from ..models.rental_unit import RentalUnit
from ..models.rental_property import RentalProperty
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from ..models.notification import Notification
from ..serializers.lease_cancellation_request_serializer import (
    LeaseCancellationRequestSerializer,
)
from rest_framework import status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class LeaseCancellationRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaseCancellationRequest.objects.all()
    serializer_class = LeaseCancellationRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "tenant__user__first_name",
        "tenant__user__last_name",
    ]
    ordering_fields = [
        "tenant__user__last_name",
        "rental_unit__name",
        "request_date",
        "status",
        "created_at",
    ]

    def get_queryset(self):
        user = self.request.user

        if user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(tenant=tenant)
            return queryset
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            return queryset
        #Return empty queryset if user is not an owner or tenant
        return LeaseCancellationRequest.objects.none() 
    # Create a function to override the post method to create a lease cancellation request
    def create(self, request, *args, **kwargs):
        tenant_user_id = request.data.get("tenant")
        tenant_user = User.objects.get(id=tenant_user_id)
        # Retrieve the unit id from the request
        tenant = Tenant.objects.get(user=tenant_user)

        # Check if the tenant has an active lease agreement cancellation request
        lease_cancellation_request = LeaseCancellationRequest.objects.filter(
            tenant=tenant, status="pending"
        ).first()
        if lease_cancellation_request:
            return JsonResponse(
                {
                    "message": "You already have an active lease cancellation request.",
                    "data": None,
                    "status": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        unit_id = request.data.get("rental_unit")
        # Retrieve the unit object from the database
        unit = RentalUnit.objects.get(id=unit_id)
        owner=unit.owner
        # Retrieve the lease agreement using the unit id
        lease_agreement = LeaseAgreement.objects.filter(
            rental_unit=unit, tenant=tenant, is_active=True
        ).first()
        # Retrieve the lease agreement object from the database
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement.id)
        # Retrieve the reason from the request
        reason = request.data.get("reason")
        # Retrieve the comments from the request
        comments = request.data.get("comments")
        # Retrieve the request date from the request
        request_date = request.data.get("request_date")
        # Retrieve the rental property id from the request
        rental_property_id = request.data.get("rental_property")
        # Retrieve the rental property object from the database
        rental_property = RentalProperty.objects.get(id=rental_property_id)

        # Check if the tenant already has existing lease cancellation requests
        lease_cancellation_requests = LeaseCancellationRequest.objects.filter(
            tenant=tenant, status="pending"
        ).first()
        if lease_cancellation_requests:
            return JsonResponse(
                {
                    "message": "You already have an active lease cancellation request.",
                    "data": None,
                    "status": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a lease cancellation request object
        lease_cancellation_request = LeaseCancellationRequest.objects.create(
            owner=owner,
            tenant=tenant,
            rental_unit=unit,
            lease_agreement=lease_agreement,
            rental_property=rental_property,
            reason=reason,
            comments=comments,
            request_date=request_date,
        )
        try: 
            #Retrieve the owner's preferences
            owner_preferences = json.loads(lease_agreement.owner.preferences)
            #Retrieve the object in the array who's "name" key value is "lease_cancellation_request_created"
            lease_cancellation_request_created = next(
                item for item in owner_preferences if item["name"] == "lease_cancellation_request_created"
            )
            #Retrieve the "values" key value of the object
            lease_cancellation_request_created_values = lease_cancellation_request_created["values"]
            client_hostname = os.getenv("CLIENT_HOSTNAME")
            #loop through the values array and check if the value is "email" or "push"
            for value in lease_cancellation_request_created_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a  notification for the owner that the tenant has requested to cancel the lease agreement
                    notification = Notification.objects.create(
                        user=owner.user,
                        message=f"{tenant.user.first_name} {tenant.user.last_name} has requested to cancel the lease agreement for unit {unit.name} at {rental_property.name}",
                        type="lease_cancellation_request",
                        title="Lease Cancellation Request",
                        resource_url=f"/dashboard/owner/lease-cancellation-requests/{lease_cancellation_request.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the owner that the tenant has requested to cancel the lease agreement using postmark
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = owner.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Cancellation Request",
                        HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has requested to cancel the lease agreement for unit {unit.name} at {rental_property.name}. <a href='{client_hostname}/dashboard/owner/lease-cancellation-requests/{lease_cancellation_request.id}'>Click here to view the request.</a>",
                    )
        except StopIteration:
            # Handle case where "lease_cancellation_request_created" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_cancellation_request_created"

            pass
        # Return a success response containing the lease cancellation request object as well as a message and a 201 stuats code
        serializer = LeaseCancellationRequestSerializer(lease_cancellation_request)
        return Response(
            {
                "message": "Lease cancellation request created successfully.",
                "data": serializer.data,
                "status": 201,
            },
            status=status.HTTP_201_CREATED,
        )

    # Create a function handle the approval of a lease cancellation request
    @action(detail=False, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        data = request.data.copy()

        owner = request.user
        owner = Owner.objects.get(user=owner)
        lease_cancellation_request = LeaseCancellationRequest.objects.get(
            id=data["lease_cancellation_request_id"]
        )
        lease_agreement_id = data["lease_agreement_id"]
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        lease_terms = json.loads(lease_agreement.rental_unit.lease_terms)
        lease_cancellation_fee = next(
            (item for item in lease_terms if item["name"] == "lease_cancellation_fee"),
            None,
        )


        # Retreive tenant from lease Agreement
        tenant_user = User.objects.get(id=lease_agreement.tenant.user.id)

        tenant = Tenant.objects.get(user=tenant_user)
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

        tenant_payment_methods = stripe.Customer.list_payment_methods(
            customer.id,
            limit=1,
        )

        #Retrieve all customers invoices
        invoices = stripe.Invoice.list(customer=customer.id, limit=100)["data"]
        #fetch invoice with the metadata's lease_agreement_id property equal to the lease_agreement_id and void each invoice
        for invoice in invoices:
            if invoice.metadata["type"] == "rent_payment" and int(invoice.metadata["lease_agreement_id"]) == lease_agreement.id and invoice.status == "open":
                #Retrieve the invoice using the invoice's id attribute and void it
                stripe.Invoice.void_invoice(invoice.id)

        unit = RentalUnit.objects.get(id=lease_agreement.rental_unit.id)
        # Create a stripe charge for the tenant for cancellation fee
        lease_cancellation_fee_payment_intent = stripe.PaymentIntent.create(
            amount=int(int(lease_cancellation_fee['value']) * 100),
            currency="usd",
            payment_method_types=["card"],
            customer=customer.id,
            payment_method=tenant_payment_methods.data[0].id,#TODO: Should be tenants default payment method not just first  one in list
            transfer_data={
                "destination": owner.stripe_account_id  # The Stripe Connected Account ID
            },
            confirm=True,
            # Add Metadata to the transaction signifying that it is a security deposit
            metadata={
                "type": "revenue",
                "description": f"{tenant_user.first_name} {tenant_user.last_name} Lease Cancellation Fee Payment for unit {unit.name} at {unit.rental_property.name}",
                "user_id": owner.id,
                "tenant_id": tenant.id,
                "owner_id": owner.id,
                "rental_property_id": unit.rental_property.id,
                "rental_unit_id": unit.id,
                "payment_method_id": tenant_payment_methods.data[0].id,#TODO: Should be tenants default payment method not just first  one in list
            },
        )

        # Change Unit To Not Occupied and remove tenant
        unit = RentalUnit.objects.get(id=lease_agreement.rental_unit.id)
        unit.is_occupied = False
        unit.tenant = None
        unit.save()

        # Delete Lease Cancellation Request
        # lease_cancellation_request.delete()
        lease_cancellation_request.status = "approved"
        lease_cancellation_request.save()

        # Delete Lease Agreement
        lease_agreement.delete()

        try:
            tenant_preferences = json.loads(tenant.preferences)
            lease_cancellation_request_approved = next(
                item for item in tenant_preferences if item["name"] == "lease_cancellation_request_approved"
            )
            lease_cancellation_request_approved_values = lease_cancellation_request_approved["values"]
            for value in lease_cancellation_request_approved_values:
                if value["name"] == "push" and value["value"] == True:
                    #Create a notification for the tenant that the lease agreement has been cancelled
                    notification = Notification.objects.create(
                        user=tenant_user,
                        message=f"Your lease agreement for unit {unit.name} at {unit.rental_property.name} has been cancelled.",
                        type="lease_agreement_cancelled",
                        title="Lease Agreement Cancelled",
                        resource_url=f"/dashboard/tenant/my-lease/",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":           
                    #Create an email notification for the tenant that the lease agreement has been cancelled using postmark
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = tenant_user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Agreement Cancelled",
                        HtmlBody=f"Your lease agreement for unit {unit.name} at {unit.rental_property.name} has been cancelled.",
                    )
        except StopIteration:
            # Handle case where "tenant_lease_agreement_signed" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "tenant_lease_agreement_signed"

            pass

        # Return a success response
        return Response(
            {
                "message": "Lease cancellation request approved.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    # Create a function handle the denial of a lease cancellation request by deleting the lease cancellation request
    @action(detail=False, methods=["post"], url_path="deny")
    def deny(self, request, pk=None):
        data = request.data.copy()
        lease_cancellation_request = LeaseCancellationRequest.objects.get(
            id=data["lease_cancellation_request_id"]
        )
        account_type = request.user.account_type
        if account_type == "tenant":
            #check that the request user is the tenant that owns the lease cancellation request
            if lease_cancellation_request.tenant.user != request.user:
                return JsonResponse(
                    {
                        "message": "You are not authorized to deny this lease cancellation request.",
                        "data": None,
                        "status": 403,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif account_type == "owner":
            #check that the request user is the owner that owns the lease cancellation request
            if lease_cancellation_request.owner.user != request.user:
                return JsonResponse(
                    {
                        "message": "You are not authorized to deny this lease cancellation request.",
                        "data": None,
                        "status": 403,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            
        # Delete Lease Cancellation Request
        lease_cancellation_request.status = "denied"
        lease_cancellation_request.save()
        lease_cancellation_request.delete()

        try:
            tenant_preferences = json.loads(lease_cancellation_request.tenant.preferences)
            lease_cancellation_request_denied = next(
                item for item in tenant_preferences if item["name"] == "lease_cancellation_request_denied"
            )

            lease_cancellation_request_denied_values = lease_cancellation_request_denied["values"]
            for value in lease_cancellation_request_denied_values:
                if value["name"] == "push" and value["value"] == True:
                    #Create a notification for the tenant that the lease cancellation request has been denied
                    notification = Notification.objects.create(
                        user=lease_cancellation_request.tenant.user,
                        message=f"Your lease cancellation request for unit {lease_cancellation_request.rental_unit.name} at {lease_cancellation_request.rental_property.name} has been denied.",
                        type="lease_cancellation_request_denied",
                        title="Lease Cancellation Request Denied",
                        resource_url=f"/dashboard/tenant/lease-cancellation-requests/{lease_cancellation_request.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the tenant that the lease cancellation request has been denied using postmark
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = lease_cancellation_request.tenant.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Cancellation Request Denied",
                        HtmlBody=f"Your lease cancellation request for unit {lease_cancellation_request.rental_unit.name} at {lease_cancellation_request.rental_property.name} has been denied.",
                    )
        except StopIteration:
            # Handle case where "lease_cancellation_request_denied" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_cancellation_request_denied"

            pass

        # Return a success response
        return Response(
            {
                "message": "Lease cancellation request denied.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
        )


    # Create a function to retrieve all of the tenant's lease cancellation requests called get_tenant_lease_cancellation_requests with the url path tenat
    @action(detail=False, methods=["get"], url_path="tenant")
    def get_tenant_lease_cancellation_requests(self, request, pk=None):
        # Retrieve the tenant object from the database
        tenant_user = request.user
        tenant = Tenant.objects.get(user=tenant_user)
        # Retrieve all of the tenant's lease cancellation requests
        lease_cancellation_requests = LeaseCancellationRequest.objects.filter(
            tenant=tenant
        )
        # Return a success response containing the lease cancellation requests as well as a message and a 200 status code
        serializer = LeaseCancellationRequestSerializer(lease_cancellation_requests, many=True)
        return Response(
            {
                "message": "Lease cancellation requests retrieved successfully.",
                "data": serializer.data,
                "status": 200,
            },
            status=status.HTTP_200_OK,
        )
