import os
import time
from dotenv import load_dotenv
from django.contrib.auth.hashers import make_password
from pytz import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
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

import stripe

load_dotenv()


# create a login endpoint
class UserLoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = User.objects.filter(email=email).first()
        print(email)
        print(user)
        if user is None:
            return Response(
                {
                    "message": "Error logging you in.",
                    "status": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        if not user.check_password(password):
            return Response(
                {
                    "message": "Invalid email or password.",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check if user accoun is active
        if user.is_active is False:
            return Response(
                {
                    "message": "User account is not active. Please check your email for an activation link.",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check if user is a owner 
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            # create a token for the user on success full login
            token = Token.objects.create(user=user)
            user_serializer = UserSerializer(instance=user)
            return Response(
                {
                    "message": "User logged in successfully.",
                    "user": user_serializer.data,
                    "token": token.key,
                    "statusCode": status.HTTP_200_OK,
                    "owner_id": owner.pk,
                    "isAuthenticated": True,
                },
                status=status.HTTP_200_OK,
            )
        # Check if user is a tenant
        if user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            # create a token for the user on success full login
            token = Token.objects.create(user=user)
            user_serializer = UserSerializer(instance=user)
            return Response(
                {
                    "message": "User logged in successfully.",
                    "user": user_serializer.data,
                    "token": token.key,
                    "statusCode": status.HTTP_200_OK,
                    "tenant_id": tenant.pk,
                    "isAuthenticated": True,
                },
                status=status.HTTP_200_OK,
            )


# create a logout endpoint that deletes the token
class UserLogoutView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(
            {"message": "User logged out successfully.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


# class UserRegistrationView(APIView):


# Create a class that retrieve a price from stripe subscriptions for landlords and returns it in the response


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
