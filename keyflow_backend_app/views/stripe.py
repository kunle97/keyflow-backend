import os
from dotenv import load_dotenv
from datetime import timedelta, timezone, datetime
import json
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action, authentication_classes, permission_classes, api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models import Notification,User, RentalProperty, RentalUnit, LeaseAgreement, MaintenanceRequest, LeaseCancellationRequest, LeaseTerm, Transaction, RentalApplication, PasswordResetToken, AccountActivationToken
from ..serializers import NotificationSerializer,UserSerializer, PropertySerializer, RentalUnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer, LeaseCancellationRequestSerializer, LeaseTermSerializer, TransactionSerializer,PasswordResetTokenSerializer, RentalApplicationSerializer
from ..permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly, IsResourceOwner, DisallowUserCreatePermission, PropertyCreatePermission, ResourceCreatePermission,RentalApplicationCreatePermission, PropertyDeletePermission, UnitDeletePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers import RentalApplicationSerializer
from datetime import datetime, timedelta
import stripe
import plaid
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

load_dotenv()
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
            print(f'Event Data {event.data}')
            print(f'zx Payment intent {payment_intent}')
            print(f'zx Metadata {metadata}')
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
            print(f'Event Data {event.data}')
            print(f'zx Payment intent {subscription}')
            print(f'zx Metadata {metadata}')
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
