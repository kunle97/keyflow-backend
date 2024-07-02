from datetime import timedelta
import os
from postmarker.core import PostmarkClient
import time
from dotenv import load_dotenv
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from keyflow_backend_app.models.expiring_token import ExpiringToken
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, authenticate, login
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from keyflow_backend_app.serializers.account_type_serializer import OwnerSerializer, TenantSerializer
from ..models.notification import Notification
from ..models.user import User
from ..models.account_type import Owner, Tenant
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.maintenance_request import MaintenanceRequest
from ..models.lease_template import LeaseTemplate
from ..models.transaction import Transaction
from ..models.rental_application import RentalApplication
from ..models.account_activation_token import AccountActivationToken
from ..serializers.notification_serializer import NotificationSerializer
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_property_serializer import RentalPropertySerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from ..serializers.rental_application_serializer import RentalApplicationSerializer

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

load_dotenv()

# Create the login endpoint view
class UserLoginView(APIView):
    def post(self, request): # POST /api/auth/login/
        email = request.data.get("email")
        password = request.data.get("password")
        user = User.objects.filter(email=email).first()
        remember_me = request.data.get("remember_me")
        print("remember_me: ", remember_me)

        expiration_time_in_days = 1
        if user is None:
            return Response(
                {"message": "Error logging you in.", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.check_password(password):
            return Response(
                {"message": "Invalid email or password.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not user.is_active:
            return Response(
                {"message": "User account is not active. Please check your email for an activation link.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)

        if remember_me:
            expiration_time_in_days = 30    
        else:
            expiration_time_in_days = 7
        
        # Set expiration to 1 minute for demonstration purposes, modify as needed
        expiration_date = timezone.now() + timedelta(days=expiration_time_in_days)
        # expiration_date = timezone.now() + timedelta(minutes=1)

        # Check if user is an owner
        if user.account_type == "owner":
            try:
                owner = Owner.objects.get(user=user)
                token = self.manage_token(user, expiration_date)
                user_serializer = UserSerializer(instance=user)
                owner_serializer = OwnerSerializer(instance=owner)
                return Response(
                    {
                        "message": "User logged in successfully.",
                        "user": user_serializer.data,
                        "owner": owner_serializer.data,
                        "token": token.key,
                        "token_expiration_date": expiration_date,
                        "statusCode": status.HTTP_200_OK,
                        "owner_id": owner.pk,
                        "isAuthenticated": True,
                    },
                    status=status.HTTP_200_OK,
                )
            except Owner.DoesNotExist:
                return Response(
                    {"message": "Owner account not found.", "status": status.HTTP_404_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND,
                )
        
        # Check if user is a tenant
        elif user.account_type == "tenant":
            try:
                tenant = Tenant.objects.get(user=user)
                token = self.manage_token(user, expiration_date)
                user_serializer = UserSerializer(instance=user)
                tenant_serializer = TenantSerializer(instance=tenant)
                return Response(
                    {
                        "message": "User logged in successfully.",
                        "user": user_serializer.data,
                        "tenant": tenant_serializer.data,
                        "token": token.key,
                        "token_expiration_date": expiration_date,
                        "statusCode": status.HTTP_200_OK,
                        "owner_id":tenant.owner.pk,
                        "tenant_id": tenant.pk,
                        "isAuthenticated": True,
                    },
                    status=status.HTTP_200_OK,
                )
            except Tenant.DoesNotExist:
                return Response(
                    {"message": "Tenant account not found.", "status": status.HTTP_404_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND,
                )

        else:
            return Response(
                {"message": "Invalid account type.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def manage_token(self, user, expiration_date):
        # Check if the user already has an active token
        existing_token = ExpiringToken.objects.filter(user=user).first()
        if existing_token:
            if existing_token.is_expired():
                existing_token.delete()
                token = ExpiringToken.objects.create(user=user, expiration_date=expiration_date)
                token.key = Token.generate_key()
                token.save()
            else:
                token = existing_token
        else:
            token = ExpiringToken.objects.create(user=user, expiration_date=expiration_date, key=Token.generate_key())

        return token
    
# create a logout endpoint that deletes the token
class UserLogoutView(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        user = request.user
        # Check if the user has an expiring token
        expiring_token = ExpiringToken.objects.filter(user=user).first()
        if expiring_token:
            expiring_token.delete()  # Delete the expiring token
            return Response(
                {"message": "User logged out successfully.", "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
            {"message": "No active token found for the user.", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

#Create a class that has a post method to check if the email exists in the database
class UserEmailCheckView(APIView):
    def post(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email=email).exists()
        if user:
            return Response(
                {"message": "Email already exists.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Email does not exist.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )
    
#Create a class that has a post method to check if a username exists in the database
class UsernameCheckView(APIView):
    def post(self, request):
        username = request.data.get("username")
        user = User.objects.filter(username=username).exists()
        if user:
            return Response(
                {"message": "Username already exists.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Username does not exist.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["account_type", "is_active"]
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["first_name", "last_name", "email", "created_at"]

    # Create a function to change password
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        user = self.get_object()
        data = request.data.copy()
        old_password = data["old_password"]
        new_password = data["new_password"]
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            #Create an email notification for the user that the password has been changed
            postmark   =  PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
            to_email = ""
            if os.getenv("ENVIRONMENT") == "development":
                to_email = "keyflowsoftware@gmail.com"
            else:
                to_email = user.email
            postmark.emails.send(
                From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                To=to_email,
                Subject="Keyflow Password Changed",
                HtmlBody=f"Your password has been changed successfully. If you did not make this change, please contact us immediately.",
            )
            
            return Response(
                {
                    "message": "Password changed successfully.",
                    "status": status.HTTP_200_OK,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": "Error changing password."}, status=status.HTTP_400_BAD_REQUEST
        )

    # GET: api/users/{id}/transactions
    # Create a function to retrieve all transactions for a specific user
    @action(detail=True, methods=["get"], url_path="transactions")
    def transactions(self, request, pk=None):
        user = self.get_object()
        transactions = Transaction.objects.filter(user=user)
        serializer = TransactionSerializer(transactions, many=True)
        if user.id == request.user.id:
            return Response(serializer.data)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )


# create an endpoint to activate the account of a new user that will set the  is_active field to true
class UserActivationView(APIView):
    def post(self, request):
        # Verify that the account activation token is valid
        account_activation_token = AccountActivationToken.objects.get(
            token=request.data.get("activation_token")
        )
        if account_activation_token is None:
            return Response(
                {"message": "Invalid token.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # retrieve user via account activation token
        user = User.objects.get(email=account_activation_token.email)

        if user is None:
            return Response(
                {"message": "Error activating user."}, status=status.HTTP_404_NOT_FOUND
            )
        user.is_active = True
        user.save()
        # Delete the account activation token
        account_activation_token.delete()
        return Response(
            {
                "account_type": user.account_type,
                "message": "User activated successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )
