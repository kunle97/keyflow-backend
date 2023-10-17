import os
from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_term import  LeaseTerm
from ..serializers.lease_term_serializer import (LeaseTermSerializer)
from ..permissions import  IsResourceOwner
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

import stripe

load_dotenv()

#Create a classs to retrieve one lease term from one specific unit
class RetrieveLeaseTermByUnitView(APIView):
    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        lease_term = unit.lease_term
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)



class LeaseTermViewSet(viewsets.ModelViewSet):
    queryset = LeaseTerm.objects.all()
    serializer_class = LeaseTermSerializer
    permission_classes = [IsAuthenticated, IsResourceOwner]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['term', 'rent', 'security_deposit' ]
    ordering_fields = ['term', 'rent', 'security_deposit' ]
    filterset_fields = ['term', 'rent', 'security_deposit' ]
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(user=user)
        return queryset


#make a viewset for lease terms
class LeaseTermCreateView(APIView):
    def post(self, request):
        user = User.objects.get(id=request.data.get('user_id'))
        data = request.data.copy()
        if user.is_authenticated and user.account_type == 'landlord':
            lease_term = LeaseTerm.objects.create(
                user=user,
                rent=data['rent'],
                term=data['term'],
                security_deposit=data['security_deposit'],
                late_fee=data['late_fee'],
                gas_included=data['gas_included'],
                water_included=data['water_included'],
                electric_included=data['electric_included'],
                repairs_included=data['repairs_included'],
                lease_cancellation_fee=data['lease_cancellation_fee'],
                lease_cancellation_notice_period=data['lease_cancellation_notice_period'],
                grace_period=data['grace_period'],
            )
            #Create a stripe product for the lease term
            stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
            product = stripe.Product.create(
                name=f'{user.first_name} {user.last_name}\'s (User ID: {user.id}) {data["term"]} month lease @ ${data["rent"]}/month. Lease Term ID: {lease_term.id}',
                type='service',
                metadata={"seller_id": user.stripe_account_id},  # Associate the product with the connected account
            )

            #Create a stripe price for the lease term
            price = stripe.Price.create(
                unit_amount=data['rent']*100,
                recurring={"interval": "month"},
                currency='usd',
                product=product.id,
            )


            #update the lease term object with the stripe product and price ids
            lease_term.stripe_product_id = product.id
            lease_term.stripe_price_id = price.id
            lease_term.save()

            return Response({'message': 'Lease term created successfully.'})
        return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)   

    #Create a method to retrive all lease terms for a specific user
    @action(detail=True, methods=['get'])
    def user_lease_terms(self, request, pk=None):
        user = self.get_object()
        lease_terms = LeaseTerm.objects.filter(user_id=user.id)
        serializer = LeaseTermSerializer(lease_terms, many=True)
        return Response(serializer.data,  status=status.HTTP_200_OK)


#Create a class tto retrieve a lease term by its id and approval hash
class RetrieveLeaseTermByIdViewAndApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement = LeaseAgreement.objects.filter(approval_hash=approval_hash)
        #Check if a lease agreement with the approval hash exists
        if lease_agreement.exists() == False:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)

        lease_term_id = request.data.get('lease_term_id')
        print(f'Lease term id: {lease_term_id}')
        lease_term = LeaseTerm.objects.get(id=lease_term_id)
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
#Create a class tto retrieve a lease term by its id
class RetrieveLeaseTermByIdView(APIView):
    def post(self, request):
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        lease_term_id = request.data.get('lease_term_id')
        lease_term = LeaseTerm.objects.get(id=lease_term_id)
        #Check if user is the owner of the lease term
        if lease_term.user != user:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaseTermSerializer(lease_term)
        return Response(serializer.data, status=status.HTTP_200_OK)

#Create a class to delete a lease term by its id
class DeleteLeaseTermByIdView(APIView):
    def post(self, request):
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        lease_term_id = request.data.get('lease_term_id')
        lease_term = LeaseTerm.objects.get(id=lease_term_id)
        #Check if user is the owner of the lease term
        if lease_term.user != user:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        lease_term.delete()
        return Response({'message': 'Lease term deleted successfully.'}, status=status.HTTP_200_OK)
