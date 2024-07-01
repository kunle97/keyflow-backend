from operator import le
import os
import json
from rest_framework.response import Response
import requests
from postmarker.core import PostmarkClient
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.views import boldsign
from ..helpers import make_id
from keyflow_backend_app.models.account_type import Owner
from ..models.user import User
from ..models.notification import Notification
from ..models.rental_application import RentalApplication
from ..models.rental_unit import RentalUnit
from ..serializers.rental_application_serializer import RentalApplicationSerializer
from ..permissions import RentalApplicationCreatePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..helpers import strtobool
from keyflow_backend_app.models import rental_unit

from keyflow_backend_app.models import rental_application


class RetrieveRentalApplicationByApprovalHash(APIView):
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        rental_application = RentalApplication.objects.get(approval_hash=approval_hash)
        serializer = RentalApplicationSerializer(rental_application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RentalApplicationViewSet(viewsets.ModelViewSet):
    queryset = RentalApplication.objects.all()
    serializer_class = RentalApplicationSerializer
    permission_classes = [
        IsAuthenticated,
        RentalApplicationCreatePermission,
    ]  # TODO: Investigate why IsResourceOwner is not working
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["first_name", "last_name", "email", "phone_number","is_approved","is_archived"]
    ordering_fields =  ["first_name","last_name", "email","unit__rental_property__name","created_at","is_approved","is_archived"]

    def get_queryset(self):
        user = self.request.user  # Get the current user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset

    def get_permissions(self):
        # Allow unauthenticated users to access the create method
        if self.action == "create":
            return []
        return [IsAuthenticated()]

    # OVerride the defualt create method to create a rental application and send a notification to the owner
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        unit = RentalUnit.objects.get(id=data["unit_id"])
        user = unit.owner.user
        owner = unit.owner
        pets = data["pets"]
        vehicles = data["vehicles"]
        convicted = data["convicted"]
        bankrupcy = data["bankrupcy"]
        evicted = data["evicted"]
        #Check if the pets field is a string and convert it to a boolean
        if isinstance(pets, str):
            pets = strtobool(pets)
        #Check if the vehicles field is a string and convert it to a boolean
        if isinstance(vehicles, str):
            vehicles = strtobool(vehicles)
        #Check if the convicted field is a string and convert it to a boolean
        if isinstance(convicted, str):
            convicted = strtobool(convicted)
        #Check if the bankrupcy field is a string and convert it to a boolean
        if isinstance(bankrupcy, str):
            bankrupcy = strtobool(bankrupcy)
        #Check if the evicted field is a string and convert it to a boolean
        if isinstance(evicted, str):
            evicted = strtobool(evicted)
        rental_application = RentalApplication.objects.create(
            unit=unit,
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=data["date_of_birth"],
            email=data["email"],
            phone_number=data["phone_number"],
            desired_move_in_date=data["desired_move_in_date"],
            other_occupants=data["other_occupants"],
            pets=pets,
            vehicles=vehicles,
            convicted=convicted,
            bankrupcy_filed=bankrupcy,
            evicted=evicted,
            employment_history=data["employment_history"],
            residential_history=data["residential_history"],
            owner=owner,
            comments=data["comments"],
        )
        try:
            #Retrieve the owner's preferences
            owner_preferences = json.loads(owner.preferences)
            #Retrieve the object in the array who's "name" key value is "rental_application_created"
            rental_application_created = next(
                item for item in owner_preferences if item["name"] == "rental_application_created"
            )
            #Retrieve the "values" key value of the object
            rental_application_created_values = rental_application_created["values"]
            for value in rental_application_created_values:
                if value["name"] == "push" and value["value"] == True:
                    # Create a notification for the owner that a new rental application has been submitted
                    notification = Notification.objects.create(
                        user=user,
                        message=f"{data['first_name']} {data['last_name']} has submitted a rental application for unit {rental_application.unit.name} at {rental_application.unit.rental_property.name}",
                        type="rental_application_submitted",
                        title="Rental Application Submitted",
                        resource_url=f"/dashboard/owner/rental-applications/{rental_application.id}",
                    )
                elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                    #Create an email notification using postmark for the owner that a new rental application has been submitted
                    client_hostname = os.getenv("CLIENT_HOSTNAME")
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""
                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"
                    else:
                        to_email = user.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="New Rental Application Submitted",
                        HtmlBody=f"{data['first_name']} {data['last_name']} has submitted a rental application for unit {rental_application.unit.name} at {rental_application.unit.rental_property.name}. <a href='{client_hostname}/dashboard/owner/rental-applications/{rental_application.id}'>View Application</a>",
                    )   
        except StopIteration:
            # Handle case where "rental_application_created" is not found
            print("rental_application_created not found. Notification not sent.")
            pass
        except KeyError:
            # Handle case where "values" key is missing in "rental_application_created"
            print("values key not found in rental_application_created. Notification not sent.")
            pass

        return Response({"message": "Rental application created successfully."})

    # Create method to delete all rental applications for a specific unit
    @action(
        detail=True, methods=["delete"], url_path="delete-remaining-rental-applications"
    )
    def delete_remaining_rental_applications(self, request, pk=None):
        application = self.get_object()
        rental_applications = RentalApplication.objects.filter(
            unit=application.unit, is_archived=False
        )
        rental_applications.delete()
        return Response({"message": "Rental applications deleted successfully."})

    # Create a method to approve a rental application
    @action(detail=True, methods=["post"], url_path="approve-rental-application") #POST /api/rental-applications/{id}/approve-rental-application/
    def approve_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        unit = rental_application.unit
        user = request.user
        owner = Owner.objects.get(user=user)
        sign_link = ""
        if rental_application.owner == owner:
            approval_hash = make_id(64)
            rental_application.is_approved = True
            rental_application.is_archived = True
            rental_application.approval_hash = approval_hash
            rental_application.save()

            #Send document to be signed by making a call to the endpoint 
            payload_data = {
                "owner_id": owner.id, 
                "template_id": unit.template_id,
                "tenant_first_name": rental_application.first_name,
                "tenant_last_name": rental_application.last_name,
                "tenant_email": rental_application.email,
                "document_title": f"{rental_application.first_name} {rental_application.last_name} Lease Agreement for unit {unit.name}",
                "message": "Please sign the lease agreement to complete the rental application process.",
            }

            response = requests.post(
                f"{os.getenv('SERVER_API_HOSTNAME')}/boldsign/create-document-from-template/",
                data=payload_data,
            )
            boldsign_document_id = response.json()["documentId"]
            #Create a lease agreement
            lease_agreement = LeaseAgreement.objects.create(
                rental_application=rental_application,
                document_id=boldsign_document_id,
                rental_unit=unit,
                owner=owner,
                approval_hash=approval_hash,
            )   
            client_hostname = os.getenv("CLIENT_HOSTNAME")
            sign_link = f"{client_hostname}/sign-lease-agreement/{lease_agreement.id}/{approval_hash}/"
            try:
                if os.getenv("ENVIRONMENT") == "production":
                    #Send an email to the person who submitted the rental application that their application has been approved. rental_application.email in the to field
                    postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                    to_email = ""

                    if os.getenv("ENVIRONMENT") == "development":
                        to_email = "keyflowsoftware@gmail.com"  
                    else:
                        to_email = rental_application.email
                    postmark.emails.send(
                        From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                        To=to_email,
                        Subject="Rental Application Approved",
                        HtmlBody=f"Your rental application for unit {rental_application.unit.name} at {rental_application.unit.rental_property.name} has been approved. <a href='{sign_link}'>Sign Lease Agreement</a>",
                    )
            except Exception as e:
                print(e)
                pass
        
            #Delete remaining rental applications for the unit
            rental_applications = RentalApplication.objects.filter(
                unit=unit, is_archived=False, is_approved=False, 
            )
            rental_applications.delete()
            return Response(
                {
                    "message": "Rental application approved successfully.",
                    "approval_hash":approval_hash, 
                    "sign_link":sign_link,
                    "status": status.HTTP_200_OK,
                }, 
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )
    
    #Create a method called revokeRentalApplication to delete an approved rental application and revoke the document
    @action(detail=True, methods=["delete"], url_path="revoke-rental-application") #DELETE /api/rental-applications/{id}/revoke-rental-application/
    def revoke_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        lease_agreement = None
        #Check if rental application has a lease agreement
        if  LeaseAgreement.objects.filter(rental_application=rental_application).exists():
            lease_agreement = LeaseAgreement.objects.filter(rental_application=rental_application).first()
            #Check if the leaseagreement has a document_id
            if lease_agreement.document_id and rental_application.tenant is None:
                lease_agreement.revoke_boldsign_document()
            lease_agreement.delete()
        if request.user.is_authenticated and rental_application.owner == owner:
            rental_application.delete()
            return Response({"message": "Rental application revoked successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )

    # Create a method to reject and delete a rental application
    @action(detail=True, methods=["post"], url_path="reject-rental-application") #POST /api/rental-applications/{id}/reject-rental-application/
    def reject_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        lease_agreement = None
        #Check if rental application has a lease agreement
        if  LeaseAgreement.objects.filter(rental_application=rental_application).exists():
            lease_agreement = LeaseAgreement.objects.filter(rental_application=rental_application).first()
            #Check if the leaseagreement has a document_id
            if lease_agreement.document_id and rental_application.tenant is None:
                lease_agreement.revoke_boldsign_document()
            lease_agreement.delete()
        if request.user.is_authenticated and rental_application.owner == owner:
            rental_application.is_approved = False
            rental_application.save()
            rental_application.delete()
            return Response({"message": "Rental application rejected successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )

    #Create a method to archive a rental application
    @action(detail=True, methods=["post"], url_path="archive-rental-application")#POST /api/rental-applications/{id}/archive-rental-application/
    def archive_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        if request.user.is_authenticated and rental_application.owner == owner:
            rental_application.is_archived = True
            rental_application.save()
            return Response({"message": "Rental application archived successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )
    #Create a method to unarchive a rental application
    @action(detail=True, methods=["post"], url_path="unarchive-rental-application")#POST /api/rental-applications/{id}/unarchive-rental-application/
    def unarchive_rental_application(self, request, pk=None):
        rental_application = self.get_object()
        user = request.user
        owner = Owner.objects.get(user=user)
        if request.user.is_authenticated and rental_application.owner == owner:
            rental_application.is_archived = False
            rental_application.save()
            return Response({"message": "Rental application unarchived successfully."})
        return Response(
            {"message": "You do not have the permissions to access this resource"}
        )