import os
from re import sub
from dotenv import load_dotenv
import json
import stripe
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated 
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.helpers.helpers import unitNameIsValid
from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from keyflow_backend_app.models.lease_template import LeaseTemplate
from keyflow_backend_app.models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit, default_rental_unit_lease_terms
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
    permission_classes = [ IsAuthenticated,IsResourceOwner, ResourceCreatePermission,UnitDeletePermission]
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['name']
    ordering_fields = ['name', 'beds', 'baths', 'created_at', 'id', 'is_occupied']
    filterset_fields = ['name', 'beds', 'baths', 'is_occupied']

    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset
    
    def partial_update(self, request, *args, **kwargs):
        unit = self.get_object()
        serializer = self.get_serializer(unit)
        if 'lease_terms' in request.data:
            lease_terms = request.data.get('lease_terms')
            unit.lease_terms = lease_terms
            #updated the additional charges so that thier frequencies match the lease terms rent_frequency
            lease_terms_dict = json.loads(lease_terms)
            additional_charges_dict = json.loads(unit.additional_charges)

            rent_frequency = next(
                (item for item in lease_terms_dict if item["name"] == "rent_frequency"),
                None,
            )
            #check that the additional charges is not an empty list
            if  len(additional_charges_dict) > 0:
                for charge in additional_charges_dict:
                    charge['frequency'] = rent_frequency['value']

                unit.additional_charges = json.dumps(additional_charges_dict)
                
            unit.save()
            return super().partial_update(request, *args, **kwargs)
        if 'signed_lease_document_file' in request.data:
            file_id = request.data.get('signed_lease_document_file')
            if file_id is not None:
                file = UploadedFile.objects.get(id=file_id)
                unit.signed_lease_document_file = file
                unit.save()

                return super().partial_update(request, *args, **kwargs)
            else:
                unit.signed_lease_document_file = None
                unit.save()
                return super().partial_update(request, *args, **kwargs)
        if 'template_id' in request.data:
            template_id = request.data.get('template_id')
            if template_id is  None:
                unit.template_id = None
                unit.save()
                return super().partial_update(request, *args, **kwargs)
            else:
                unit.template_id = template_id
                unit.save()
                return super().partial_update(request, *args, **kwargs)
        return super().partial_update(request, *args, **kwargs)

    #Make a create function that creates a unit with all of the expected values as well as a subscription_id to check to see what subscription plan thee user has
    def create(self, request):
        data = request.data.copy()
        user = request.user 
        owner = Owner.objects.get(user=user)
        rental_property = data['rental_property']
        rental_property_instance = RentalProperty.objects.get(id=rental_property)
        subscription_id = data['subscription_id']
        default_lease_terms = data['lease_terms']  
        lease_template = None
        if rental_property_instance.lease_template:
            lease_template = rental_property_instance.lease_template
            
        #Convert defauult lease_terms to dictionary 
        product_id = data['product_id']
        units = json.loads(data['units']) #Retrieve the javascript object from from the request in the 'units' property and convert it to a python object 
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
        if subscription_id is not None:
            subscription = stripe.Subscription.retrieve( 
                subscription_id, #Retrieve the subscription from stripe
            )
        
        #Validate the unit name using the validate_name function
        for unit in units:
            if not unitNameIsValid(rental_property, unit['name'], owner):
                return Response({'message': 'A unit with the name ' + unit['name'] + ' already exists for this property.'}, status=status.HTTP_400_BAD_REQUEST)

        #Retrieve the users stripe account
        stripe_account = stripe.Account.retrieve(owner.stripe_account_id)
        stripe_account_requirements = stripe_account.requirements.currently_due
        if len(stripe_account_requirements) > 0:
            return Response({'message': 'Please complete your stripe account onboarding before creating units.'}, status=status.HTTP_400_BAD_REQUEST)

        #Validate if user can create a new unit as per thier subscription plan
        owner_plan_permissions = OwnerPlanAccessControl(owner)
        if owner_plan_permissions.can_create_new_rental_unit(len(units)) is False:
            return Response({
                    'message': 'You have reached the maximum number of rental units allowed for your plan. Please upgrade your plan to create more rental units.',
                    "status":status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(units) > 0:
            #Create the unit
            for unit in units:
                rental_unit = RentalUnit.objects.create(
                    rental_property_id=rental_property,
                    owner=owner,
                    name=unit['name'],
                    beds=unit['beds'],
                    baths=unit['baths'],
                    size=unit['size'],
                    lease_terms=default_lease_terms
                )
                rental_unit.apply_lease_template(lease_template)

        #Check if user is on the professional or enterprise plan. if so update the metered usage for the user
        if product_id == os.getenv('STRIPE_OWNER_PROFESSIONAL_PLAN_PRODUCT_ID') or product_id == os.getenv('STRIPE_OWNER_ENTERPRISE_PLAN_PRODUCT_ID'):
            #Update the subscriptions quantity to the new number of units
            subscription_item=stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                quantity=RentalUnit.objects.filter(owner=owner).count(),
            )
            return Response({'message': 'Unit(s) created successfully.', 'status':status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
        
        return Response({'message': 'Unit(s) created successfully.', 'status':status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
  

    #Create a function that override the dlete function to delete the unit and decrease the metered usage for the user
    def destroy(self, request, pk=None):
        unit = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        data = request.data.copy()
        product_id = data['product_id']
        subscription_id = data['subscription_id']
        stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')

        if product_id is None:
            unit.delete()
            return Response({'message': 'Unit deleted successfully.', 'status':status.HTTP_204_NO_CONTENT}, status=status.HTTP_204_NO_CONTENT)

        if subscription_id is not None:
            subscription = stripe.Subscription.retrieve( 
                subscription_id, #Retrieve the subscription from stripe
            )
        
        #If user has the pro plan, decrease the metered usage for the user
        if product_id == os.getenv('STRIPE_OWNER_PROFESSIONAL_PLAN_PRODUCT_ID') or product_id == os.getenv('STRIPE_OWNER_ENTERPRISE_PLAN_PRODUCT_ID'):
            #Retrieve the subscription item from the subscription and Update the subscriptions quantity to the new number of units
            subscription_item = stripe.SubscriptionItem.modify(
                subscription['items']['data'][0].id,
                quantity=RentalUnit.objects.filter(owner=owner).count() - 1,
            )
            unit.delete()
            return Response({'message': 'Unit deleted successfully.', 'status':status.HTTP_204_NO_CONTENT}, status=status.HTTP_204_NO_CONTENT)

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

    #manage leases (mainly used by owners)
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
    
    #Create a function to assign a lease template to a unit using the unit's assign_lease_template function
    @action(detail=True, methods=['post'], url_path='assign-lease-template')
    def assign_lease_template(self, request, pk=None):
        unit = self.get_object()
        lease_template_id = request.data.get('lease_template_id')
        lease_template = LeaseTemplate.objects.get(id=lease_template_id)
        unit.apply_lease_template(lease_template)
        return Response({'message': 'Lease template assigned successfully.',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK) 

    #Create a function to remove a lease template from a unit
    @action(detail=True, methods=['patch'], url_path='remove-lease-template') #POST: /api/units/{id}/remove-lease-template
    def remove_lease_template(self, request, pk=None):
        unit = self.get_object()
        unit.remove_lease_template()
        return Response({'message': 'Lease template removed successfully.',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    
    #Create an endpoint that uses the validate_name function to check if a unit name is valid
    @action(detail=False, methods=['post'], url_path='validate-name')
    def validate_name(self, request):
        data = request.data.copy()
        rental_property = data['rental_property']
        name = data['name']
        user = request.user
        owner = Owner.objects.get(user=user)
        if not unitNameIsValid(rental_property, name, owner):
            return Response({'message': 'A unit with the name ' + name + ' already exists for this property.', "status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Unit name is valid.', "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)