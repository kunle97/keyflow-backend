from datetime import timedelta, datetime
import json
import os
import resource
from postmarker.core import PostmarkClient
from tracemalloc import start
import stripe
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
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
from ..models.lease_template import LeaseTemplate
from rest_framework import status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class LeaseRenewalRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaseRenewalRequest.objects.all()
    serializer_class = LeaseRenewalRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
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
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    # Create a function to override the post method to create a lease renewal request
    def create(self, request, *args, **kwargs):
        # Retrieve the unit id from the request
        tenant_user = User.objects.get(id=request.data.get("tenant"))
        tenant = Tenant.objects.get(user=tenant_user)
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

        owner_preferences = json.loads(owner.preferences)
        lease_renewal_request_created_preferences = next(
            (item for item in owner_preferences if item["name"] == "lease_renewal_request_created"),
            None,
        )
        lease_renewal_request_created_values = lease_renewal_request_created_preferences["values"]
        for value in lease_renewal_request_created_values:
            if value["name"] == "push" and value["value"] == True:
                # Create a  notification for the landlord that the tenant has requested to renew the lease agreement
                notification = Notification.objects.create(
                    user=user,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has requested to renew their lease agreement at unit {unit.name} at {rental_property.name}",
                    type="lease_renewal_request",
                    title="Lease Renewal Request",
                    resource_url=f"/dashboard/landlord/lease-renewal-requests/{lease_renewal_request.id}",
                )
            elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                #Create an email notification for the landlord that the tenant has requested to renew the lease agreement
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
                    HtmlBody=f"{tenant_user.first_name} {tenant_user.last_name} has requested to renew their lease agreement at unit {unit.name} at {rental_property.name}. Click <a href='{client_hostname}/dashboard/landlord/lease-renewal-requests/{lease_renewal_request.id}'>here</a> to view the request.",
                )

        # Return a success response containing the lease renewal request object as well as a message and a 201 stuats code
        serializer = LeaseRenewalRequestSerializer(lease_renewal_request)
        return Response(
            {
                "message": "Lease renewal request created successfully.",
                "data": serializer.data,
                "status": 201,
            },
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
        lease_agreement = LeaseAgreement.objects.get(
            id=data["current_lease_agreement_id"]
        )

        tenant = lease_renewal_request.tenant
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

        tenant_payment_methods = stripe.Customer.list_payment_methods(
            customer.id, limit=1
        )

        # Update Lease Renewal Request
        lease_renewal_request.status = "approved"
        lease_renewal_request.save()
        
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

        return Response(
            {
                "message": "Lease renewal request rejected.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    
    def calculate_rent_periods(self, lease_start_date, rent_frequency, term):
        rent_periods = []
        current_date = lease_start_date
        end_date = None
        print(f"ZX reent_frequency: {rent_frequency}")
        if rent_frequency == "month":
            end_date = lease_start_date + relativedelta(months=term)
        elif rent_frequency == "week":
            end_date = lease_start_date + relativedelta(weeks=term)
        elif rent_frequency == "day":
            end_date = lease_start_date + relativedelta(days=term)
        elif rent_frequency == "year":
            end_date = lease_start_date + relativedelta(years=term)
        print(f"ZX current_date: {current_date}")
        print(f"ZX end_date: {end_date}")
        while current_date < end_date:
            period_start = current_date
            period_end = None
            if rent_frequency == "month":
                period_end = current_date + relativedelta(months=1)
            elif rent_frequency == "week":
                period_end = current_date + relativedelta(weeks=1)
            elif rent_frequency == "day":
                period_end = current_date + relativedelta(days=1)
            elif rent_frequency == "year":
                period_end = current_date + relativedelta(years=1)

            rent_periods.append((period_start, period_end))
            current_date = period_end

        return rent_periods

    def create_invoice_for_period(
        self,
        period_start,
        rent_amount,
        customer_id,
        due_date,
        unit,
        additional_charges_dict,
        lease_agreement
    ):
        # Set time part of due_date to end of the day
        due_date_end_of_day = datetime.combine(due_date, datetime.max.time())

        # Create Stripe Invoice for the specified rent payment period
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=True,
            collection_method="send_invoice",
            due_date=int(due_date_end_of_day.timestamp()),
            metadata={
                "type": "rent_payment",
                "description": "Rent payment",
                "tenant_id": unit.tenant.id,
                "owner_id": unit.owner.id,
                "rental_property_id": unit.rental_property.id,
                "rental_unit_id": unit.id,
                "lease_agreement_id": lease_agreement.id,
            },
            transfer_data={"destination": unit.owner.stripe_account_id},
            application_fee_amount=int(rent_amount * 0.01 * 100),
        )

        price = stripe.Price.create(
            unit_amount=int(rent_amount * 100),
            currency="usd",
            product_data={
                "name": f"Rent for unit {unit.name} at {unit.rental_property.name}"
            },
        )

        # Create a Stripe invoice item for the specified rent payment period
        invoice_item = stripe.InvoiceItem.create(
            customer=customer_id,
            price=price.id,
            currency="usd",
            description="Rent payment",
            invoice=invoice.id,
        )
        print(f"ZX invoice: {additional_charges_dict}")
        if len(additional_charges_dict) > 0:
            # Create an invoice item for each additional charge
            for charge in additional_charges_dict:
                charge_amount = charge["amount"]
                charge_name = charge["name"]
                charge_product_name = str(
                    f"{charge_name} for unit {unit.name} at {unit.rental_property.name}"
                )
                print(charge_product_name)
                print(f"ZX charge_amount: {charge_amount}")
                print(f"ZX charge_name: {charge_name}")
                charge_product = stripe.Product.create(
                    name=charge_product_name,
                    type="service",
                )
                charge_price = stripe.Price.create(
                    unit_amount=int(charge_amount) * 100,
                    currency="usd",
                    product=charge_product.id,
                )
                invoice_item = stripe.InvoiceItem.create(
                    customer=customer_id,
                    price=charge_price.id,
                    currency="usd",
                    description=f"{charge['name']} for unit {unit.name} at {unit.rental_property.name}",
                    invoice=invoice.id,
                )
        stripe.Invoice.finalize_invoice(invoice.id)
        return invoice

    def create_rent_invoices(
        self,
        lease_start_date,
        rent_amount,
        rent_frequency,
        lease_term,
        customer_id,
        unit,
        additional_charges_dict,
        leasea_agreement
    ):
        rent_periods = self.calculate_rent_periods(
            lease_start_date, rent_frequency, lease_term
        )
        current_date = datetime.now().date()
        due_date = None
        for period_start, period_end in rent_periods:
            if period_start.date() >= current_date:
                # calculate the due date for current invoice
                if rent_frequency == "month":
                    due_date = period_start + relativedelta(months=1)
                elif rent_frequency == "week":
                    due_date = period_start + relativedelta(weeks=1)
                elif rent_frequency == "day":
                    due_date = period_start + relativedelta(days=1)
                elif rent_frequency == "year":
                    due_date = period_start + relativedelta(years=1)
                # Create Stripe invoice for each rent payment period
                self.create_invoice_for_period(
                    period_start,
                    rent_amount,
                    customer_id,
                    due_date,
                    unit,
                    additional_charges_dict,
                    leasea_agreement
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
        landlord = lease_agreement.owner
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
                    "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
                },
                confirm=True,
                # Add Metadata to the transaction signifying that it is a security deposit
                metadata={
                    "type": "revenue",
                    "description": f"{tenant.user.first_name} {tenant.user.last_name} Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                    "user_id": landlord.id,
                    "tenant_id": tenant.id,
                    "landlord_id": landlord.id,
                    "rental_property_id": lease_renewal_request.rental_unit.rental_property.id,
                    "rental_unit_id": lease_renewal_request.rental_unit.id,
                    "payment_method_id": tenant_payment_methods.data[0].id,
                },
            )
            # Create Transaction for Lease Renewal Fee
            transaction = Transaction.objects.create(
                user=landlord.user,
                rental_property=lease_renewal_request.rental_unit.rental_property,
                rental_unit=lease_renewal_request.rental_unit,
                payment_method_id=tenant_payment_methods.data[0].id,
                payment_intent_id=lease_renewal_fee_payment_intent.id,
                amount=lease_renewal_fee_value,
                description=f"{tenant.user.first_name} {tenant.user.last_name} Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                type="lease_renewal_fee",
            )
            # Create Transaction for Lease Renewal Fee
            transaction = Transaction.objects.create(
                user=tenant.user,
                rental_property=lease_renewal_request.rental_unit.rental_property,
                rental_unit=lease_renewal_request.rental_unit,
                payment_method_id=tenant_payment_methods.data[0].id,
                payment_intent_id=lease_renewal_fee_payment_intent.id,
                amount=lease_renewal_fee_value,
                description=f"Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
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
        additional_charges_dict = json.loads(unit.additional_charges)
        
        #Create rent invoices usiing the create_rent_invoices method
        self.create_rent_invoices(
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

        owner_preferences = json.loads(landlord.preferences)
        lease_agreement_preferences = next(
            (item for item in owner_preferences if item["name"] == "lease_renewal_agreement_signed"),
            None,
        )
        lease_agreement_values = lease_agreement_preferences["values"]
        for value in lease_agreement_values:
            if value["name"] == "push" and value["value"] == True:
                # Create a notification for the landlord that the tenant has signed the lease renewal agreement
                notification = Notification.objects.create(
                    user=landlord.user,
                    message=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                    type="lease_renewal_agreement_signed",
                    title="Lease Renewal Agreement Signed",
                    resource_url=f"/dashboard/landlord/lease-agreements/{lease_agreement.id}",
                )
            elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                #CReate an email notification fot the landlord that the tenant has signed the lease renewal agreement
                client_hostname = os.getenv("CLIENT_HOSTNAME")
                postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                to_email = ""
                if os.getenv("ENVIRONMENT") == "development":
                    to_email = "keyflowsoftware@gmail.com"
                else:
                    to_email = landlord.user.email
                postmark.emails.send(
                    From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                    To=to_email,
                    Subject="Lease Renewal Agreement Signed",
                    # HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}. Click <a href='{client_hostname}/dashboard/landlord/lease-agreements/{lease_agreement.id}'>here</a> to view the agreement.",
                    HtmlBody=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}.",
                )

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
