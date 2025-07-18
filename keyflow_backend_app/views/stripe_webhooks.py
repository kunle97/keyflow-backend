import os
from postmarker.core import PostmarkClient 
from dotenv import load_dotenv
import stripe
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from datetime import datetime
from keyflow_backend_app.helpers.helpers import calculate_final_price_in_cents
from keyflow_backend_app.models.notification import Notification
from ..models.transaction import Transaction
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.account_type import Tenant
from ..models.user import User
from ..models.account_type import Owner
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")


class StripeSubscriptionPaymentSucceededEventView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        payload = request.body
        event = None

        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)


            if event.type == "invoice.payment_succeeded":
                # Test using the the following CLI Command:
                """
                stripe.exe trigger subscription.payment_succeeded --add subscription:metadata.amount=1000 ^
                --add subscription:metadata.description=webhook_test ^
                --add subscription:metadata.owner_id=1 ^
                --add subscription:metadata.tenant_id=2 ^
                --add subscription:metadata.rental_property_id=5 ^
                --add subscription:metadata.rental_unit_id=3 ^
                --add subscription:metadata.type=rent_payment ^
                --add subscription:metadata.payment_method_id=pm_1H4ZQzJZqXK5j4Z2X2ZQZQZQ
                """

                invoice = event.data.object
                amount = invoice.amount_paid
                metadata = invoice.lines.data[0].metadata
                payment_intent = event.data.object

                owner = Owner.objects.get(id=(metadata.get("owner_id", None)))
                owner_user = User.objects.get(id=owner.user.id)
                tenant = Tenant.objects.get(id=metadata.get("tenant_id", None))
                tenant_user = User.objects.get(id=tenant.user.id)
                rental_property = RentalProperty.objects.get(
                    id=metadata.get("rental_property_id", None)
                )
                rental_unit = RentalUnit.objects.get(
                    id=metadata.get("rental_unit_id", None)
                )

                subscription_transaction = Transaction.objects.create(
                    amount=rental_unit.lease_template.rent,  # Convert to currency units
                    user=owner_user,
                    owner=owner,
                    tenant=tenant,  # related tenant
                    type=metadata.get("type", None),
                    description=metadata.get("description", None),
                    rental_property=rental_property,
                    rental_unit=rental_unit,
                    payment_method_id=metadata.get(
                        "payment_method_id", None
                    ),  # or payment_intent.payment_method.id
                    payment_intent_id=invoice.payment_intent,
                )
                notification = Notification.objects.create(
                    user=owner_user,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has made a rent payment for the amount of ${rental_unit.lease_template.rent} for unit {rental_unit.name} at {rental_property.name}",
                    type="rent_payment",
                    title="Rent Payment",
                    resource_url=f"/dashboard/owner/transactions/{subscription_transaction.id}",
                )

            return JsonResponse({"status": "ok"})
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

