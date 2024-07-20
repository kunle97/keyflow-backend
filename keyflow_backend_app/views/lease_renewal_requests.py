from datetime import datetime
import json
import os
from postmarker.core import PostmarkClient
import stripe
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.user import User
from ..models.notification import Notification
from ..models.rental_unit import RentalUnit
from ..models.transaction import Transaction
from ..models.rental_property import RentalProperty
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_renewal_request import LeaseRenewalRequest
from ..models.notification import Notification
from ..serializers.lease_renewal_request_serializer import (
    LeaseRenewalRequestSerializer,
)
from keyflow_backend_app.helpers.helpers import calculate_final_price_in_cents, create_rent_invoices
from rest_framework import status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class LeaseRenewalRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaseRenewalRequest.objects.all()
    serializer_class = LeaseRenewalRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "tenant__first_name",
        "tenant__last_name",
    ]
    ordering_fields = ["tenant", "status"]

    def get_queryset(self):
        user = self.request.user
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            return queryset
        elif user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(tenant=tenant)
            return queryset
        else:
            return LeaseRenewalRequest.objects.none()

    # Create a function to override the post method to create a lease renewal request
    def create(self, request, *args, **kwargs):
        # Retrieve the unit id from the request
        tenant = Tenant.objects.get(id=request.data.get("tenant"))
        # Check if the tenant has an active lease agreement renewal request
        lease_renewal_request = LeaseRenewalRequest.objects.filter(
            tenant=tenant, status="pending"
        ).first()
        if lease_renewal_request:
            return JsonResponse(
                {
                    "message": "You already have an active lease renewal request.",
                    "data": None,
                    "status": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        move_in_date = request.data.get("move_in_date")
        unit_id = request.data.get("rental_unit")
        unit = RentalUnit.objects.get(id=unit_id)
        user = User.objects.get(id=unit.owner.user.id)
        owner = Owner.objects.get(user=user)
        request_date = request.data.get("request_date")
        rental_property_id = request.data.get("rental_property")
        rental_property = RentalProperty.objects.get(id=rental_property_id)

        # Create a lease renewal request object
        lease_renewal_request = LeaseRenewalRequest.objects.create(
            owner=owner,
            tenant=tenant,
            rental_unit=unit,
            rental_property=rental_property,
            request_date=dj_timezone.now(),
            move_in_date=move_in_date,
            comments=request.data.get("comments"),
            request_term=request.data.get("lease_term"),
            rent_frequency=request.data.get("rent_frequency"),
        )
        try:
            owner_preferences = json.loads(owner.preferences)
            lease_renewal_request_created_preferences = next(
                (item for item in owner_preferences if item["name"] == "lease_renewal_request_created"),
                None,
            )
            lease_renewal_request_created_values = lease_renewal_request_created_preferences["values"]
            for value in lease_renewal_request_created_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a  notification for the owner that the tenant has requested to renew the lease agreement
                    notification = Notification.objects.create(
                        user=user,
                        message=f"{tenant.user.first_name} {tenant.user.last_name} has requested to renew their lease agreement at unit {unit.name} at {rental_property.name}",
                        type="lease_renewal_request",
                        title="Lease Renewal Request",
                        resource_url=f"/dashboard/owner/lease-renewal-requests/{lease_renewal_request.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the owner that the tenant has requested to renew the lease agreement
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="New Lease Renewal Request",
                        HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has requested to renew their lease agreement at unit {unit.name} at {rental_property.name}. Click <a href='{client_hostname}/dashboard/owner/lease-renewal-requests/{lease_renewal_request.id}'>here</a> to view the request.",
                    )
        except StopIteration:
            # Handle case where "lease_cancellation_request_created" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_cancellation_request_created"

            pass
        # Return a success response containing the lease renewal request object as well as a message and a 201 stuats code
        serializer = LeaseRenewalRequestSerializer(lease_renewal_request)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        ) 

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        data = request.data.copy()
        lease_renewal_request = LeaseRenewalRequest.objects.get(
            id=data["lease_renewal_request_id"]
        )

        tenant = lease_renewal_request.tenant
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

        tenant_payment_methods = stripe.Customer.list_payment_methods(
            customer.id, limit=1
        )

        # Update Lease Renewal Request
        lease_renewal_request.status = "approved"
        lease_renewal_request.save()
        try:
            tenant_preferences = json.loads(tenant.preferences)
            lease_renewal_request_approved = next(
                (item for item in tenant_preferences if item["name"] == "lease_renewal_request_approved"),
                None,
            )
            lease_renewal_request_approved_values = lease_renewal_request_approved["values"]
            for value in lease_renewal_request_approved_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create notification for tenant that lease renewal request has been approved
                    notification = Notification.objects.create(
                        user=tenant.user,
                        message=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been approved.",
                        type="lease_renewal_request_approved",
                        title="Lease Renewal Request Approved",
                        resource_url=f"/dashboard/tenant/lease-renewal-requests/{lease_renewal_request.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the tenant that the lease renewal request has been approved
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = tenant.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Renewal Request Approved",
                        HtmlBody=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been approved. Click <a href='{client_hostname}/dashboard/tenant/lease-renewal-requests/{lease_renewal_request.id}'>here</a> to view the request.",
                    )
        except StopIteration:
            # Handle case where "lease_renewal_request_approved" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_renewal_request_approved"

            pass

        return Response(
            {
                "message": "Lease renewal request approved.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
        )
    
    # Create a reject function to handle the rejection of a lease renewal request that will delete the lease renewal request and notify the tenant. Detail should be set to true
    @action(detail=False, methods=["post"], url_path="deny")
    def deny(self, request, pk=None):
        data = request.data.copy()

        lease_renewal_request = LeaseRenewalRequest.objects.get(
            id=data["lease_renewal_request_id"]
        )

        # Delete Lease Renewal Request
        lease_renewal_request.delete()

        try:
            tenant_preferences = json.loads(lease_renewal_request.tenant.preferences)
            lease_renewal_request_denied = next(
                (item for item in tenant_preferences if item["name"] == "lease_renewal_request_rejected"),
                None,
            )
            lease_renewal_request_denied_values = lease_renewal_request_denied["values"]
            for value in lease_renewal_request_denied_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a notification for the tenant that the lease renewal request has been rejected
                    notification = Notification.objects.create(
                        user=lease_renewal_request.tenant.user,
                        message=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been rejected.",
                        type="lease_renewal_request_rejected",
                        title="Lease Renewal Request Rejected",
                        resource_url=f"/dashboard/tenant/lease-renewal-requests/{lease_renewal_request.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification for the tenant that the lease renewal request has been rejected
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = lease_renewal_request.tenant.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Renewal Request Rejected",
                        HtmlBody=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been rejected.",
                    )
        except StopIteration:
            # Handle case where "lease_renewal_request_rejected" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_renewal_request_rejected"

            pass

        return Response(
            {
                "message": "Lease renewal request rejected.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    
 
    @action(detail=False, methods=["post"], url_path="sign")
    def sign(self, request, pk=None):
        data = request.data.copy()
        lease_renewal_request = LeaseRenewalRequest.objects.get(
            id=data["lease_renewal_request_id"]
        )
        lease_agreement = LeaseAgreement.objects.get(id=data["lease_agreement_id"])
        unit = RentalUnit.objects.get(id=lease_renewal_request.rental_unit.id)
        lease_terms = json.loads(unit.lease_terms)

        tenant = lease_agreement.tenant
        owner = lease_agreement.owner
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
        new_lease_start_date = lease_renewal_request.move_in_date
        new_lease_end_date = new_lease_start_date + relativedelta(
            months=lease_renewal_request.request_term
        )

        tenant_payment_methods = stripe.Customer.list_payment_methods(
            customer.id,
            limit=1,
        )
        selected_payment_method = tenant_payment_methods.data[0].id
        lease_renewal_fee = next(
            (item for item in lease_terms if item["name"] == "lease_renewal_fee"),
            None,
        )
        lease_renewal_fee_value = float(lease_renewal_fee["value"])
        if (
            lease_renewal_fee_value is not None
            and lease_renewal_fee_value > 0
        ):
            lease_renewal_fee_payment_intent = stripe.PaymentIntent.create(
                amount=int(lease_renewal_fee_value * 100),
                currency="usd",
                # payment_method_types=["card"],
                customer=customer.id,
                payment_method=tenant_payment_methods.data[0].id,
                transfer_data={
                    "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                },
                confirm=True,
                # Add Metadata to the transaction signifying that it is a security deposit
                metadata={
                    "type": "revenue",
                    "description": f"{tenant.user.first_name} {tenant.user.last_name} Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                    "user_id": owner.id,
                    "tenant_id": tenant.id,
                    "owner_id": owner.id,
                    "rental_property_id": lease_renewal_request.rental_unit.rental_property.id,
                    "rental_unit_id": lease_renewal_request.rental_unit.id,
                    "payment_method_id": tenant_payment_methods.data[0].id,
                },
            )
            # Create Transaction for Lease Renewal Fee
            transaction = Transaction.objects.create(
                user=owner.user,
                owner=owner,
                tenant=tenant,
                rental_property=lease_renewal_request.rental_unit.rental_property,
                rental_unit=lease_renewal_request.rental_unit,
                payment_method_id=tenant_payment_methods.data[0].id,
                payment_intent_id=lease_renewal_fee_payment_intent.id,
                amount=lease_renewal_fee_value,
                description=f"{tenant.user.first_name} {tenant.user.last_name} Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                type="lease_renewal_fee",
            )

        security_deposit = next(
            (item for item in lease_terms if item["name"] == "security_deposit"),
            None,
        )
        # Get the value property from the security_deposit object
        security_deposit_value = float(security_deposit["value"])
        # Retrieve rent frequency from the preferences list
        rent = next(
            (item for item in lease_terms if item["name"] == "rent"),
            None,
        )
        # Get the value property from the rent object
        rent_value = float(rent["value"])
        # Get the rent frequency from the preferences list
        rent_frequency = next(
            (item for item in lease_terms if item["name"] == "rent_frequency"),
            None,
        )
        # Get the value property from the rent_frequency object
        rent_frequency_value = rent_frequency["value"]

        # Get the value of the grace period from the preferences list
        grace_period = next(
            (item for item in lease_terms if item["name"] == "grace_period"),
            None,
        )
        # Get the value property from the grace object
        grace_period_value = int(grace_period["value"])

        term = next(
            (item for item in lease_terms if item["name"] == "term"),
            None,
        )
        term_value = int(term["value"])

        if security_deposit_value > 0:
            # Get current timestamp
            current_timestamp = int(datetime.now().timestamp())

            # Add 5 hours (in seconds) to the current timestamp
            due_date_timestamp = current_timestamp + (5 * 60 * 60)

            security_deposit_invoice = stripe.Invoice.create(
                customer=customer.id,
                auto_advance=True,
                collection_method="send_invoice",
                # Set duedate for today
                due_date=due_date_timestamp,
                metadata={
                    "type": "security_deposit",
                    "description": "Security Deposit Payment",
                    "tenant_id": tenant.id,
                    "owner_id": unit.rental_property.owner.id,
                    "rental_property_id": unit.rental_property.id,
                    "rental_unit_id": unit.id,
                },
                transfer_data={"destination": unit.owner.stripe_account_id},
            )
            # Create stripe price for security deposit
            price = stripe.Price.create(
                unit_amount=int(security_deposit_value * 100),
                currency="usd",
                product_data={
                    "name": str(
                        f"Security Deposit for unit {unit.name} at {unit.rental_property.name}"
                    )
                },
            )
            stripe.InvoiceItem.create(
                customer=customer.id,
                price=price.id,
                currency="usd",
                description=f"{tenant.user.first_name} {tenant.user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                invoice=security_deposit_invoice.id,
            )    
            #Add Invoice item for stripe fee
            stripe_fee_in_cents = calculate_final_price_in_cents(security_deposit_value)["stripe_fee_in_cents"]
            stripe_fee_product = stripe.Product.create(
                name=f"Payment processing fee",
                type="service",
            )
            stripe_fee_price = stripe.Price.create(
                unit_amount=int(stripe_fee_in_cents),
                currency="usd",
                product=stripe_fee_product.id,
            )
            stripe.InvoiceItem.create(
                customer=customer.id,
                price=stripe_fee_price.id,
                currency="usd",
                description=f"Payment processing fee",
                invoice=security_deposit_invoice.id,
            )
            # Finalize the invoice
            stripe.Invoice.finalize_invoice(security_deposit_invoice.id)
        additional_charges_dict = json.loads(unit.additional_charges)
        
        #Create rent invoices usiing the create_rent_invoices method
        create_rent_invoices(
            new_lease_start_date,
            rent_value,
            rent_frequency_value,
            term_value,
            customer.id,
            unit,
            additional_charges_dict,
            lease_agreement
        )


        # lease_agreement.stripe_subscription_id = subscription.id
        lease_agreement.start_date = new_lease_start_date
        lease_agreement.end_date = new_lease_end_date
        lease_agreement.is_active = False  # TODO: Need to set a CronJob to set this to true on the start_date in Prod
        lease_agreement.save()

        try:
            owner_preferences = json.loads(owner.preferences)
            lease_agreement_preferences = next(
                (item for item in owner_preferences if item["name"] == "lease_renewal_agreement_signed"),
                None,
            )
            lease_agreement_values = lease_agreement_preferences["values"]
            for value in lease_agreement_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a notification for the owner that the tenant has signed the lease renewal agreement
                    notification = Notification.objects.create(
                        user=owner.user,
                        message=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                        type="lease_renewal_agreement_signed",
                        title="Lease Renewal Agreement Signed",
                        resource_url=f"/dashboard/owner/lease-agreements/{lease_agreement.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #CReate an email notification fot the owner that the tenant has signed the lease renewal agreement
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = owner.user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Lease Renewal Agreement Signed",
                        # HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}. Click <a href='{client_hostname}/dashboard/owner/lease-agreements/{lease_agreement.id}'>here</a> to view the agreement.",
                        HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}.",
                    )
        except StopIteration:
            # Handle case where "lease_renewal_agreement_signed" is not found

            pass
        except KeyError:
            # Handle case where "values" key is missing in "lease_renewal_agreement_signed"

            pass

        # Return a success response
        return Response(
            {
                "message": "Lease agreement (Renewal) signed successfully.",
                "status": 200,
            },
            status=status.HTTP_200_OK,
        )

# Create a function to retrieve all of the tenant's lease renewal requests called get_tenant_lease_renewal_requests
    @action(detail=False, methods=["get"], url_path="tenant")
    def get_tenant_lease_renewal_requests(self, request, pk=None):
        user = request.user
        tenant = Tenant.objects.get(user=user)
        lease_renewal_requests = LeaseRenewalRequest.objects.filter(
            tenant=tenant
        ).order_by("-request_date")
        serializer = LeaseRenewalRequestSerializer(lease_renewal_requests, many=True)
        return Response(
            {
                "message": "Lease renewal requests retrieved successfully.",
                "data": serializer.data,
                "status": 200,
            },
            status=status.HTTP_200_OK,
        )
