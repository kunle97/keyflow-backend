from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models.user import User
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.maintenance_request import MaintenanceRequest
from ..models.transaction import Transaction
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_property_serializer import RentalPropertySerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.lease_agreement_serializer import LeaseAgreementSerializer
from ..serializers.maintenance_request_serializer import MaintenanceRequestSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from rest_framework import status
from rest_framework.response import Response


class LandlordTenantDetailView(APIView):
    # POST: api/users/{id}/tenant
    # Create a function to retrieve a specific tenant for a specific landlord
    # @action(detail=True, methods=['post'], url_path='tenant')
    def post(self, request):
        # Create variable for LANDLORD id
        landlord_id = request.data.get("landlord_id")
        tenant_id = request.data.get("tenant_id")

        landlord = User.objects.get(id=landlord_id)
        tenant = User.objects.filter(id=tenant_id).first()

        # Find a lease agreement matching the landlord and tenant

        # Retrieve the unit from the tenant
        unit = RentalUnit.objects.get(tenant=tenant)
        rental_property = RentalProperty.objects.get(id=unit.rental_property.id)

        # Retrieve transactions for the tenant
        transactions = Transaction.objects.filter(tenant=tenant)
        # Retrieve maintenance request
        maintenance_requests = MaintenanceRequest.objects.filter(tenant=tenant)

        user_serializer = UserSerializer(tenant, many=False)
        unit_serializer = RentalUnitSerializer(unit, many=False)
        rental_property_serializer = RentalPropertySerializer(
            rental_property, many=False
        )
        transaction_serializer = TransactionSerializer(transactions, many=True)
        maintenance_request_serializer = MaintenanceRequestSerializer(
            maintenance_requests, many=True
        )

        lease_agreement = None
        lease_agreement_serializer = None
        if LeaseAgreement.objects.filter(user=landlord, tenant=tenant).exists():
            lease_agreement = LeaseAgreement.objects.get(user=landlord, tenant=tenant)
            lease_agreement_serializer = LeaseAgreementSerializer(
                lease_agreement, many=False
            )
            
        if lease_agreement:
            response_data = {
                "tenant": user_serializer.data,
                "unit": unit_serializer.data,
                "property": rental_property_serializer.data,
                "lease_agreement": lease_agreement_serializer.data,
                "transactions": transaction_serializer.data,
                "maintenance_requests": maintenance_request_serializer.data,
                "status": status.HTTP_200_OK,
            }
        else:
            response_data = {
                "tenant": user_serializer.data,
                "unit": unit_serializer.data,
                "property": rental_property_serializer.data,
                "transactions": transaction_serializer.data,
                "maintenance_requests": maintenance_request_serializer.data,
                "status": status.HTTP_200_OK,
            }
        if landlord_id == request.user.id:
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )


class LandlordTenantListView(APIView):
    # POST: api/users/{id}/tenants
    def post(self, request):
        user = User.objects.get(id=request.data.get("landlord_id"))
        # Verify user is a landlord
        if user.account_type != "landlord":
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Retrieve landlord's properties
        properties = RentalProperty.objects.filter(user_id=user.id)
        # retrieve units for each property that are occupied
        units = RentalUnit.objects.filter(
            rental_property__in=properties, is_occupied=True
        )
        # Retrieve the tenants for each unit
        tenants = User.objects.filter(id__in=units.values_list("tenant", flat=True))
        # Create a user serializer for the tenants object
        serializer = UserSerializer(tenants, many=True)

        if user.id == request.user.id:
            return Response(
                {"tenants": serializer.data, "status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )
