import json
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from keyflow_backend_app.models.account_type import Owner, Staff, Tenant
from keyflow_backend_app.models.staff_invite import StaffInvite
from keyflow_backend_app.serializers.portfolio_serializer import PortfolioSerializer
from keyflow_backend_app.serializers.rental_property_serializer import RentalPropertySerializer
from keyflow_backend_app.serializers.staff_invite_serializer import StaffInviteSerializer
from ..models.notification import Notification
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.rental_property import RentalProperty
from ..models.portfolio import Portfolio
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_cancelleation_request import LeaseCancellationRequest
from ..models.transaction import Transaction
from ..models.rental_application import RentalApplication
from ..models.account_activation_token import AccountActivationToken
from ..models.announcement import Announcement
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.lease_agreement_serializer import LeaseAgreementSerializer
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from ..serializers.annoucement_serializer import AnnouncementSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

class StaffRegistrationVerificationView(APIView):
    # Create a function that verifies the lease agreement id and approval hash
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        # check if approval hash exists in the Staff invites
        staff_invite_id = request.data.get("staff_invite_id")
        staff_invite = StaffInvite.objects.get(id=staff_invite_id)
        # check if the approval hash is valid with the lease agreement
        if staff_invite.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # return a response for the lease being signed successfully
        return Response(
            {"message": "Approval hash valid.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


class StaffInviteVerificationView(APIView):
    # Create a function that verifies the tenant invite and approval hash
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        staff_invite_id = request.data.get("staff_invite_id")
        owner_id = request.data.get("owner_id")
        print("Approval Hash ", approval_hash)
        print("Staff Invite ID ", staff_invite_id)
        print("Owner Id ", owner_id)

        owner = Owner.objects.get(id=owner_id)
        try:
            staff_invite = StaffInvite.objects.get(id=staff_invite_id, owner=owner)
        except StaffInvite.DoesNotExist:
            return Response(
                {"message": "Staff Invite not found.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the approval hash
        if staff_invite.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid Approval Hash", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Serialize the staff_invite object
        staff_invite_serialized = StaffInviteSerializer(staff_invite)
        # Return a response for the lease being signed successfully
        return Response(
            {
                "message": "Approval hash valid.", 
                "status": status.HTTP_200_OK, 
                "data": staff_invite_serialized.data
            },
            status=status.HTTP_200_OK,
        )

class CustomPaginationClass(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'results': data
        })
    def paginate_queryset(self, queryset, request, view=None):
        if 'all' in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)
    
class RetrieveStaffRentalAssignmentsView(APIView):
    pagination_class = CustomPaginationClass
    def get(self, request, *args, **kwargs):
        # Authenticate staff account 
        user = request.user
        user = User.objects.get(id=user.id)
        if user.account_type == "staff":
            staff = Staff.objects.get(user=user)
            rental_assignments = json.loads(staff.rental_assignments)
            assignment_type = rental_assignments["assignment_type"]
            assignment_type_ids = rental_assignments["value"]

            if assignment_type == "units":
                rental_units = RentalUnit.objects.filter(id__in=assignment_type_ids)
                serializer = RentalUnitSerializer(rental_units, many=True)
                return Response(serializer.data)
            
            elif assignment_type == "properties":
                properties = RentalProperty.objects.filter(id__in=assignment_type_ids)
                serializer = RentalPropertySerializer(properties, many=True)
                return Response(serializer.data)
            
            elif assignment_type == "portfolio":
                portfolios = Portfolio.objects.filter(id__in=assignment_type_ids)
                serializer = PortfolioSerializer(portfolios, many=True)
                return Response(serializer.data)
                
            else:
                return Response(
                    {"message": "Invalid assignment type", "status": status.HTTP_400_BAD_REQUEST},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"message": "You do not have access to this resource", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
#Create a class to retrieve the Staff members privileges
class RetrieveStaffPrivilegesView(APIView):
    def get(self, request, *args, **kwargs):
        # Authenticate staff account 
        user = request.user
        user = User.objects.get(id=user.id)
        if user.account_type == "staff":
            staff = Staff.objects.get(user=user)
            privileges = json.loads(staff.privileges)
            return Response({"privileges":privileges}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "You do not have access to this resource", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )
