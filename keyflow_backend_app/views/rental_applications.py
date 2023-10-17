from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from ..models.user import User
from ..models.notification import Notification
from ..models.rental_application import RentalApplication
from ..serializers.rental_application_serializer import RentalApplicationSerializer
from ..permissions import RentalApplicationCreatePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

class RetrieveRentalApplicationByApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get('approval_hash')
        rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
        serializer = RentalApplicationSerializer(rental_application)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RentalApplicationViewSet(viewsets.ModelViewSet):
    queryset = RentalApplication.objects.all()
    serializer_class = RentalApplicationSerializer
    permission_classes =[ RentalApplicationCreatePermission]#TODO: Investigate why IsResourceOwner is not working
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['first_name', 'last_name', 'email' ]
    filterset_fields = ['first_name', 'last_name', 'email', 'phone_number' ]
    ordering_fields = ['first_name', 'last_name', 'email', 'phone_number', 'created_at' ]
    
    def get_queryset(self):
        user = self.request.user  # Get the current user
        queryset = super().get_queryset().filter(landlord=user)
        return queryset
    
    #Create a method to create a rental application for a specific unit that also creat a notification for the landlord
    @action(detail=True, methods=['post'], url_path='create-rental-application')
    def create_rental_application(self, request, pk=None):
        data = request.data.copy()
        unit = self.get_object()
        user = User.objects.get(id=data['user_id'])
        rental_application = RentalApplication.objects.create(
            unit=unit,
            user=user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone_number=data['phone_number'],
            approval_hash=data['approval_hash'],
        )
        #Create a notification for the landlord that a new rental application has been submitted
        notification = Notification.objects.create(
            user=unit.user,
            message=f'{user.first_name} {user.last_name} has submitted a rental application for unit {unit.name} at {unit.rental_property.name}',
            type='rental_application_submitted',
            title='Rental Application Submitted',
        )
        return Response({'message': 'Rental application created successfully.'})

    #Create method to delete all rental applications for a specific unit
    @action(detail=True, methods=['delete'], url_path='delete-remaining-rental-applications')
    def delete_remaining_rental_applications(self, request, pk=None):
        application = self.get_object()
        rental_applications = RentalApplication.objects.filter(unit=application.unit,is_archived=False)
        rental_applications.delete()
        return Response({'message': 'Rental applications deleted successfully.'})

    #Create a method to approve a rental application
    @action(detail=True, methods=['post'], url_path='approve-rental-application')
    def approve_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        request_user = request.data.get('user_id')
        print(f'Reqeust User id: {request_user}')
        print(f'Landlord id: {rental_application.landlord.id}')
        if rental_application.landlord == request_user:
            rental_application.is_approved = True
            rental_application.save()
            return Response({'message': 'Rental application approved successfully.'})
        return Response({'message': 'You do not have the permissions to access this resource'})
    
    #Create a method to reject and delete a rental application
    @action(detail=True, methods=['post'], url_path='reject-rental-application')
    def reject_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        if request.user.is_authenticated and rental_application.landlord == request.user:
            rental_application.is_approved = False
            rental_application.save()
            rental_application.delete()
            return Response({'message': 'Rental application rejected successfully.'})
        return Response({'message': 'You do not have the permissions to access this resource'})
 