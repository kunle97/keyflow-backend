from rest_framework import serializers
from ..models.user import User
from ..models.uploaded_file import UploadedFile
from .uploaded_file_serializer import UploadedFileSerializer

class UserSerializer(serializers.ModelSerializer):
    uploaded_profile_picture = serializers.SerializerMethodField()
    def get_uploaded_profile_picture(self, obj):
        # Retrieve the user's uploaded file with subfolder='user_profile_picture'
        profile_picture = UploadedFile.objects.filter(user=obj, subfolder='user_profile_picture').first()
        # Serialize the file if found
        if profile_picture:
            serializer = UploadedFileSerializer(profile_picture)
            return serializer.data
        return None

    class Meta:
        model = User
        fields = '__all__'
