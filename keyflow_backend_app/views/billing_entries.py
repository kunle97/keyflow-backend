import json
import re
import resource
import stripe
import os
from keyflow_backend_app.models.maintenance_request import MaintenanceRequest
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from rest_framework import viewsets
import pytz
from django.utils import timezone
from keyflow_backend_app.helpers.helpers import calculate_final_price_in_cents
from keyflow_backend_app.models.notification import Notification
from keyflow_backend_app.models.rental_unit import RentalUnit
from ..models.account_type import Owner, Tenant
from ..models.billing_entry import BillingEntry
from ..models.transaction import Transaction
from ..serializers.billing_entry_serializer import BillingEntrySerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from datetime import datetime, timedelta
from rest_framework import status
from keyflow_backend_app.permissions.billing_entry_permissions import IsResourceOwner

load_dotenv()


# Create a model viewset for the BillingEntry MOdel
class BillingEntryViewSet(viewsets.ModelViewSet):
    queryset = BillingEntry.objects.all()
    serializer_class = BillingEntrySerializer
    permission_classes = [IsAuthenticated, IsResourceOwner]
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["tenant__user__first_name", "status"]
    search_fields = ["tenant__user__first_name", "status"]
    ordering_fields = ["tenant__user__first_name", "status", "amount", "type","created_at"]

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

    # create an function to override the get method for retrieveing one speceific billing entry
    def retrieve(self, request, *args, **kwargs):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        user = self.request.user
        payment_link = None
        billing_entry = self.get_object()
        # Retrieve the stripe invoice for the billing entry
        if billing_entry.stripe_invoice_id:
            stripe_invoice = stripe.Invoice.retrieve(billing_entry.stripe_invoice_id)
            payment_link = stripe_invoice.hosted_invoice_url
        serializer = BillingEntrySerializer(billing_entry)
        
        return Response({"data": serializer.data, "payment_link": payment_link}, status=status.HTTP_200_OK)

    def create(self, request):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        type = data["type"]
        expense_types = [
            "expense",
            "vendor_payment",
        ]
        amount = float(data["amount"])
        description = data["description"]
        tenant = None
        rental_unit = None
        rental_property = None
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        account = stripe.Account.retrieve(owner.stripe_account_id)
        requirements = account.requirements
        if len(requirements.currently_due) > 0:
            return Response(
                {
                    "message": "Please complete your stripe account requirements before creating a billing entry.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        collection_method = None


        # Check if tennt exists
        tenant_id = request.data.get("tenant", None)

        if type in expense_types and tenant_id is None and request.data.get("rental_unit", None) is not None:
            rental_unit = RentalUnit.objects.get(id=request.data.get("rental_unit"))
            rental_property = rental_unit.rental_property
            collection_method = None
        if type not in expense_types and tenant_id is  None:
            collection_method = None
        #Check for if Rental unit exists when request_unit is passed in the request
        if tenant_id is not None and request.data.get("rental_unit", None) is None:
            tenant = Tenant.objects.get(id=request.data.get("tenant"))
            rental_unit = RentalUnit.objects.get(tenant=tenant)
            rental_property = rental_unit.rental_property
            
            tenant_stripe_customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
            collection_method ="send_invoice"

        #Check for if Rental unit exists when request_unit is passed in the request
        billing_entry_status = data["status"]
        stripe_invoice = None
        due_date = None
        if request.data.get("due_date", None) is not None:
            due_date_str = request.data.get("due_date", None)
            # Convert due_date (Should look like: "2024-03-07") to timestamp (Like this: 1680644467)
            due_date_timestamp = int(datetime.fromisoformat(due_date_str).timestamp())
            # Create variable date_time to convert due_date_str to store in a DateTimeField
            due_date_time_field = datetime.fromisoformat(due_date_str)
            # Add one day to the due_date_time_field to adjust for the database 
            due_date_time_field += timedelta(days=1)
            # Create a stripe invoice for the billing entry
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            # retrieve thestripe cusotmer object


            # Calculate the Stripe fee based on the rent amount
            stripe_fee_in_cents = calculate_final_price_in_cents(amount)["stripe_fee_in_cents"]

            # Create a Stripe product and price for the Stripe fee
            stripe_fee_product = stripe.Product.create(
                name=f"Payment processing fee",
                type="service",
            )
            stripe_fee_price = stripe.Price.create(
                unit_amount=int(stripe_fee_in_cents),
                currency="usd",
                product=stripe_fee_product.id,
            )

            if collection_method == "send_invoice":
                # Create a stripe invoice object if type is not in the expense_types list
                if type not in expense_types:
                    if billing_entry_status == "unpaid":
                        stripe_invoice = stripe.Invoice.create(
                            customer=tenant_stripe_customer,
                            auto_advance=True,
                            collection_method=collection_method,
                            due_date=due_date_timestamp,
                            metadata={
                                "description": description,
                                "tenant_id": tenant.pk,
                                "owner_id": owner.pk,
                                "type": type,
                            },
                        )

                        # Create a stripe price object
                        price = stripe.Price.create(
                            unit_amount=int(amount * 100),
                            currency="usd",
                            product_data={
                                "name": description,
                            },
                        )

                        # Create an invoice item for the stripe invoice
                        invoice_item = stripe.InvoiceItem.create(
                            customer=tenant_stripe_customer,
                            price=price.id,
                            quantity=1,
                            invoice=stripe_invoice.id,
                            description=description,
                        )
                        # Create a Stripe invoice item for the Stripe fee
                        invoice_item = stripe.InvoiceItem.create(
                            customer=tenant_stripe_customer,
                            price=stripe_fee_price.id,
                            currency="usd",
                            description=f"Stripe fee for rent payment of {rental_unit.name} at {rental_unit.rental_property.name}",
                            invoice=stripe_invoice.id,
                        )
                        stripe.Invoice.finalize_invoice(stripe_invoice.id)
                        stripe.Invoice.send_invoice(stripe_invoice.id)

                    tenant_preferences = json.loads(tenant.preferences)

                    # Retrieve the object in the array whose "name" key value is "bill_created"
                    invoice_recieved = next(
                        item for item in tenant_preferences if item["name"] == "bill_created"
                    )

                    # Retrieve the dictionary in the "values" list where the "name" key value is "push"
                    push_value = next(
                        value for value in invoice_recieved["values"] if value["name"] == "push"
                    )

                    if push_value["value"] == True:
                        resource_url = None
                        if stripe_invoice != None:
                            resource_url=f"/dashboard/tenant/bills/{stripe_invoice.id}"
                        else:
                            resource_url="/dashboard/tenant/bills"
                        # Create a notification for the tenant that a new invoice has been sent
                        notification = Notification.objects.create(
                            user=tenant.user,
                            message=f"A new invoice has been received for {description}",
                            type="invoice_recieved",
                            title="Invoice Received",
                            resource_url=resource_url,
                        )

                    # Retrieve the dictionary in the "values" list where the "name" key value is "email"
                    email_value = next(
                        value for value in invoice_recieved["values"] if value["name"] == "email"
                    )

                    if email_value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                        # Create an email notification using Postmark for the tenant that a new invoice has been received
                        client_hostname = os.getenv("CLIENT_HOSTNAME")
                        postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                        to_email = tenant.user.email
                        if os.getenv("ENVIRONMENT") == "development":
                            to_email = "keyflowsoftware@gmail.com"
                        else:
                            to_email = tenant.user.email
                        postmark.emails.send(
                            From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                            To=to_email,
                            Subject="New Invoice Received",
                            HtmlBody=f"""
                            A new invoice has been received for {description}.
                            <a href='{client_hostname}/dashboard/tenant/bills/{stripe_invoice.id}'>View Invoice</a>
                            """,
                        )
                stripe_invoice_id = None
                if stripe_invoice != None:
                    stripe_invoice_id = stripe_invoice.id
                
                # Create Billing Entry for the owner
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    due_date=due_date_time_field,
                    description=description,
                    tenant=tenant,
                    rental_unit=rental_unit,
                    owner=owner,
                    status=billing_entry_status,
                    stripe_invoice_id=stripe_invoice_id,
                )
                if billing_entry_status == "paid":
                    # Create Transaction for the billing entry
                    transaction = Transaction.objects.create(
                        amount=amount,
                        billing_entry=billing_entry,
                        description=description,
                        type=type,
                        tenant=tenant,
                        owner=owner,
                        user=owner.user,
                        rental_unit=rental_unit,
                        rental_property=rental_property,
                    )
                serializer = BillingEntrySerializer(billing_entry)
                return Response(
                    {
                        "message": "Billing entry created successfully.",
                        "data": serializer.data,
                        "status": status.HTTP_201_CREATED
                    },
                    status=status.HTTP_201_CREATED,
                )
            elif collection_method == None:
                #Handle case for expense types
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    due_date=due_date_time_field,
                    description=description,
                    tenant=tenant,
                    owner=owner,
                    rental_unit=rental_unit,
                    status=billing_entry_status,
                )
                if billing_entry_status == "paid":
                    # Create Transaction for the billing entry
                    transaction = Transaction.objects.create(
                        amount=amount,
                        billing_entry=billing_entry,
                        description=description,
                        type=type,
                        tenant=tenant,
                        owner=owner,
                        user=owner.user,
                        rental_unit=rental_unit,
                        rental_property=rental_property,
                        timestamp=due_date_time_field,
                    )
                serializer = BillingEntrySerializer(billing_entry)
                maintenance_request_id = request.data.get("maintenance_request_id", None)
                #Check if maintenance_request_id is passed in the request
                if maintenance_request_id != None:
                    maintenance_request = MaintenanceRequest.objects.get(id=data['maintenance_request_id'])
                    maintenance_request.billing_entry = billing_entry
                    maintenance_request.save()

                return Response(
                    {
                        "message": "Billing entry created successfully.",
                        "data": serializer.data,
                        "status": status.HTTP_201_CREATED
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            return Response(
                {"message": "Due date  or transaction date is required to create a billing entry."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    def partial_update(self, request, *args, **kwargs):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        user = self.request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        stripe_invoice = None
        stripe_invoice_item = None
        billing_entry = self.get_object()
        if billing_entry.stripe_invoice_id:
            stripe_invoice = stripe.Invoice.retrieve(billing_entry.stripe_invoice_id)
        if stripe_invoice:
            stripe_invoice_item = stripe.InvoiceItem.retrieve(
                stripe_invoice.lines.data[0].invoice_item
            )

        updated_type = request.data.get("type", None)
        if updated_type and updated_type != billing_entry.type:
            billing_entry.type = updated_type
            if stripe_invoice:
                # update stripe invoice metadata for the type
                stripe.Invoice.modify(
                    stripe_invoice.id,
                    metadata={"type": updated_type},
                )

        updated_status = request.data.get("status", None)
        if updated_status and updated_status != billing_entry.status:
            # only allow status channge from upaid to paid
            if billing_entry.status == "unpaid" and updated_status == "paid":
                if stripe_invoice:
                    # void the invoice
                    stripe.Invoice.void_invoice(stripe_invoice.id)
                billing_entry_status = updated_status
                billing_entry.status = billing_entry_status
                billing_entry.save()
                billing_entry_rental_unit = None
                billing_entry_rental_property = None
                #check if the billing entry has a rental unit
                if billing_entry.rental_unit:
                    billing_entry_rental_unit = billing_entry.rental_unit
                    billing_entry_rental_property = billing_entry.rental_unit.rental_property
                
                #Create transaction for the billing entry
                transaction = Transaction.objects.create(
                    amount=billing_entry.amount,
                    billing_entry=billing_entry,
                    description=billing_entry.description,
                    type=billing_entry.type,
                    tenant=billing_entry.tenant,
                    owner=request.user.owner,
                    user=request.user,
                    rental_unit=billing_entry_rental_unit,
                    rental_property=billing_entry_rental_property,
                )
                return super().partial_update(request, *args, **kwargs)
            else:
                return Response(
                    {
                        "message": "You cannot change the status of a paid invoice.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # updated description
        updated_description = request.data.get("description", None)
        if updated_description and updated_description != billing_entry.description:
            billing_entry.description = updated_description
            if stripe_invoice:
                # update stripe invoice metadata for the description
                stripe.Invoice.modify(
                    stripe_invoice.id,
                    metadata={"description": updated_description},
                )
        updated_collection_method = request.data.get("collection_method", None)
        if (
            updated_collection_method
            and updated_collection_method != billing_entry.collection_method
        ):
            billing_entry.collection_method = updated_collection_method
            # update stripe invoice collection method
            stripe_invoice.collection_method = updated_collection_method
            stripe_invoice.save()
        billing_entry.updated_at = datetime.now()
        billing_entry.save()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        billing_entry = self.get_object()
        #Check if there is a transaction for the billing entry
        transaction = Transaction.objects.filter(billing_entry=billing_entry)
        if transaction.exists():
            #Delete the transaction
            transaction.delete()
        if billing_entry.stripe_invoice_id != None:
            invoice = stripe.Invoice.retrieve(billing_entry.stripe_invoice_id)
            if invoice.status == "open" or invoice.status == "draft":
                stripe.Invoice.void_invoice(billing_entry.stripe_invoice_id)
            billing_entry.delete()
            return Response(
                {"message": "Billing entry deleted successfully.", "status": 204},
                status=status.HTTP_204_NO_CONTENT,
            )
        else:
            billing_entry.delete()
            return Response(
                {"message": "Billing entry deleted successfully.", "status": 204},
                status=status.HTTP_204_NO_CONTENT,
            )
