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



class RetrieveLandlordSubscriptionPriceView(APIView):
    def post(self, request):
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        standard_plan_product = stripe.Product.retrieve("prod_OkG5FJoG1wZUyt")
        pro_plan_product = stripe.Product.retrieve("prod_Op6uc8RCVCv78W")
        standard_plan_price = stripe.Price.retrieve(standard_plan_product.default_price)
        pro_plan_price = stripe.Price.retrieve(pro_plan_product.default_price)
        serialized_products = [{
            'product_id': standard_plan_product.id,
            'name': standard_plan_product.name,
            'price': standard_plan_price.unit_amount / 100,  # Convert to dollars
            'price_id': standard_plan_price.id,
            'features': standard_plan_product.features,
            'billing_scheme':standard_plan_price.recurring
        },{
            'product_id': pro_plan_product.id,
            'name': pro_plan_product.name,
            'price': pro_plan_price.unit_amount / 100,  # Convert to dollars
            'price_id': pro_plan_price.id,
            'features': pro_plan_product.features,
            'billing_scheme': pro_plan_price.recurring
        }]
        return Response({'products':serialized_products}, status=status.HTTP_200_OK)


#Create a class that handles manageing a tenants stripe subscription (rent) called ManageTenantSusbcriptionView
class ManageTenantSubscriptionView(viewsets.ModelViewSet):
    #TODO: Investigate why authentication CLasses not working
    # queryset = User.objects.all()
    # serializer_class = UserSerializer
    # authentication_classes = [TokenAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated, DisallowUserCreatePermission]

    #Create a method to cancel a subscription called turn_off_autopay
    @action(detail=False, methods=['post'], url_path='turn-off-autopay')
    def turn_off_autopay(self, request, pk=None):
        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        #Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        #Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        #Retrieve the subscription id from the lease agreement object
        subscription_id = lease_agreement.stripe_subscription_id
        print(f'Subscription id: {subscription_id}')
        stripe.Subscription.modify(
          subscription_id,
          pause_collection={"behavior": "void"},
        )
        lease_agreement.auto_pay_is_enabled = False
        lease_agreement.save()
        #Return a response
        return Response({'message': 'Subscription paused successfully.', "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    
    #Create a method to create a subscription called turn_on_autopay
    @action(detail=False, methods=['post'], url_path='turn-on-autopay')
    def turn_on_autopay(self, request, pk=None):
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        #Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        #Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        subscription_id = lease_agreement.stripe_subscription_id

        stripe.Subscription.modify(
          subscription_id,
          pause_collection='',
        )
        lease_agreement.auto_pay_is_enabled = True
        lease_agreement.save()
        #Return a response
        return Response({'message': 'Subscription resumed successfully.', "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    
    #Create a get function to retrieve the next payment date for rent for a specific user
    @action(detail=False, methods=['post'], url_path='next-payment-date')
    def next_payment_date(self, request, pk=None):
        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        print(f'User id: {user_id}')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        #Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        #Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)

        # Input lease start date (replace with your actual start date)
        lease_start_date = datetime.fromisoformat(f"{lease_agreement.start_date}")  # Example: February 28, 2023

        # Calculate the current date
        current_date = datetime.now()

        # Calculate the next payment date
        while lease_start_date < current_date:
            
            next_month_date = lease_start_date + timedelta(days=30)  # Assuming monthly payments
            # Ensure that the result stays on the same day even if the next month has fewer days
            # For example, if input_date is January 31, next_month_date would be February 28 (or 29 in a leap year)
            # This code snippet adjusts it to February 28 (or 29)
            if lease_start_date.day != next_month_date.day:
                next_month_date = next_month_date.replace(day=lease_start_date.day)
                lease_start_date = next_month_date
            else:
                lease_start_date += timedelta(days=30)  # Assuming monthly payments

        next_payment_date = lease_start_date
        #Return a response
        return Response({'next_payment_date': next_payment_date, "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)


    #Create a method to retrieve all payment dates for a specific user's subscription
    @action(detail=False, methods=['post'], url_path='payment-dates')
    def payment_dates(self, request, pk=None):
        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        #Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        #Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)

        # Input lease start date (replace with your actual start date)
        lease_start_date = datetime.fromisoformat(f"{lease_agreement.start_date}")  # Example: February 28, 2023
        
        # Calculate the lease end date
        lease_end_date = datetime.fromisoformat(f"{lease_agreement.end_date}")  # Example: February 28, 2023

        #Create a ppayment dates list
        payment_dates = [{'title':'Rent Due','payment_date':lease_start_date, 'transaction_paid':False}]

         # Calculate the next payment date
        while lease_start_date <= lease_end_date:
            #Check for transaction in database to see if payment has been made
            transaction_paid = Transaction.objects.filter(rental_unit=unit, created_at=lease_start_date).exists()
            event_title = ''
            if transaction_paid:
                event_title = 'Rent Paid'
            else:
                event_title = 'Rent Due'


            next_month_date = lease_start_date + timedelta(days=30)  # Assuming monthly payments
            # Ensure that the result stays on the same day even if the next month has fewer days
            # For example, if input_date is January 31, next_month_date would be February 28 (or 29 in a leap year)
            # This code snippet adjusts it to February 28 (or 29)
            if lease_start_date.day != next_month_date.day:
                next_month_date = next_month_date.replace(day=lease_start_date.day)
                payment_dates.append({'title':event_title,'payment_date':next_month_date, 'transaction_paid':transaction_paid})
                lease_start_date = next_month_date
            else:
                payment_dates.append({'title':event_title,'payment_date':next_month_date, 'transaction_paid':transaction_paid})
                lease_start_date += timedelta(days=30)  # Assuming monthly payments
                
            #Add the payment date and transaction paid status to the payment dates list

        #Return a response with the payment dates list
        return Response({'payment_dates': payment_dates, "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
 
