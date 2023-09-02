"""keyflow_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from keyflow_backend_app.views import UserViewSet, RetrieveRentalApplicationByApprovalHash,TenantVerificationView, SignLeaseAgreementView,UserActivationView,PropertyViewSet, UnitViewSet, LeaseAgreementViewSet, MaintenanceRequestViewSet,UserRegistrationView, LeaseCancellationRequestViewSet, UserLoginView, UserLogoutView, TenantRegistrationView,TransactionViewSet, LeaseTermViewSet,  RentalApplicationViewSet, PlaidLinkTokenView,AddCardPaymentMethodView,ListPaymentMethodsView, RetrieveLeaseAgreementByIdView,RetrieveLeaseTermByIdView
from keyflow_backend_app import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
router = DefaultRouter()
router.register(r'users', UserViewSet,  basename='users')
router.register(r'properties', PropertyViewSet, basename='rental_properties')
router.register(r'units', UnitViewSet, basename='rental_units')
router.register(r'lease-agreements', LeaseAgreementViewSet, basename='lease-agreements')
router.register(r'maintenance-requests', MaintenanceRequestViewSet, basename='maintenance-requests')
router.register(r'lease-cancellation-requests', LeaseCancellationRequestViewSet, basename='lease-cancellation-requests')
router.register(r'lease-terms', LeaseTermViewSet, basename='lease-terms')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'rental-applications',RentalApplicationViewSet , basename='rental-applications')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/login/', UserLoginView.as_view(), name='login'),
    path('api/auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('api/auth/register/', UserRegistrationView.as_view(), name='register'),
    path('api/auth/tenant/register/', TenantRegistrationView.as_view(), name='tenant_register'),
    path('api/auth/tenant/register/verify/', TenantVerificationView.as_view(), name='tenant_register_verify'),
    path('api/auth/tenant/register/retrieve-rental-application/', RetrieveRentalApplicationByApprovalHash.as_view(), name='tenant_register_verify'),
    path('api/plaid/create-link-token/', PlaidLinkTokenView.as_view(), name='create_plaid_link_token'),
    path('api/stripe/add-payment-method/', AddCardPaymentMethodView.as_view(), name='add_stripe_payment_method'),
    path('api/stripe/list-payment-methods/', ListPaymentMethodsView.as_view(), name='list_stripe_payment_method'),
    path('api/test_token', views.test_token, name='test_token'),
    path('api/sign-lease-agreement/',SignLeaseAgreementView.as_view(), name='sign_lease'),
    path('api/retrieve-lease-agreement/',RetrieveLeaseAgreementByIdView.as_view(), name='retrieve_lease_agreement'),
    path('api/retrieve-lease-term/',RetrieveLeaseTermByIdView.as_view(), name='retrieve_lease_term'),
    path('api/activate/<email>/<token>/', UserActivationView.as_view(), name='activate'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]