class StripeInvoicePaymentSucceededEventView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        payload = request.body
        event = None

        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

            if event.type == "invoice.payment_succeeded":

                # Test using the the following windows CLI Command:
                """
                stripe trigger subscription.payment_succeeded --add subscription:metadata.amount=1000 ^
                --add subscription:metadata.description=webhook_test ^
                --add subscription:metadata.owner_id=1 ^
                --add subscription:metadata.tenant_id=2 ^
                --add subscription:metadata.rental_property_id=5 ^
                --add subscription:metadata.rental_unit_id=3 ^
                --add subscription:metadata.type=rent_payment ^
                --add subscription:metadata.payment_method_id=pm_1H4ZQzJZqXK5j4Z2X2ZQZQZQ
                """
                # Test using the the following mac CLI Command:
                """
                stripe trigger invoice.payment_succeeded \
                --add "invoice:metadata.amount=5000" \
                --add "invoice:metadata.description=webhook_test" \
                --add "invoice:metadata.owner_id=7" \
                --add "invoice:metadata.tenant_id=4" \
                --add "invoice:metadata.rental_property_id=17" \
                --add "invoice:metadata.rental_unit_id=22" \
                --add "invoice:metadata.type=rent_payment" \
                --add "invoice:metadata.payment_method_id=pm_1H4ZQzJZqXK5j4Z2X2ZQZQZQ"
                """

                invoice = event.data.object
                invoice_metadata = invoice.metadata
                amount = invoice.amount_paid
                metadata = invoice.lines.data[0].metadata
                payment_intent = event.data.object
                if invoice_metadata['type'] == "rent_payment":

                    owner = Owner.objects.get(id=invoice_metadata["owner_id"])
                    owner_user = User.objects.get(id=owner.user.id)
                    tenant = Tenant.objects.get(id=invoice_metadata["tenant_id"])
                    tenant_user = User.objects.get(id=tenant.user.id)
                    rental_property = RentalProperty.objects.get(
                        id=invoice_metadata["rental_property_id"]
                    )
                    rental_unit = RentalUnit.objects.get(
                        id=invoice_metadata["rental_unit_id"]
                    )
                    

                    if invoice.status == "open" and invoice.due_date < int(datetime.now().timestamp()):
                        #retrieve the late fee from the unit's lease terms
                        lease_terms = json.loads(rental_unit.lease_terms)
                        late_fee = next(
                            (item for item in lease_terms if item["name"] == "late_fee"),
                            None,
                        )
                        late_fee_value = float(late_fee["value"])
                        #Create an invoice for the late fee
                        late_fee_invoice = stripe.Invoice.create(
                            customer=invoice.customer,
                            amount=int(late_fee_value*100),
                            collection_method="send_invoice",
                            days_until_due=30,
                            metadata={
                                "type": "late_fee",
                                "description": "Late Fee Payment",
                                "tenant_id": metadata["tenant_id"],
                                "owner_id": metadata["owner_id"],
                                "rental_property_id": metadata["rental_property_id"],
                                "rental_unit_id": metadata["rental_unit_id"],
                            },
                            transfer_data={"destination": owner.stripe_account_id},
                        )
                        #Create Stripe product for the late fee
                        late_fee_product = stripe.Product.create(
                            name=f"Late Fee",
                            type="service",
                        )
                        #Crate a stripe price for the late fee
                        late_fee_price = stripe.Price.create(
                            unit_amount=int(late_fee_value*100),
                            currency="usd",
                            product=late_fee_product.id,
                        )
                        #Create a stripe invoice item for the late fee
                        late_fee_invoice_item = stripe.InvoiceItem.create(
                            customer=invoice.customer,
                            price=late_fee_price.id,
                            quantity=1,
                            description="Late Fee Payment",
                            invoice=late_fee_invoice.id
                        )
                        # Calculate the Stripe fee based on the rent amount
                        stripe_fee_in_cents = calculate_final_price_in_cents(late_fee_value)["stripe_fee_in_cents"]

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

                        #finalize invoice
                        late_fee_invoice.finalize_invoice()

                    invoice_transaction = Transaction.objects.create(
                        amount=float(invoice.amount_paid/100),  # Convert to currency units
                        owner=owner,
                        user=owner_user,
                        type=invoice_metadata["type"],
                        description=f"Rent Payment for {rental_unit.name} at {rental_property.name} by {tenant_user.first_name} {tenant_user.last_name}",
                        rental_property=rental_property,
                        rental_unit=rental_unit,
                        tenant=tenant,  # related tenant
                        payment_intent_id=invoice.payment_intent,
                    )
                    try: 
                        owner_preferences = json.loads(owner.preferences)
                        invoice_paid = next(
                            item for item in owner_preferences if item["name"] == "invoice_paid"
                        )
                        invoice_paid_values = invoice_paid["values"]
                        for value in invoice_paid_values:
                            if value["name"] == "push" and value["value"] == True:
                                notification = Notification.objects.create(
                                    user=owner_user,
                                    message=f"{tenant_user.first_name} {tenant_user.last_name} has made a rent payment for the amount of ${float(invoice.amount_paid/100)} for unit {rental_unit.name} at {rental_property.name}",
                                    type="rent_payment",
                                    title="Rent Payment",
                                    resource_url=f"/dashboard/owner/transactions/{invoice_transaction.id}",
                                )
                            elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                                #Create an email notification for the owner about the the tenant's rent payment
                                client_hostname = os.getenv("CLIENT_HOSTNAME")
                                postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                                to_email = ""
                                if os.getenv("ENVIRONMENT") == "development":
                                    to_email = "keyflowsoftware@gmail.com"
                                else:
                                    to_email = owner_user.email
                                postmark.emails.send(
                                    From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                                    To=to_email,
                                    Subject="Rent Payment Notification",
                                    HtmlBody=f"<p>{tenant_user.first_name} {tenant_user.last_name} has made a rent payment for the amount of ${float(invoice.amount_paid/100)} for unit {rental_unit.name} at {rental_property.name}</p> <a href='{client_hostname}/dashboard/owner/transactions/{invoice_transaction.id}'>View Transaction</a>",
                                )
                    except StopIteration:
                        # Handle case where "invoice_paid" is not found

                        pass
                    except KeyError:
                        # Handle case where "values" key is missing in "invoice_paid"

                        pass                        
                if invoice_metadata.get("type", None) == "security_deposit":
                    if invoice.status == "open" and invoice.due_date < int(datetime.now().timestamp()):
                        #retrieve the late fee from the unit's lease terms
                        lease_terms = json.loads(rental_unit.lease_terms)
                        late_fee = next(
                            (item for item in lease_terms if item["name"] == "late_fee"),
                            None,
                        )
                        late_fee_value = float(late_fee["value"])
                        #Create an invoice for the late fee
                        late_fee_invoice = stripe.Invoice.create(
                            customer=invoice.customer,
                            collection_method="send_invoice",
                            days_until_due=30,
                            metadata={
                                "type": "late_fee",
                                "description": "Late Fee Payment",
                                "tenant_id": invoice_metadata.get("tenant_id",None),
                                "owner_id": invoice_metadata.get("owner_id", None),
                                "rental_property_id": invoice_metadata.get("rental_property_id", None),
                                "rental_unit_id": invoice_metadata.get("rental_unit_id", None),
                            },
                            transfer_data={"destination": owner.stripe_account_id},
                        )
                    owner = Owner.objects.get(id=(invoice_metadata.get("owner_id", None)))
                    owner_user = User.objects.get(id=owner.user.id)
                    tenant = Tenant.objects.get(id=invoice_metadata.get("tenant_id", None))
                    tenant_user = User.objects.get(id=tenant.user.id)
                    rental_property = RentalProperty.objects.get(
                        id=invoice_metadata.get("rental_property_id", None)
                    )
                    rental_unit = RentalUnit.objects.get(
                        id=invoice_metadata.get("rental_unit_id", None)
                    )
                    
                    invoice_transaction = Transaction.objects.create(
                        amount=float(invoice.amount_paid/100),  # Convert to currency units
                        owner=owner,
                        user=owner_user,
                        type=invoice_metadata.get("type", None),
                        description=f"Security Deposit Payment for {rental_unit.name} at {rental_property.name} by {tenant_user.first_name} {tenant_user.last_name}",
                        rental_property=rental_property,
                        rental_unit=rental_unit,
                        tenant=tenant,  # related tenant
                        # payment_method_id=invoice_metadata.get(
                        #     "payment_method_id", None
                        # ),  # or payment_intent.payment_method.id
                        payment_intent_id=invoice.payment_intent,
                    )
                    try:
                        owner_preferences = json.loads(owner.preferences)
                        invoice_paid = next(
                            item for item in owner_preferences if item["name"] == "invoice_paid"
                        )
                        invoice_paid_values = invoice_paid["values"]
                        for value in invoice_paid_values:
                            if value["name"] == "push" and value["value"] == True:
                                notification = Notification.objects.create(
                                    user=owner_user,
                                    message=f"{tenant_user.first_name} {tenant_user.last_name} has made a security deposit payment for the amount of ${float(invoice.amount_paid/100)} for unit {rental_unit.name} at {rental_property.name}",
                                    type="security_deposit",
                                    title="Security Deposit Payment",
                                    resource_url=f"/dashboard/owner/transactions/{invoice_transaction.id}",
                                )
                            elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                                #Create an email notification for the owner about the the tenant's security deposit payment
                                client_hostname = os.getenv("CLIENT_HOSTNAME")
                                postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                                to_email = ""
                                if os.getenv("ENVIRONMENT") == "development":
                                    to_email = "keyflowsoftware@gmail.com"
                                else:
                                    to_email = owner_user.email
                                postmark.emails.send(
                                    From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                                    To=to_email,
                                    Subject="Security Deposit Payment Notification",
                                    HtmlBody=f"<p>{tenant_user.first_name} {tenant_user.last_name} has made a security deposit payment for the amount of ${float(invoice.amount_paid/100)} for unit {rental_unit.name} at {rental_property.name}</p> <a href='{client_hostname}/dashboard/owner/transactions/{invoice_transaction.id}'>View Transaction</a>",
                                )
                    except StopIteration:
                        # Handle case where "invoice_paid" is not found

                        pass
                    except KeyError:
                        # Handle case where "values" key is missing in "invoice_paid"

                        pass
                else:
                    return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "ok"})
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
