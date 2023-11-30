# models.py
from django.db import models
from .user import User
from datetime import datetime


def user_directory_path(instance, filename):
    # Modify to match your user identifier (e.g., user.id or user.username)
    return f"user_data/user_{instance.user.id}/{filename}"

class UploadedFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_path, max_length=1000)
    file_key = models.CharField(max_length=1000, blank=True, null=True)  # New field for file key
    subfolder = models.CharField(max_length=100, blank=True, null=True)  # New field for subfolder
    uploaded_at = models.DateTimeField(default=datetime.now, blank=False)
    file_s3_url = models.URLField(blank=True, null=True, max_length=1000)  # Store S3 URL here

    class Meta:
        db_table = "uploaded_files"

    def __str__(self):
        return self.file.name