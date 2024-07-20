import json
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.models.portfolio import Portfolio
from ..serializers.portfolio_serializer import PortfolioSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework import status
from keyflow_backend_app.helpers.helpers import portfolioNameIsValid

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["name", "description", "created_at"]
    search_fields = ["name", "description", "created_at"]
    filterset_fields = ["name"]

    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        return Portfolio.objects.filter(owner=owner)

    #Override the create method to validate the name of the portfolio using the helper function portfolioNameIsValid
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        name = data.get("name")
        owner = Owner.objects.get(user=request.user)
        owner_plan_permission = OwnerPlanAccessControl(owner)
        if not owner_plan_permission.can_use_portfolios():
            return JsonResponse({'message': 'To access the portfolios feature, you need to upgrade your subscription plan to the Keyflow Owner Standard Plan or higher.', "status":status.HTTP_400_BAD_REQUEST}, status=400)
        if not portfolioNameIsValid(name, owner):
            return JsonResponse({'message': 'A portfolio with this name already exists.', "status":status.HTTP_400_BAD_REQUEST}, status=400)
        return super().create(request, *args, **kwargs)

    #Create an endpont that validates the portfolio name using the helper function portfolioNameIsValid
    @action(detail=False, methods=["post"], url_path="validate-name")
    def validate_name(self, request):
        data = request.data.copy()
        name = data.get("name")
        owner = Owner.objects.get(user=request.user)
        if not portfolioNameIsValid(name, owner):
            return JsonResponse({'message': 'Invalid portfolio name.', "status":status.HTTP_400_BAD_REQUEST}, status=400)
        return JsonResponse({'message': 'Valid portfolio name.', "status":status.HTTP_200_OK}, status=200)


    #Create a fucntion to update the portfolio preferences. once a preference is updated all of the properties and units preferences should be updated as well
    @action(detail=True, methods=["patch"], url_path="update-preferences")# PATCH /api/portfolios/{pk}/update-preferences/
    def update_preferences(self, request, pk=None):
        portfolio_instance = self.get_object()
        data = request.data.copy()
        preferences_update = json.loads(data["preferences"])

        # Update the portfolio preferences
        portfolio_preferences = json.loads(portfolio_instance.preferences)
        for updated_pref in preferences_update:
            for pref in portfolio_preferences:
                if updated_pref["name"] == pref["name"]:
                    pref["value"] = updated_pref["value"]
                    break  # Exit the loop once updated

        portfolio_instance.preferences = json.dumps(portfolio_preferences)
        portfolio_instance.save()

        # Update property preferences
        properties = portfolio_instance.rental_properties.all()
        for property in properties:
            property_preferences = json.loads(property.preferences)
            for updated_pref in preferences_update:
                for pref in property_preferences:
                    if updated_pref["name"] == pref["name"]:
                        pref["value"] = updated_pref["value"]
                        break  # Exit the loop once updated
            property.preferences = json.dumps(property_preferences)
            property.save()

            # Update unit preferences
            units = property.rental_units.all()
            for unit in units:
                unit_preferences = json.loads(unit.preferences)
                for updated_pref in preferences_update:
                    for pref in unit_preferences:
                        if updated_pref["name"] == pref["name"]:
                            pref["value"] = updated_pref["value"]
                            break  # Exit the loop once updated
                unit.preferences = json.dumps(unit_preferences)
                unit.save()

        return JsonResponse({'message': 'Preferences updated successfully.', "status":status.HTTP_200_OK}, status=200)

        #Create a function to remove the lease template from the portfolio and set all lease term for the units  values to the default values
    @action(detail=True, methods=["patch"], url_path="remove-lease-template")
    def remove_lease_template(self, request, pk=None):
        portfolio_instance = self.get_object()
        portfolio_instance.lease_template = None
        portfolio_instance.save()
        properties = portfolio_instance.rental_properties.all()
        for property in properties:
            property.lease_template = None
            property.save()
            units = property.rental_units.all()
            for unit in units:
                unit.remove_lease_template()
        return JsonResponse({'message': 'Lease template removed successfully.', "status":status.HTTP_200_OK}, status=200)