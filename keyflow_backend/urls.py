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
from keyflow_backend_app.views import UserViewSet, PropertyViewSet, UnitViewSet, LeaseAgreementViewSet, MaintenanceRequestViewSet,UserRegistrationView, LeaseCancellationRequestViewSet, UserLoginView, TenantApplicationView
from keyflow_backend_app import views

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'properties', PropertyViewSet)
router.register(r'units', UnitViewSet)
router.register(r'lease-agreements', LeaseAgreementViewSet)
router.register(r'maintenance-requests', MaintenanceRequestViewSet)
router.register(r'lease-cancellation-requests', LeaseCancellationRequestViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/login/', UserLoginView.as_view(), name='login'),
    path('api/auth/register/', UserRegistrationView.as_view(), name='register'),
    path('api/test_token', views.test_token, name='test_token'),
    path('/submit_application/', TenantApplicationView.as_view(), name='submit_application'),
]
