from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 
import csv
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from io import TextIOWrapper
from keyflow_backend_app.models.account_type import Owner
from ..models.user import User
from ..models.rental_property import  RentalProperty
from ..models.rental_unit import  RentalUnit
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_property_serializer import RentalPropertySerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..permissions import IsResourceOwner, PropertyCreatePermission, PropertyDeletePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


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
        owner = Owner.objects.get(user=user)
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

            return Response({'message': 'Units created successfully.'}, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'message': f'Error processing CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)

#Used to retrieve property info unauthenticated
class RetrievePropertyByIdView(APIView):
    def post(self, request):
        property_id = request.data.get('property_id')
        property = RentalProperty.objects.get(id=property_id)
        serializer = RentalPropertySerializer(property)
        response_data = serializer.data
        return Response(response_data, status=status.HTTP_200_OK)

