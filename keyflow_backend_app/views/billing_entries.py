import stripe
import os
from dotenv import load_dotenv
from rest_framework import viewsets

from keyflow_backend_app.models.rental_unit import RentalUnit
from ..models.account_type import Owner, Tenant
from ..models.billing_entry import BillingEntry
from ..models.transaction import Transaction
from ..serializers.billing_entry_serializer import BillingEntrySerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from datetime import datetime
from rest_framework import status

load_dotenv()


# Create a model viewset for the BillingEntry MOdel
class BillingEntryViewSet(viewsets.ModelViewSet):
    queryset = BillingEntry.objects.all()
    serializer_class = BillingEntrySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["tenant__user__first_name", "status"]
    search_fields = ["tenant__user__first_name", "status"]
    ordering_fields = ["tenant__user__first_name", "status", "amount", "created_at"]

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
        #Retrieve the stripe invoice for the billing entry
        if billing_entry.stripe_invoice_id:
            stripe_invoice = stripe.Invoice.retrieve(billing_entry.stripe_invoice_id)
            payment_link = stripe_invoice.hosted_invoice_url
        serializer = BillingEntrySerializer(billing_entry)
        return Response({"data": serializer.data, "payment_link":payment_link}, status=status.HTTP_200_OK)

    def create(self, request):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        type = data["type"]
        expense_types = [
            "expense",
            "vendor_payment",
        ]
        amount = data["amount"]
        description = data["description"]
        tenant = None
        # Check if tennt exists
        tenant_id = request.data.get("tenant", None)
        if Tenant.objects.filter(id=tenant_id).exists():
            tenant = Tenant.objects.get(id=request.data.get("tenant"))

        billing_entry_status = data["status"]
        collection_method = request.data.get("collection_method", None)
        stripe_invoice = None
        due_date = None
        if request.data.get("due_date", None) is not None:
            due_date_str = request.data.get("due_date", None)
            # Convert due_date (Should look like: "2024-03-07") to timestamp (Like this: 1680644467)
            due_date_timestamp = int(datetime.fromisoformat(due_date_str).timestamp())
            # Create variable date_time to convert duedate_str to store  in a DateTimeField
            due_date_time_field = datetime.fromisoformat(due_date_str)
            print("Due Date", due_date)

            # Create a stripe invoice for the billing entry
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            # retrieve thestripe cusotmer object
            tenant_stripe_customer = stripe.Customer.retrieve(tenant.stripe_customer_id)

            if collection_method == "send_invoice":
                # Create a stripe invoice object if type is not in the expense_types list
                if type not in expense_types:
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
                        unit_amount=int(float(amount) * 100),
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
                    stripe.Invoice.finalize_invoice(stripe_invoice.id)
                    stripe.Invoice.send_invoice(stripe_invoice.id)

                # Create Billing Entry for the owner
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    due_date=due_date_time_field,
                    description=description,
                    tenant=tenant,
                    owner=owner,
                    status=billing_entry_status,
                    stripe_invoice_id=stripe_invoice.id,
                )
                rental_unit = RentalUnit.objects.get(tenant=tenant)
                rental_property = rental_unit.rental_property
                # Create Transaction for the billing entry
                transaction = Transaction.objects.create(
                    amount=amount,
                    billing_entry=billing_entry,
                    description=description,
                    type=type,
                    tenant=tenant,
                    user=owner.user,
                    rental_unit=rental_unit,
                    rental_property=rental_property,
                )
                serializer = BillingEntrySerializer(billing_entry)
                return Response(
                    {
                        "message": "Billing entry created successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            elif collection_method == "charge_automatically":
                if type not in expense_types:
                    # Create a stripe invoice object
                    stripe_invoice = stripe.Invoice.create(
                        customer=tenant_stripe_customer,
                        auto_advance=True,
                        collection_method=collection_method,
                        metadata={
                            "description": description,
                            "tenant_id": tenant.pk,
                            "owner_id": owner.pk,
                            "type": type,
                        },
                    )

                    # Create a stripe price object
                    price = stripe.Price.create(
                        unit_amount=int(float(amount) * 100),
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
                    stripe.Invoice.finalize_invoice(stripe_invoice.id)

                # Create Billing Entry for the owner
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    due_date=due_date_time_field,
                    description=description,
                    tenant=tenant,
                    owner=owner,
                    status=billing_entry_status,
                    stripe_invoice_id=stripe_invoice.id,
                )
                rental_unit = RentalUnit.objects.get(tenant=tenant)
                rental_property = rental_unit.rental_property
                # Create Transaction for the billing entry
                transaction = Transaction.objects.create(
                    amount=amount,
                    billing_entry=billing_entry,
                    description=description,
                    type="revenue",
                    tenant=tenant,
                    user=owner.user,
                )

                serializer = BillingEntrySerializer(billing_entry)
                return Response(
                    {
                        "message": "Billing entry created successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            billing_entry = BillingEntry.objects.create(
                type=type,
                amount=amount,
                description=description,
                tenant=tenant,
                owner=owner,
                status=billing_entry_status,
            )
            # Create Transaction for the billing entry
            transaction = Transaction.objects.create(
                amount=amount,
                billing_entry=billing_entry,
                description=description,
                type=type,
                tenant=tenant,
                user=owner.user,
            )
            serializer = BillingEntrySerializer(billing_entry)
            return Response(
                {
                    "message": "Billing entry created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
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
