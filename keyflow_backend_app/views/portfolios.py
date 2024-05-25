import json
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.models.portfolio import Portfolio
from ..serializers.portfolio_serializer import PortfolioSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework import status

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
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