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
        )

        # Create a  notification for the landlord that the tenant has requested to renew the lease agreement
        notification = Notification.objects.create(
            user=user,
            message=f"{tenant_user.first_name} {tenant_user.last_name} has requested to renew their lease agreement at unit {unit.name} at {rental_property.name}",
            type="lease_renewal_request",
            title="Lease Renewal Request",
            resource_url=f"/dashboard/landlord/lease-renewal-requests/{lease_renewal_request.id}",

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
        lease_template = LeaseTemplate.objects.get(id=data["lease_template_id"])

        tenant_user = User.objects.get(id=lease_agreement.tenant.id)
        tenant = Tenant.objects.get(user=tenant_user)
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

        tenant_payment_methods = stripe.Customer.list_payment_methods(
            customer.id, limit=1
        )


        # Update Lease Renewal Request
        lease_renewal_request.status = "approved"
        lease_renewal_request.save()
        # Create notification for tenant that lease renewal request has been approved
        notification = Notification.objects.create(
            user=tenant_user,
            message=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been approved.",
            type="lease_renewal_request_approved",
            title="Lease Renewal Request Approved",
            resource_url=f"/dashboard/tenant/lease-renewal-requests/{lease_renewal_request.id}",
        )
        return Response(
            {
                "message": "Lease renewal request approved.",
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
        

        if (
            lease_agreement.lease_template.lease_renewal_fee is not None
            and lease_agreement.lease_template.lease_renewal_fee > 0
        ):
            lease_renewal_fee_payment_intent = stripe.PaymentIntent.create(
                amount=int(lease_agreement.lease_template.lease_renewal_fee * 100),
                currency="usd",
                payment_method_types=["card"],
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
                amount=lease_agreement.lease_template.lease_renewal_fee,
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
                amount=lease_agreement.lease_template.lease_renewal_fee,
                description=f"Lease Renewal Fee Payment for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                type="lease_renewal_fee",
            )

        
        
        #TODO: implement secutrity deposit flow here. Should not charge tenant untill start of lease. Ensure subsicption is sety to a trial period of 30 days and then charge the security deposit immeediatly
        # if lease_agreement.lease_template.security_deposit>0:
        #     #Retrieve landlord from the unit
        #     security_deposit_payment_intent = stripe.PaymentIntent.create(
        #         amount=int(lease_agreement.lease_template.security_deposit*100),
        #         currency='usd',
        #         payment_method_types=['card'],
        #         customer=customer.id,
        #         payment_method=selected_payment_method, #TODO: Should be tenants default payment method not just first  one in list
        #         transfer_data={
        #             "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
        #         },
        #         confirm=True,
        #         #Add Metadata to the transaction signifying that it is a security deposit
        #         metadata={
        #             "type": "revenue",
        #             "description": f'{tenant.first_name} {tenant.last_name} Security Deposit Payment for unit {lease_agreement.rental_unit.name} at {lease_agreement.rental_unit.rental_property.name}',
        #             "user_id": landlord.id,
        #             "tenant_id": tenant.id,
        #             "landlord_id": landlord.id,
        #             "rental_property_id": lease_agreement.rental_unit.rental_property.id,
        #             "rental_unit_id": lease_agreement.rental_unit.id,
        #             "payment_method_id": selected_payment_method,#TODO: Should be tenants default payment method not just first one in list
        #         }

        #     )

        #     #create a transaction object for the security deposit
        #     security_deposit_transaction = Transaction.objects.create(
        #         type = 'revenue',
        #         description = f'{tenant.first_name} {tenant.last_name} Security Deposit Payment for unit {lease_agreement.rental_unit.name} at {lease_agreement.rental_unit.rental_property.name}',
        #         rental_property = lease_agreement.rental_unit.rental_property,
        #         rental_unit = lease_agreement.rental_unit,
        #         user=landlord,
        #         tenant=tenant,
        #         amount=int(lease_agreement.lease_template.security_deposit),
        #         payment_method_id=selected_payment_method,
        #         payment_intent_id=security_deposit_payment_intent.id,

        #     )
        #     #Create a notification for the landlord that the security deposit has been paid
        #     notification = Notification.objects.create(
        #         user=landlord,
        #         message=f'{tenant.first_name} {tenant.last_name} has paid the security deposit for the amount of ${lease_agreement.lease_template.security_deposit} for unit {lease_agreement.rental_unit.name} at {lease_agreement.rental_unit.rental_property.name}',
        #         type='security_deposit_paid',
        #         title='Security Deposit Paid',
        #         resource_url=f'/dashboard/landlord/transactions/{security_deposit_transaction.id}'
        #     )


        # Create Stripe Subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[
                {"price": lease_agreement.lease_template.stripe_price_id},
            ],
            trial_end=int(new_lease_start_date.timestamp()),
            transfer_data={
                "destination": landlord.stripe_account_id  # The Stripe Connected Account ID
            },
            cancel_at=int(new_lease_end_date.timestamp()),
            metadata={
                "type": "lease",
                "description": f"{tenant.user.first_name} {tenant.user.last_name} rent subscription for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
                "user_id": landlord.id,
                "tenant_id": tenant.id,
                "landlord_id": landlord.id,
                "rental_property_id": lease_renewal_request.rental_unit.rental_property.id,
                "rental_unit_id": lease_renewal_request.rental_unit.id,
                "payment_method_id": tenant_payment_methods.data[0].id,
            },
        )

        lease_agreement.stripe_subscription_id = subscription.id
        lease_agreement.start_date = new_lease_start_date
        lease_agreement.end_date = new_lease_end_date
        lease_agreement.is_active = (
            False  # TODO: Need to set a CronJob to set this to true on the start_date in Prod
        )
        lease_agreement.save()

        #Create a notification for the landlord that the tenant has signed the lease renewal agreement
        notification = Notification.objects.create(
            user=landlord.user,
            message=f"{tenant.user.first_name} {tenant.user.last_name} has signed the lease renewal agreement for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name}",
            type="lease_renewal_agreement_signed",
            title="Lease Renewal Agreement Signed",
            resource_url=f"/dashboard/landlord/lease-agreements/{lease_agreement.id}",
        )

        # Return a success response
        return Response(
            {
                "message": "Lease agreement (Renewal) signed successfully.",
                "status": 200,
            },
            status=status.HTTP_200_OK,
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

        # Create a notification for the tenant that the lease renewal request has been rejected
        notification = Notification.objects.create(
            user=lease_renewal_request.owner.user,
            message=f"Your lease renewal request for unit {lease_renewal_request.rental_unit.name} at {lease_renewal_request.rental_unit.rental_property.name} has been rejected.",
            type="lease_renewal_request_rejected",
            title="Lease Renewal Request Rejected",
            
        )

        return Response(
            {
                "message": "Lease renewal request rejected.",
                "status": 204,
            },
            status=status.HTTP_204_NO_CONTENT,
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
