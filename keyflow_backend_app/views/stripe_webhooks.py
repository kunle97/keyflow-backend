import os
from dotenv import load_dotenv
import stripe
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from keyflow_backend_app.models.notification import Notification
from ..models.transaction import Transaction
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.account_type import Tenant
from ..models.user import User
from ..models.account_type import Owner
from keyflow_backend_app.models import rental_property

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

            print(f"Event Type: {event.type}")
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
                print(f"XZZX Metadata: {metadata}")
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
                    type=metadata.get("type", None),
                    description=metadata.get("description", None),
                    rental_property=rental_property,
                    rental_unit=rental_unit,
                    tenant=tenant,  # related tenant
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
                    resource_url=f"/dashboard/landlord/transactions/{subscription_transaction.id}",
                )
            return JsonResponse({"status": "ok"})
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
