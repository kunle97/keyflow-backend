import os
import json
import logging


from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from keyflow_backend_app.models.account_type import Owner
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.rental_property import RentalProperty
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_template import  LeaseTemplate
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..permissions import  IsResourceOwner
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

import stripe

logger = logging.getLogger(__name__)
load_dotenv()

#Create a classs to retrieve one lease term from one specific unit
class RetrieveLeaseTemplateByUnitView(APIView):
    def get(self, request):
        #Retrieve the unit id from the request fro the get request params
        unit_id = request.GET.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        lease_template = unit.lease_template
        serializer = LeaseTemplateSerializer(lease_template)
        return Response(serializer.data, status=status.HTTP_200_OK)



class LeaseTemplateViewSet(viewsets.ModelViewSet):
    queryset = LeaseTemplate.objects.all()
    serializer_class = LeaseTemplateSerializer
    # permission_classes = [IsResourceOwner]
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['term', 'rent', 'security_deposit' ]
    ordering_fields = ['term', 'rent', 'security_deposit', 'created_at' ]
    filterset_fields = ['term', 'rent', 'security_deposit' ]
    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset
    def create(self, request):
        try:
            user_id = request.data.get('user_id')
            user = User.objects.get(id=user_id)
            owner = Owner.objects.get(user=user)
            
            data = request.data.copy()

            lease_template = LeaseTemplate.objects.create(
                owner=owner,
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
                additional_charges=data['additional_charges'],
                template_id=data['template_id'],
            )

            stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
            product = stripe.Product.create(
                name=f'{user.first_name} {user.last_name}\'s (User ID: {user.id}) {data["term"]} month lease @ ${data["rent"]}/month. Lease Term ID: {lease_template.id}',
                type='service',
                metadata={"seller_id": owner.stripe_account_id},
            )

            price = stripe.Price.create(
                unit_amount=data['rent'] * 100,
                recurring={"interval": "month"},
                currency='usd',
                product=product.id,
            )

            lease_template.stripe_product_id = product.id
            lease_template.stripe_price_id = price.id
            lease_template.save()

            selected_assignments_dict = json.loads(data['selected_assignments'])
            if selected_assignments_dict and data['assignment_mode']:
                if data['assignment_mode'] == 'unit':
                    for assignment in selected_assignments_dict:
                        unit = RentalUnit.objects.get(id=assignment['id'])
                        unit.lease_template = lease_template
                        unit.save()
                elif data['assignment_mode'] == 'property':
                    for assignment in selected_assignments_dict:
                        property = RentalProperty.objects.get(id=assignment['id'])
                        units = RentalUnit.objects.filter(rental_property=property)
                        for unit in units:
                            unit.lease_template = lease_template
                            unit.save()
            else:
                print("No assignments selected")
            
            serializer = LeaseTemplateSerializer(lease_template)
            
            return Response({
                'message': 'Lease term created successfully.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except User.DoesNotExist:
            return Response({'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        
        except Owner.DoesNotExist:
            return Response({'message': 'Owner does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error creating lease template: {str(e)}")
            return Response({'message': 'Error creating lease template.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #Create a functiont to handle deleting a lease term
    def destroy(self, request, pk=None):        
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        owner = Owner.objects.get(user=user)
        lease_template_id = request.data.get('lease_template_id')
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        #Check if user is the owner of the lease term
        if lease_template.owner != owner:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        lease_template.delete()
        return Response({'message': 'Lease term deleted successfully.'}, status=status.HTTP_200_OK)
    
#Create a class tto retrieve a lease term by its id and approval hash
class RetrieveLeaseTemplateByIdViewAndApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement = LeaseAgreement.objects.filter(approval_hash=approval_hash)
        #Check if a lease agreement with the approval hash exists
        if lease_agreement.exists() == False:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)

        lease_template_id = request.data.get('lease_template_id')
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        serializer = LeaseTemplateSerializer(lease_template)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
#Create a class tto retrieve a lease term by its id
class RetrieveLeaseTemplateByIdView(APIView):
    def post(self, request):
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        owner = Owner.objects.get(user=user)
        lease_template_id = request.data.get('lease_template_id')
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        #Check if user is the owner of the lease term
        if lease_template.owner != owner:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaseTemplateSerializer(lease_template)
        return Response(serializer.data, status=status.HTTP_200_OK)

#Create a class to delete a lease term by its id
class DeleteLeaseTemplateByIdView(APIView):
    def post(self, request):
        #check if user is authenticated
        user_id = request.data.get('user_id')
        user = User.objects.get(id=user_id)
        owner = Owner.objects.get(user=user)
        lease_template_id = request.data.get('lease_template_id')
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        #Check if user is the owner of the lease term
        if lease_template.owner != owner:
            return Response({'message': 'You do not have permission to access this resource.'}, status=status.HTTP_403_FORBIDDEN)
        lease_template.delete()
        return Response({'message': 'Lease term deleted successfully.'}, status=status.HTTP_200_OK)
