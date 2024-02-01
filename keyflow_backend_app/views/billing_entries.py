
import stripe
import os
from dotenv import load_dotenv
from rest_framework import viewsets
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
    ordering_fields = ["tenant__user__first_name", "status", "amount","created_at"]

    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    def create(self, request):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        type = data["type"]
        amount = data["amount"]
        description = data["description"]
        tenant_id = data["tenant"]
        tenant = Tenant.objects.get(id=tenant_id)
        billing_entry_status = data["status"]
        collection_method = data["collection_method"]

        if billing_entry_status == "unpaid":        
            due_date = None
            if data["due_date"] != None:
                due_date_str = data["due_date"]
                # convert due_date (Should look like: "2024-03-07") to timestamp (Like this: 1680644467)
                due_date = int(datetime.strptime(due_date_str, "%Y-%m-%d").timestamp())
            else:
                due_date = None
            print("Due Date", due_date)
            # Create a stripe invoice for the billing entry
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            # retrieve thestripe cusotmer object
            tenant_stripe_customer = stripe.Customer.retrieve(tenant.stripe_customer_id)


            if(collection_method == "send_invoice"):
                #Create a stripe invoice object
                stripe_invoice = stripe.Invoice.create(
                    customer=tenant_stripe_customer,
                    auto_advance=True,
                    collection_method=collection_method,
                    due_date=due_date,
                    metadata={
                        "description": description,
                        "tenant_id": tenant.pk,
                        "owner_id": owner.pk,
                        "type": type,
                    },
                )  

                #Create a stripe price object 
                price = stripe.Price.create(
                    unit_amount=int(float(amount)*100),
                    currency="usd",
                    product_data={
                        "name": description,
                    },
                )

                #Create an invoice item for the stripe invoice
                invoice_item = stripe.InvoiceItem.create(
                    customer=tenant_stripe_customer,
                    price=price.id,
                    quantity=1,
                    invoice=stripe_invoice.id,
                )   

                # Create Billing Entry for the owner
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    description=description,
                    tenant=tenant,
                    owner=owner,
                    status=billing_entry_status,
                    stripe_invoice_id=stripe_invoice.id,
                )
                #Create Transaction for the billing entry
                transaction = Transaction.objects.create(                   
                    amount=amount,
                    billing_entry=billing_entry,
                    description=description,
                    type="revenue",
                    tenant=tenant,
                    user=owner.user,
                    stripe_invoice_id=stripe_invoice.id,
                )
                stripe.Invoice.finalize_invoice(stripe_invoice.id)
                stripe.Invoice.send_invoice(stripe_invoice.id)
            elif collection_method == "charge_automatically":
                #Create a stripe invoice object
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

                #Create a stripe price object 
                price = stripe.Price.create(
                    unit_amount=int(float(amount)*100),
                    currency="usd",
                    product_data={
                        "name": description,
                    },
                )

                #Create an invoice item for the stripe invoice
                invoice_item = stripe.InvoiceItem.create(
                    customer=tenant_stripe_customer,
                    price=price.id,
                    quantity=1,
                    invoice=stripe_invoice.id,
                )   

                # Create Billing Entry for the owner
                billing_entry = BillingEntry.objects.create(
                    type=type,
                    amount=amount,
                    description=description,
                    tenant=tenant,
                    owner=owner,
                    status=billing_entry_status,
                    stripe_invoice_id=stripe_invoice.id,
                )

                stripe.Invoice.finalize_invoice(stripe_invoice.id)
                #Create Transaction for the billing entry
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
                user=owner.user,
                status=billing_entry_status,
            )
            #Create Transaction for the billing entry
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
