import os
from dotenv import load_dotenv
import json
import stripe
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from keyflow_backend_app.models.account_type import Owner
from ..models.rental_unit import RentalUnit 
from ..models.lease_agreement import LeaseAgreement
from ..models.maintenance_request import MaintenanceRequest
from ..models.rental_application import RentalApplication
from ..models.uploaded_file import UploadedFile
from ..serializers.rental_unit_serializer import  RentalUnitSerializer 
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer 
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..serializers.rental_application_serializer import RentalApplicationSerializer
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from ..permissions import  IsResourceOwner, ResourceCreatePermission, UnitDeletePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
load_dotenv()

#Create a class to retrieve a unit by its id using the class name RetrieveUnitByIdView
class RetrieveUnitByIdView(APIView):
    def post(self, request):
        unit_id = request.data.get('unit_id')
        unit = RentalUnit.objects.get(id=unit_id)
        serializer = RentalUnitSerializer(unit)
        return Response(serializer.data, status=status.HTTP_200_OK) 
    

    
class UnitViewSet(viewsets.ModelViewSet):
    queryset = RentalUnit.objects.all()
    serializer_class = RentalUnitSerializer
    permission_classes = [ IsResourceOwner, ResourceCreatePermission,UnitDeletePermission]
    authentication_classes = [JWTAuthentication]
    # pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['name']
    ordering_fields = ['name', 'beds', 'baths', 'created_at', 'id']
    filterset_fields = ['name', 'beds', 'baths']

    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    #Make a create function that creates a unit with all of the expected values as well as a subscription_id to check to see what subscription plan thee user has
    def create(self, request):
        data = request.data.copy()
        user = request.user 
        owner = Owner.objects.get(user=user)
        rental_property = data['rental_property']
        subscription_id = data['subscription_id']
        product_id = data['product_id']
        units = json.loads(data['units']) #Retrieve the javascript object from from the request in the 'units' property and convert it to a python object 
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        subscription = stripe.Subscription.retrieve( 
            subscription_id, #Retrieve the subscription from stripe
        )

        #If user has the premium plan, check to see if they have 10 or less units
        if product_id == os.getenv('STRIPE_STANDARD_PLAN_PRODUCT_ID'):
            if RentalUnit.objects.filter(user=user).count() >= 10 or len(units) > 10 or len(units) + RentalUnit.objects.filter(user=user).count() > 10:
                return Response({'message': 'You have reached the maximum number of units for your subscription plan. Please upgrade to a higher plan.'}, status=status.HTTP_400_BAD_REQUEST)
            #Create the unit
            for unit in units:
                RentalUnit.objects.create(
                    rental_property_id=rental_property,
                    owner=owner,
                    name=unit['name'],
                    beds=unit['beds'],
                    baths=unit['baths'],
                    size=unit['size'],  
                )

            return Response({'message': 'Unit(s) created successfully.', 'status':status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
        
        #If user has the pro plan, increase the metered usage for the user based on the new number of units
        if product_id == os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID'):
            #Create the unit 
            for unit in units:
                RentalUnit.objects.create(
                    rental_property_id=rental_property,
                    owner=owner,
                    name=unit['name'],
                    beds=unit['beds'],
                    baths=unit['baths'],
                    size=unit['size'],  
                )
            #Update the subscriptions quantity to the new number of units
            subscription_item=stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                quantity=RentalUnit.objects.filter(owner=owner).count(),
            )
            return Response({'message': 'Unit(s) created successfully.', 'status':status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
        return Response({"message","error Creating unit"}, status=status.HTTP_400_BAD_REQUEST)
    #Create a function that override the dlete function to delete the unit and decrease the metered usage for the user
    def destroy(self, request, pk=None):
        unit = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        product_id = data['product_id']
        subscription_id = data['subscription_id']
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        subscription = stripe.Subscription.retrieve( 
            subscription_id, #Retrieve the subscription from stripe
        )
        
 
        #If user has the pro plan, decrease the metered usage for the user
        if product_id == os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID'):
            #Retrieve the subscription item from the subscription and Update the subscriptions quantity to the new number of units
            subscription_item = stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                quantity=RentalUnit.objects.filter(owner=owner).count() - 1,
            )
            unit.delete()
            return Response({'message': 'Unit deleted successfully.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
        elif product_id == os.getenv('STRIPE_STANDARD_PLAN_PRODUCT_ID'): #If user has the premium plan, delete the unit
            unit.delete()
            return Response({'message': 'Unit deleted successfully.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

        return Response({"message","error deleting unit"}, status=status.HTTP_400_BAD_REQUEST) 


    #Create a function that sets the is occupied field to true
    @action(detail=True, methods=['post'])
    def set_occupied(self, request, pk=None):
        unit = self.get_object()
        unit.is_occupied = True
        unit.save()
        return Response({'message': 'Unit set to occupied successfully.'})

    #Create a function to retireve all rental applications for a specific unit
    @action(detail=True, methods=['get'], url_path='rental-applications')
    def rental_applications(self, request, pk=None):
        unit = self.get_object()
        rental_applications = RentalApplication.objects.filter(unit=unit)
        serializer = RentalApplicationSerializer(rental_applications, many=True)
        return Response(serializer.data)

    #manage leases (mainly used by landlords)
    @action(detail=True, methods=['post'])
    def assign_lease(self, request, pk=None):
        unit = self.get_object()
        lease_id = request.data.get('lease_id')
        lease = LeaseAgreement.objects.get(id=lease_id)
        unit.lease_agreement = lease
        unit.save()
        return Response({'message': 'Lease assigned successfully.'})

    @action(detail=True, methods=['post'])
    def remove_lease(self, request, pk=None):
        unit = self.get_object()
        unit.lease_agreement = None
        unit.save()
        return Response({'message': 'Lease removed successfully.'})  
    
    #Create a function to retrieve maintenance requests for a specific unit
    @action(detail=True, methods=['get'], url_path='maintenance-requests')
    def maintenance_requests(self, request, pk=None):
        unit = self.get_object()
        maintenance_requests = MaintenanceRequest.objects.filter(unit=unit)
        serializer = MaintenanceRequestSerializer(maintenance_requests, many=True)
        return Response(serializer.data)

    #Retrieve the lease term for a specific unit endpoint: api/units/{id}/lease-template
    @action(detail=True, methods=['get'], url_path='lease-template')
    def lease_template(self, request, pk=None):
        unit = self.get_object()
        lease_template = unit.lease_template
        serializer = LeaseTemplateSerializer(lease_template)
        return Response(serializer.data)
