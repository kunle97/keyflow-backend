from rest_framework import serializers
from ..models.rental_unit import RentalUnit
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
class RentalUnitSerializer(serializers.ModelSerializer):
    rental_property_name = serializers.SerializerMethodField()
    signed_lease_document_file = UploadedFileSerializer(many=False, read_only=False)
    class Meta:
        model = RentalUnit
        fields = "__all__"

    
    def get_rental_property_name(self, obj):
        return obj.rental_property.name  # Replace 'name' with the field you want to display
