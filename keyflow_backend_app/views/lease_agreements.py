
import os
from dotenv import load_dotenv
from datetime import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models.notification import Notification
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from ..models.rental_application import RentalApplication
from ..serializers.lease_agreement_serializer import  LeaseAgreementSerializer
from ..serializers.lease_cancellation_request_serializer import  LeaseCancellationRequestSerializer
from ..permissions import IsLandlordOrReadOnly, IsTenantOrReadOnly, IsResourceOwner, ResourceCreatePermission
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
load_dotenv()



class LeaseAgreementViewSet(viewsets.ModelViewSet):
    queryset = LeaseAgreement.objects.all()
    serializer_class = LeaseAgreementSerializer
    permission_classes = [IsAuthenticated, IsLandlordOrReadOnly, IsResourceOwner]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

#Create an endpoint that will handle when a person signs a lease agreement
class SignLeaseAgreementView(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement_id = request.data.get('lease_agreement_id')
        unit_id = request.data.get('unit_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        signed_date = request.data.get('signed_date')

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        #check if the approval hash is valid with the lease agreement 
        if lease_agreement.approval_hash != approval_hash:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        
        #retrieve the lease agreement object and update the start_date and end_date and set is_active to true
        lease_agreement.start_date = start_date
        lease_agreement.end_date = end_date
        lease_agreement.is_active = True
        lease_agreement.signed_date = signed_date
        #document_id = request.data.get('document_id') TODO
        lease_agreement.save()


        #retrieve the unit object and set the is_occupied field to true
        unit = RentalUnit.objects.get(id=unit_id)
        unit.is_occupied = True
        unit.save()
        
        #Retrieve tenantfirst and last name from the rental application using  the approval hash
        rental_application = RentalApplication.objects.filter(approval_hash=approval_hash).first()
        print(f'zx Rental applicatnt {rental_application.first_name} {rental_application.last_name}')
        #Create a notification for the landlord that the tenant has signed the lease agreement
        notification = Notification.objects.create(
            user=lease_agreement.user,
            message=f'{rental_application.first_name} {rental_application.last_name} has signed the lease agreement for unit {unit.name} at {unit.rental_property.name}',
            type='lease_agreement_signed',
            title='Lease Agreement Signed',
        )

        #return a response for the lease being signed successfully
        return Response({'message': 'Lease signed successfully.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
       
#Create a function to retrieve a lease agreement by the id without the need for a token
class RetrieveLeaseAgreementByIdAndApprovalHashView(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        lease_agreement_id = request.data.get('lease_agreement_id')
        
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        #check if the approval hash is valid with the lease agreement 
        if lease_agreement.approval_hash != approval_hash:
            return Response({'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = LeaseAgreementSerializer(lease_agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LeaseCancellationRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaseCancellationRequest.objects.all()
    serializer_class = LeaseCancellationRequestSerializer
    permission_classes = [IsAuthenticated, IsTenantOrReadOnly, IsResourceOwner, ResourceCreatePermission]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def perform_create(self, serializer):
        tenant = self.request.user
        unit = tenant.unit
        if unit.lease_agreement and not unit.lease_agreement.is_active:
            raise serializers.ValidationError("Cannot request cancellation for an inactive lease.")
        serializer.save(tenant=tenant, unit=unit, request_date=timezone.now())