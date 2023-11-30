import os
import boto3
from rest_framework import serializers
from ..models.uploaded_file import UploadedFile
from django.core.files.storage import default_storage
from datetime import datetime
from dotenv import load_dotenv
from ..helpers import make_id, generate_presigned_url

load_dotenv()


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = '__all__'
        read_only_fields = ("file_s3_url", "uploaded_at")

    def create(self, validated_data):
        user = validated_data["user"]
        file = validated_data["file"]
        subfolder = validated_data["subfolder"]
        unique_id = make_id(10)
        # Append unique id to file name before the extension
        file.name = (
            file.name.split(".")[0] + "_" + unique_id + "." + file.name.split(".")[1]
        )

        # Logic to handle the subfolder in file path construction
        def user_directory_path(instance, filename):
            # if subfolder:
            #     return f"user_data/user_{user.id}/{subfolder}/{filename}"
            return f"user_data/user_{user.id}/{filename}"

        # Save the file to S3 using Django's default storage
        file_path = user_directory_path(None, file.name)
        file_s3_url = default_storage.url(file_path)

        # Generate a presigned URL for the uploaded file
        presigned_url = generate_presigned_url(file_path)

        instance = UploadedFile.objects.create(
            user=user,
            file=file,
            file_key=file_path,  # Save the file path
            subfolder=subfolder,
            uploaded_at=datetime.now(),
            file_s3_url=file_s3_url,  # Save the presigned URL
        )

        # Update the file path before saving
        instance.file.name = file_path
        instance.save()
        return instance
