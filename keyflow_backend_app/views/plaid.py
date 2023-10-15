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

class PlaidLinkTokenView(APIView):
    def post(self, request):
        # Initialize the Plaid API client
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox,
            api_key={
                'clientId': os.getenv('PLAID_CLIENT_ID'),
                'secret': os.getenv('PLAID_SECRET_KEY'),
                #'plaidVersion': '2020-09-14'
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)
        #Retrieve user id from request body
        user_id = request.data.get('user_id')
        #Retrieve the user object from the database by id
        user = User.objects.get(id=user_id) 
        # Retrieve the client_user_id from the request and store it as a variable
        client_user_id = user.id
        # Create a link_token for the given user
        request = LinkTokenCreateRequest(
            products=[Products("auth")],
            client_name="Plaid Test App",
            country_codes=[CountryCode('US')],
            redirect_uri='https://domainname.com/oauth-page.html',
            language='en',
            webhook='https://webhook.example.com',
            user=LinkTokenCreateRequestUser(
                client_user_id=client_user_id
            )
        )
        response = client.link_token_create(request)
        # Send the data to the client
        return Response(response.to_dict(), status=status.HTTP_200_OK)

