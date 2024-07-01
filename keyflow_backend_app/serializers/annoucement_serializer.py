import json
from rest_framework import serializers
from ..models.announcement import Announcement
from ..models.rental_unit import RentalUnit
from ..models.rental_property import RentalProperty
from ..models.portfolio import Portfolio
from .rental_property_serializer import RentalPropertySerializer
from .rental_unit_serializer import RentalUnitSerializer
from .portfolio_serializer import PortfolioSerializer

class AnnouncementSerializer(serializers.ModelSerializer):
    target_object = serializers.SerializerMethodField()
    class Meta:
        model = Announcement
        fields = "__all__"

    def get_target_object(self, obj):
            target_data = obj.target  # Assuming target is a JSON string like '{"rental_unit": 1}'
            target_dict = {}  # Initialize an empty dictionary to store the parsed target data
            
            try:
                target_dict = json.loads(target_data)  # Parse the JSON string into a dictionary
            except json.JSONDecodeError:
                pass  # Handle JSON decoding error if necessary
            
            if "rental_unit" in target_dict:
                try:
                    rental_unit_id = int(target_dict["rental_unit"])  # Extract the rental_unit ID from the parsed data
                    rental_unit = RentalUnit.objects.get(id=rental_unit_id)  # Fetch the related RentalUnit object
                    rental_unit_data = RentalUnitSerializer(rental_unit).data  # Serialize the RentalUnit object
                    #append the key type to the rental_unit_data with the value "Rental Unit"
                    rental_unit_data["type"] = "Unit"
                    rental_unit_data["datatype"] = "rental_unit"
                    return rental_unit_data  # Serialize and return the RentalUnit object
                except (ValueError, RentalUnit.DoesNotExist):
                    pass  # Handle ValueErrors or DoesNotExist exceptions if necessary
            
            elif "rental_property" in target_dict:
                try:
                    rental_property_id = int(target_dict["rental_property"])
                    rental_property = RentalProperty.objects.get(id=rental_property_id)
                    rental_property_data = RentalPropertySerializer(rental_property).data
                    rental_property_data["type"] = "Property"
                    rental_property_data["datatype"] = "rental_property"
                    return rental_property_data
                except (ValueError, RentalProperty.DoesNotExist):
                    pass
            
            elif "portfolio" in target_dict:
                try:
                    portfolio_id = int(target_dict["portfolio"])
                    portfolio = Portfolio.objects.get(id=portfolio_id)
                    portfolio_data = PortfolioSerializer(portfolio).data
                    portfolio_data["type"] = "Portfolio"
                    portfolio_data["datatype"] = "portfolio"
                    return portfolio_data
                except (ValueError, Portfolio.DoesNotExist):
                    pass
            
            return None  # Return None if target data or related object is not found
