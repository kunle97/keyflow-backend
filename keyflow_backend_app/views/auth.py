# users/auth.py

from datetime import timedelta
import os
import logging
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from django.utils import timezone
from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from token_extension.models import ExpiringToken
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.contrib.auth import login
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from keyflow_backend_app.serializers.account_type_serializer import OwnerSerializer, TenantSerializer
from ..models.user import User
from ..models.account_type import Owner, Tenant
from ..models.transaction import Transaction
from ..models.account_activation_token import AccountActivationToken
from ..serializers.user_serializer import UserSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

logger = logging.getLogger(__name__)
load_dotenv()

class UserLoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        remember_me = request.data.get("remember_me")

        expiration_days = 30 if remember_me else 7

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
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
        expiration_date = timezone.now() + timedelta(days=expiration_days)
        token = self.manage_token(user, expiration_date)

        user_serializer = UserSerializer(user)

        if user.account_type == "owner":
            try:
                owner = Owner.objects.get(user=user)
                owner_serializer = OwnerSerializer(owner)
                plan_data = OwnerPlanAccessControl(owner).plan_data

                return Response({
                    "message": "User logged in successfully.",
                    "user": user_serializer.data,
                    "owner": owner_serializer.data,
                    "token": token.key,
                    "token_expiration_date": token.expiring_token.expiration_date,
                    "subscription_plan_data": plan_data,
                    "statusCode": status.HTTP_200_OK,
                    "owner_id": owner.pk,
                    "isAuthenticated": True,
                }, status=status.HTTP_200_OK)

            except Owner.DoesNotExist:
                return Response(
                    {"message": "Owner account not found.", "status": status.HTTP_404_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif user.account_type == "tenant":
            try:
                tenant = Tenant.objects.get(user=user)
                tenant_serializer = TenantSerializer(tenant)

                return Response({
                    "message": "User logged in successfully.",
                    "user": user_serializer.data,
                    "tenant": tenant_serializer.data,
                    "token": token.key,
                    "token_expiration_date": token.expiring_token.expiration_date,
                    "statusCode": status.HTTP_200_OK,
                    "owner_id": tenant.owner.pk,
                    "tenant_id": tenant.pk,
                    "isAuthenticated": True,
                }, status=status.HTTP_200_OK)

            except Tenant.DoesNotExist:
                return Response(
                    {"message": "Tenant account not found.", "status": status.HTTP_404_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response(
            {"message": "Invalid account type.", "status": status.HTTP_400_BAD_REQUEST},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def manage_token(self, user, expiration_date):
        # Remove old token (if any)
        Token.objects.filter(user=user).delete()

        # Create new token
        token = Token.objects.create(user=user)

        # Link expiring metadata
        ExpiringToken.objects.create(
            token=token,
            expiration_date=expiration_date
        )

        return token

class UserLogoutView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]

    def post(self, request):
        user = request.user
        if user.is_authenticated:
            token = Token.objects.filter(user=user).first()
            if token:
                token.delete()
                return Response({"message": "User logged out successfully."}, status=status.HTTP_200_OK)
            return Response({"message": "No active token found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "User is not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)


class UserActivationView(APIView):
    def post(self, request):
        token_value = request.data.get("activation_token")
        try:
            account_activation_token = AccountActivationToken.objects.get(token=token_value)
        except AccountActivationToken.DoesNotExist:
            return Response({"message": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=account_activation_token.email)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = True
        user.save()
        account_activation_token.delete()

        return Response({
            "account_type": user.account_type,
            "message": "User activated successfully.",
            "status": status.HTTP_200_OK,
        })


class UserEmailCheckView(APIView):
    def post(self, request):
        email = request.data.get("email")
        exists = User.objects.filter(email=email).exists()
        return Response({
            "message": "Email already exists." if exists else "Email does not exist.",
            "status": status.HTTP_400_BAD_REQUEST if exists else status.HTTP_200_OK,
        })


class UsernameCheckView(APIView):
    def post(self, request):
        username = request.data.get("username")
        exists = User.objects.filter(username=username).exists()
        return Response({
            "message": "Username already exists." if exists else "Username does not exist.",
            "status": status.HTTP_400_BAD_REQUEST if exists else status.HTTP_200_OK,
        })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["account_type", "is_active"]
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["first_name", "last_name", "email", "created_at"]

    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        user = self.get_object()
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()

            postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
            to_email = "keyflowsoftware@gmail.com" if os.getenv("ENVIRONMENT") == "development" else user.email

            postmark.emails.send(
                From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                To=to_email,
                Subject="Keyflow Password Changed",
                HtmlBody="Your password has been changed successfully. If you did not make this change, please contact us immediately.",
            )

            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response({"message": "Error changing password."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="transactions")
    def transactions(self, request, pk=None):
        user = self.get_object()
        if user.id != request.user.id:
            return Response({"detail": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        transactions = Transaction.objects.filter(user=user)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    