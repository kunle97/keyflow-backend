import stripe
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from ..models.transaction import  Transaction


class StripeWebhookView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        payload = request.body
        event = None

        try:
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            metadata = payment_intent.get('metadata', {})
            Transaction.objects.create(
              amount=float(payment_intent.amount / 100),  # Convert to currency units
              payment_intent_id=payment_intent.id,
              user = metadata.get('landlord_id', None),
              type = metadata.get('type', None),
              description = metadata.get('description', None),
              rental_property = metadata.get('rental_property_id', None),
              rental_unit = metadata.get('rental_unit_id', None),
              tenant = metadata.get('tenant_id', None), #related tenant
              payment_method_id = metadata.get('payment_method_id', None)# or payment_intent.payment_method.id
            )

        elif event.type == 'customer.subscription.created':
            subscription = event.data.object
            metadata = subscription.get('metadata', {})
            Transaction.objects.create(
              subscription_id=subscription.id,
              amount=int(subscription.amount / 100),  # Convert to currency units
              user = metadata.get('landlord_id', None),
              type = metadata.get('type', None),
              description = metadata.get('description', None),
              rental_property = metadata.get('rental_property_id', None),
              rental_unit = metadata.get('rental_unit_id', None),
              tenant = metadata.get('tenant_id', None), #related tenant
              payment_method_id = metadata.get('payment_method_id', None),# or payment_intent.payment_method.id
            )
            print(subscription)
        return JsonResponse({'status': 'ok'})
