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


class ManagePaymentMethodsView(viewsets.ModelViewSet):
    #Create a function to create a payment method for a user
    @action(detail=False, methods=['post'], url_path='add-payment-method')
    def add_payment_method(self, request, pk=None):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        user_id = request.data.get('user_id')
        print(f'Req User id: {user_id}')
        print(f'User first name: {user.first_name}')
        print(f'user last name: {user.last_name}')
        print(f'Stripe customer id: {user.stripe_customer_id}')
        # Retrieve the payment method id from the request
        payment_method_id = request.data.get('payment_method_id')
        # Create a payment method for the user
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id,
        )
        # Return a response
        return Response({'message': 'Payment method added successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='delete-payment-method')
    def delete_payment_method(self, request, pk=None):
    
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        #Retrieve payment id from the request
        payment_method_id = request.data.get('payment_method_id')
        stripe.PaymentMethod.detach(        
            payment_method_id,
        )
    #Create a function to set a payment method as default
    @action(detail=False, methods=['post'], url_path='set-default-payment-method')
    def set_default_payment_method(self, request, pk=None):
       
        # Set your Stripe API key
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        
        #retrieve customer id from user object
        user = User.objects.get(id=request.user.id)
        customer_id = user.stripe_customer_id
        #Retrieve lease id from the request
        lease_id = request.data.get('lease_agreement_id')
        print(f'Lease id: {lease_id}')
        #retrieve subscription id from the lease object
        lease = LeaseAgreement.objects.get(id=lease_id)
        subscription_id = lease.stripe_subscription_id
        # Replace with the new payment method details (e.g., card token or payment method ID)
        new_payment_method = request.data.get('payment_method_id')
    
        # Retrieve the subscription
        subscription = stripe.Subscription.retrieve(subscription_id)    

        # Set the default payment method on the subscription
        subscription.default_payment_method = new_payment_method
        subscription.save()
        # Return a response
        return Response({'message': 'Default payment method set successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    #List payment methods
    @action(detail=False, methods=['post'], url_path='list-payment-methods')
    def list_payment_methods(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        # Create a payment method for the user
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card",
        )
        # Return a response
        return Response(payment_methods, status=status.HTTP_200_OK)
    #Create a function to retrieve a stripe subscription by its id
    @action(detail=False, methods=['post'], url_path='retrieve-subscription')
    def retrieve_subscription(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        #retrieve subscription id from the request
        subscription_id = request.data.get('subscription_id')
        # Create a payment method for the user
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        subscription = stripe.Subscription.retrieve(
            subscription_id,
        )
        # Return a response
        return Response(subscription, status=status.HTTP_200_OK)
#Create a class that adds a card payment method for a user
class AddCardPaymentMethodView(APIView):
    def post(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        user_id = request.data.get('user_id')
        print(f'Req User id: {user_id}')
        print(f'User first name: {user.first_name}')
        print(f'user last name: {user.last_name}')
        print(f'Stripe customer id: {user.stripe_customer_id}')
        # Retrieve the payment method id from the request
        payment_method_id = request.data.get('payment_method_id')
        # Create a payment method for the user
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id,
        )
        # Return a response
        return Response({'message': 'Payment method added successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

#Create a class that lists the users payment methods
class ListPaymentMethodsView(APIView):
    def post(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get('user_id'))
        # Retrieve the stripe account id from the user object
        stripe_customer_id = user.stripe_customer_id
        # Create a payment method for the user
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card",
        )
        # Return a response
        return Response(payment_methods, status=status.HTTP_200_OK)
