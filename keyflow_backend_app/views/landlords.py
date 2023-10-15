
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
from ..serializers import NotificationSerializer,UserSerializer, PropertySerializer, RentalUnitSerializer, LeaseAgreementSerializer, MaintenanceRequestSerializer, LeaseCancellationRequestSerializer, LeaseTermSerializer, TransactionSerializer,PasswordResetTokenSerializer, RentalApplicationSerializer, RentalApplicationSerializer
from ..permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly, IsResourceOwner, DisallowUserCreatePermission, PropertyCreatePermission, ResourceCreatePermission,RentalApplicationCreatePermission, PropertyDeletePermission, UnitDeletePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters, serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta
import stripe
import plaid
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode


class LandlordTenantDetailView(APIView):   
    #POST: api/users/{id}/tenant
    #Create a function to retrieve a specific tenant for a specific landlord
    # @action(detail=True, methods=['post'], url_path='tenant')
    def post(self, request):
        #Create variable for LANDLORD id
        landlord_id = request.data.get('landlord_id')
        tenant_id = request.data.get('tenant_id')
        print(f'zx Landlord id: {landlord_id}')
        print(f'zx Tenant id: {tenant_id}')

        landlord = User.objects.get(id=landlord_id)
        tenant = User.objects.filter(id=tenant_id).first()

        #Find a lease agreement matching the landlord and tenant
        lease_agreement = LeaseAgreement.objects.get(user=landlord, tenant=tenant)

        #Retrieve the unit from the tenant
        unit = RentalUnit.objects.get(tenant=lease_agreement.tenant)
        rental_property = RentalProperty.objects.get(id=unit.rental_property.id)
        
        #Retrieve transactions for the tenant
        transactions = Transaction.objects.filter(tenant=tenant)
        #Retrieve maintenance request
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=tenant)

        user_serializer = UserSerializer(tenant, many=False)
        unit_serializer = RentalUnitSerializer(unit, many=False)
        property_serializer = PropertySerializer(rental_property, many=False)
        lease_agreement_serializer = LeaseAgreementSerializer(lease_agreement, many=False)
        transaction_serializer = TransactionSerializer(transactions, many=True)
        maintenance_request_serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        
        if lease_agreement is None:
            return Response({'detail': 'Landlord Tenant relationship does not exist'}, status=status.HTTP_404_NOT_FOUND)


        if landlord_id == request.user.id:
            return Response(
                {'tenant':user_serializer.data, 
                 'unit':unit_serializer.data, 
                 'property':property_serializer.data, 
                 'lease_agreement':lease_agreement_serializer.data,
                 'transactions':transaction_serializer.data,
                 'maintenance_requests':maintenance_request_serializer.data,
                 'status':status.HTTP_200_OK
                 }, status=status.HTTP_200_OK)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
class LandlordTenantListView(APIView):

    #POST: api/users/{id}/tenants
    def post(self, request):
        user = User.objects.get(id=request.data.get('landlord_id'))
        #Verify user is a landlord
        if user.account_type != 'landlord':
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
 
        #Retrieve landlord's properties
        properties = RentalProperty.objects.filter(user_id=user.id)
        #retrieve units for each property that are occupied
        units = RentalUnit.objects.filter(rental_property__in=properties, is_occupied=True)
        #Retrieve the tenants for each unit
        tenants = User.objects.filter(id__in=units.values_list('tenant', flat=True))
        #Create a user serializer for the tenants object
        serializer = UserSerializer(tenants, many=True)
        

        if user.id == request.user.id:
            return Response({'tenants':serializer.data, 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
        return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
    
