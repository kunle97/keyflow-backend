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
from keyflow_backend_app.views.auth  import (
    UserViewSet,
    UserLoginView, 
    UserLogoutView, 
    UserRegistrationView,
    UserActivationView
)
from keyflow_backend_app.views.landlords import (
    LandlordTenantDetailView,
    LandlordTenantListView,
)
from keyflow_backend_app.views.lease_agreements import (
    LeaseAgreementViewSet,
    SignLeaseAgreementView,
    RetrieveLeaseAgreementByIdAndApprovalHashView,
    LeaseCancellationRequestViewSet,
)
from keyflow_backend_app.views.lease_terms import (
    LeaseTermViewSet,
    LeaseTermCreateView,
    DeleteLeaseTermByIdView,
    RetrieveLeaseTermByIdView,
    RetrieveLeaseTermByUnitView,
    RetrieveLeaseTermByIdViewAndApprovalHash,
)
from keyflow_backend_app.views.maintenance_requests import (
    MaintenanceRequestViewSet,
)   
from keyflow_backend_app.views.manage_subscriptions import (
    ManageTenantSubscriptionView,
    RetrieveLandlordSubscriptionPriceView,
)
from keyflow_backend_app.views.notifications import (
    NotificationViewSet,
)
from keyflow_backend_app.views.passwords import (
    PasswordResetTokenView,
)
from keyflow_backend_app.views.payment_methods import (
    ManagePaymentMethodsView,
    AddCardPaymentMethodView,
    ListPaymentMethodsView,
)
from keyflow_backend_app.views.plaid import (
    PlaidLinkTokenView,
)
from keyflow_backend_app.views.properties import (
    PropertyViewSet,
    RetrievePropertyByIdView,
)
from keyflow_backend_app.views.rental_applications import (
    RentalApplicationViewSet,
    RetrieveRentalApplicationByApprovalHash,
)
from keyflow_backend_app.views.units import (
    UnitViewSet,
    RetrieveUnitByIdView,
)
from keyflow_backend_app.views.tenants import (
    TenantViewSet,
    TenantRegistrationView,
    TenantVerificationView,
    RetrieveTenantDashboardData,
)
from keyflow_backend_app.views.transactions import (
    TransactionViewSet,
)

from keyflow_backend_app.views.stripe import (
    StripeWebhookView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from keyflow_backend_app.views.dev import (
    test_token,
    get_landlord_emails,
    generate_properties,
    generate_units
)

router = DefaultRouter()
router.register(r'users', UserViewSet,  basename='users')
router.register(r'properties', PropertyViewSet, basename='rental_properties')
router.register(r'units', UnitViewSet, basename='rental_units')
router.register(r'lease-agreements', LeaseAgreementViewSet, basename='lease-agreements')
router.register(r'maintenance-requests', MaintenanceRequestViewSet, basename='maintenance-requests')
router.register(r'lease-cancellation-requests', LeaseCancellationRequestViewSet, basename='lease-cancellation-requests')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'rental-applications',RentalApplicationViewSet , basename='rental-applications')
router.register(r'tenants', TenantViewSet, basename='tenants')
router.register(r'manage-lease', ManageTenantSubscriptionView, basename='manage_lease')
router.register(r'password-reset', PasswordResetTokenView, basename='password_reset')
router.register(r'stripe', ManagePaymentMethodsView, basename='stripe')
router.register(r'lease-terms', LeaseTermViewSet, basename='lease-terms')
router.register(r'notifications', NotificationViewSet, basename='notifications')

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
    path('api/sign-lease-agreement/',SignLeaseAgreementView.as_view(), name='sign_lease'),
    path('api/retrieve-lease-term-and-approval/',RetrieveLeaseTermByIdViewAndApprovalHash.as_view(), name='retrieve_lease_agreement-approval'),
    path('api/retrieve-lease-agreement-approval/',RetrieveLeaseAgreementByIdAndApprovalHashView.as_view(), name='retrieve_lease_agreement'),
    path('api/create-lease-term/',LeaseTermCreateView.as_view(), name='create_lease_term'),
    path('api/delete-lease-term/',DeleteLeaseTermByIdView.as_view(), name='delete_lease_term'),
    path('api/retrieve-lease-term/',RetrieveLeaseTermByIdView.as_view(), name='retrieve_lease_term'),
    path('api/retrieve-lease-term-unit/',RetrieveLeaseTermByUnitView.as_view(), name='retrieve_lease_term_unit'),
    path('api/retrieve-unit/',RetrieveUnitByIdView.as_view(), name='retrieve_unit_unauthenticated'),
    path('api/retrieve-tenant-dashboard-data/',RetrieveTenantDashboardData.as_view(), name='retrieve_tenant_dashboard_data'),
    path('api/retrieve-property/',RetrievePropertyByIdView.as_view(), name='retrieve_property_unauthenticated'),
    path('api/retrieve-landlord-subscription-prices/',RetrieveLandlordSubscriptionPriceView.as_view(), name='retrieve_landlord_subscription_price'),
    path('api/auth/activate-account/', UserActivationView.as_view(), name='activate'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/stripe-webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('api/landlord-tenant-detail/', LandlordTenantDetailView.as_view(), name='landlord_tenant_detail'),
    path('api/landlord-tenant-list/', LandlordTenantListView.as_view(), name='landlord_tenant_list'),
    #Dev urls
    path('api/test_token', test_token, name='test_token'), 
    path('api/landlords-emails/', get_landlord_emails, name='landlord_emails'),
    path('api/generate/properties/', generate_properties, name='generate_properties'),
    path('api/generate/units/', generate_units, name='generate_units'),
]