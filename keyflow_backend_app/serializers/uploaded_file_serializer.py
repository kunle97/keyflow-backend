# serializers.py
from rest_framework import serializers
from ..models.uploaded_file import UploadedFile
from datetime import datetime
class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ('user', 'file', 'subfolder', 'file_s3_url', 'uploaded_at')
        read_only_fields = ('file_s3_url', 'uploaded_at')

    def create(self, validated_data):
        user = validated_data['user']
        file = validated_data['file']
        subfolder = validated_data.get('subfolder')

        # Logic to handle the subfolder in file path construction
        def user_directory_path(instance, filename):
            if subfolder:
                return f"user_data/user_{user.id}/{subfolder}/{filename}"
            return f"user_data/user_{user.id}/{filename}"

        instance = UploadedFile.objects.create(
            user=user,
            file=file,
            subfolder=subfolder,  # Save subfolder here
            uploaded_at=datetime.now(),
            file_s3_url=file.name  # Adjust this as needed
        )
        instance.file.name = user_directory_path(instance, file.name)
        instance.save()
        return instance