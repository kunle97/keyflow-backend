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


#Create a modle viewset that will handle the CRUD operations for PasswordResetTokens
class PasswordResetTokenView(viewsets.ModelViewSet):
    serializer_class = PasswordResetTokenSerializer
    queryset = PasswordResetToken.objects.all()
    
    #Create a function that validates a password reset token 
    @action(detail=False, methods=['post'], url_path='validate-token')
    def validate_token(self, request, pk=None):
        data = request.data.copy()
        token = data['token']
        password_reset_token = PasswordResetToken.objects.get(token=token)
        if password_reset_token is None:
            return Response({'message': 'Invalid token.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Token is valid.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    #Create a function to create a password reset token for a user but verifies that the email exdists first
    @action(detail=False, methods=['post'], url_path='create-reset-token')
    def create_reset_token(self, request, pk=None):
        data = request.data.copy()
        email = data['email']

        # user = User.objects.get(email=email).DoesNotExist
        if User.objects.filter(email=email).exists() is False:
            return Response({'message': 'Error creating password reset token.', 'status':status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        
        #delete any existing password reset tokens matching with this email
        existing_password_reset_tokens = PasswordResetToken.objects.filter(email=email)
        if existing_password_reset_tokens is not None:
            existing_password_reset_tokens.delete()

        #create a password reset token for the user
        password_reset_token = PasswordResetToken.objects.create(
            email=email,
            token=data['token'],
            #set token to expire in an hour
            expires_at=datetime.now(timezone.utc)+timedelta(hours=1)
        )
        #Return response with susccess message and status 200
        return Response({'reset_token':password_reset_token.token, 'message': 'Password reset token created successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    #create a custom function that validates a password reset token and resets the password
    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        data = request.data.copy()
        token = data['token']
        password = data['new_password']
        password_reset_token = PasswordResetToken.objects.get(token=token)
        if password_reset_token is None:
            return Response({'message': 'Invalid token.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        #Retrieve user via email
        user = User.objects.get(email=password_reset_token.email) 
        user.set_password(password)
        user.save()
        #delete the password reset token
        password_reset_token.delete()
        return Response({'message': 'Password reset successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
