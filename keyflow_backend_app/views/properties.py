import json
import stat
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 
import csv
from rest_framework.parsers import MultiPartParser
from django.core.exceptions import ValidationError
from io import TextIOWrapper
from rest_framework.response import Response
from rest_framework import status
from keyflow_backend_app.models.portfolio import Portfolio
from keyflow_backend_app.models.account_type import Owner, Staff
from ..models.user import User
from ..models.rental_property import  RentalProperty
from ..models.rental_unit import  RentalUnit
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_property_serializer import RentalPropertySerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = RentalProperty.objects.all()
    serializer_class = RentalPropertySerializer
    permission_classes = [IsAuthenticated] #TODO: Add IsResourceOwner, PropertyCreatePermission, PropertyDeletePermission permissions
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser]
    # pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['name', 'street', 'created_at', 'id', 'state' ]
    search_fields = ['name', 'street' ]
    filterset_fields = ['city', 'state']

    def get_serializer_context(self): #TODO: Delete if not needed
            # Make sure you include the context in the serializer instance
            return {'request': self.request}
    
    
    def get_queryset(self):
        user = self.request.user  # Get the current user
        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            queryset = super().get_queryset().filter(owner=owner)
            return queryset
        elif user.account_type == "staff":
            staff = Staff.objects.get(user=user)
            #retrieve staff renatal assignemnts
            rental_assignments_dict = json.loads(staff.rental_assignments)
            if rental_assignments_dict["assignment_type"] != "properties":
                raise PermissionDenied("You do not have access to properties")
            
            property_ids = rental_assignments_dict["value"]
            #check if the staff has access to the property
            if int(self.kwargs.get('pk')) not in property_ids:
                raise PermissionDenied("You do not have access to this resource")

            #Retrieve staff's owner and filter properties by owner
            owner = Owner.objects.get(user=staff.owner.user)
            queryset = super().get_queryset().filter(owner=owner)
            return queryset
    
    @action(detail=False, methods=['get'], url_path='filters')
    def retireve_filter_data(self, request):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        user_properties = RentalProperty.objects.filter(owner=owner)
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
    
    

    @action(detail=False, methods=['post'], url_path="upload-csv-properties") #POST: api/properties/upload-csv-properties
    def upload_csv_propertiess(self, request, pk=None):
        file_obj = request.FILES['file']

        # Assuming your CSV file has columns: name, beds, baths, size
        # You might need to adjust the column names based on your actual CSV file structure
        try:
            decoded_file = TextIOWrapper(file_obj.file, encoding='utf-8')
            csv_reader = csv.DictReader(decoded_file)
            
            user = request.user
            owner = Owner.objects.get(user=user)
            
            keys_to_handle = ['street', 'city', 'state', 'zip_code', 'country']

            for row in csv_reader:
                # Use a dictionary comprehension to handle keys and strip values
                property_data = {key: row.get(key, '').strip() if row.get(key) else None for key in keys_to_handle}

                # Create RentalProperty object
                RentalProperty.objects.create(
                    owner=owner,
                    name=row['name'].strip(),  # Optionally, you can strip whitespace from values
                    **property_data  # Unpack the dictionary into keyword arguments
    )

            return Response({'message': 'Units created successfully.'}, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'message': f'Error processing CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path="upload-csv-units") #POST: api/properties/{id}/upload-csv
    def upload_csv_units(self, request, pk=None):
        file_obj = request.FILES['file']

        #Retrieve rental_property_id from the detail kwarg
        rental_property_id = pk
        rental_property = RentalProperty.objects.get(id=rental_property_id)

        # Assuming your CSV file has columns: name, beds, baths, size
        # You might need to adjust the column names based on your actual CSV file structure
        try:
            decoded_file = TextIOWrapper(file_obj.file, encoding='utf-8')
            csv_reader = csv.DictReader(decoded_file)
            
            user = request.user
            owner = Owner.objects.get(user=user)

            for row in csv_reader:
                RentalUnit.objects.create(
                    owner=owner,
                    name=row['name'].strip(),  # Optionally, you can strip whitespace from values
                    beds=row['beds'].strip(),
                    baths=row['baths'].strip(),
                    rental_property=rental_property,
                    size=row['size'].strip(),
                )

            return Response({'message': 'Units created successfully.',}, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'message': f'Error processing CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)

    #Create a fucntion to update the property preferences. once a preference is updated all of the units matching preferences should be updated. url_path: api/properties/{id}/update-preferences
    @action(detail=True, methods=['patch'], url_path="update-preferences")
    def update_preferences(self, request, pk=None):
        property_instance = self.get_object()
        data = request.data.copy()
        property_instance.preferences = data["preferences"]
        property_instance.save()

        preferences_dict = json.loads(data["preferences"])
        units = RentalUnit.objects.filter(rental_property=property_instance)

        for unit in units:
            unit_preferences = json.loads(unit.preferences)
            for preference in preferences_dict:
                for unit_preference in unit_preferences:
                    if preference['name'] == unit_preference['name']:
                        unit_preference['value'] = preference['value']

            # Save the updated preferences back to the unit
            unit.preferences = json.dumps(unit_preferences)
            unit.save()

        return JsonResponse({'message': 'Preferences updated successfully.'}, status=200)

    #Create a function to update the property's portfolio. When the portfolio is updated its url_path: api/properties/{id}/update-portfolio
    @action(detail=True, methods=['patch'], url_path="update-portfolio")
    def update_portfolio(self, request, pk=None):
        property_instance = self.get_object()
        data = request.data.copy()
        print(data)
        portfolio_instance = Portfolio.objects.get(id=data["portfolio"])
        portfolio_preferences = json.loads(portfolio_instance.preferences)


        property_preferences = json.loads(property_instance.preferences)
        for updated_pref in portfolio_preferences:
            for pref in property_preferences:
                if updated_pref["name"] == pref["name"]:
                    pref["value"] = updated_pref["value"]
                    break  # Exit the loop once updated
        property_instance.preferences = json.dumps(property_preferences)
        property_instance.save()

        # Update unit preferences
        units = property_instance.rental_units.all()
        for unit in units:
            unit_preferences = json.loads(unit.preferences)
            for updated_pref in portfolio_preferences:
                for pref in unit_preferences:
                    if updated_pref["name"] == pref["name"]:
                        pref["value"] = updated_pref["value"]
                        break  # Exit the loop once updated
            unit.preferences = json.dumps(unit_preferences)
            unit.save()

        return JsonResponse({'message': 'Portfolio updated successfully.', "status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    
#Used to retrieve property info unauthenticated
class RetrievePropertyByIdView(APIView):
    def post(self, request):
        property_id = request.data.get('property_id')
        property = RentalProperty.objects.get(id=property_id)
        serializer = RentalPropertySerializer(property)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)

