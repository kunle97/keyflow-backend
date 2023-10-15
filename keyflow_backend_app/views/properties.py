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


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [ IsAuthenticated, IsResourceOwner, PropertyCreatePermission, PropertyDeletePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    # pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['name', 'street', 'created_at', 'id', 'state' ]
    search_fields = ['name', 'street' ]
    filterset_fields = ['city', 'state']

    def get_queryset(self):
        user = self.request.user  # Get the current user
        queryset = super().get_queryset().filter(user=user)
        return queryset
    
    @action(detail=False, methods=['get'], url_path='filters')
    def retireve_filter_data(self, request):
        user = self.request.user
        user_properties = RentalProperty.objects.filter(user=user)
        states = user_properties.values_list('state', flat=True).distinct()
        cities = user_properties.values_list('city', flat=True).distinct()
        return Response({'states':states, 'cities':cities}, status=status.HTTP_200_OK)

    #GET: api/properties/{id}/units
    @action(detail=True, methods=['get'])
    def units(self, request, pk=None): 
        property = self.get_object()
        units = RentalUnit.objects.filter(rental_property_id=property.id)
        serializer = RentalUnitSerializer(units, many=True)
        return Response(serializer.data)
   
    #GET: api/properties/{id}/tenants
    @action(detail=True, methods=['get'])
    def tenants(self, request, pk=None):
        property = self.get_object()
        tenants = User.objects.filter(unit__property=property, account_type='tenant')
        serializer = UserSerializer(tenants, many=True)
        return Response(serializer.data)

class RetrievePropertyByIdView(APIView):
    def post(self, request):
        property_id = request.data.get('property_id')
        print(f'zx Property id: {property_id}')
        property = RentalProperty.objects.get(id=property_id)
        print(f'zx Property: {property}')
        serializer = PropertySerializer(property)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)

