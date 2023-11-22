# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models.uploaded_file import UploadedFile
from ..models.user import User
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend, CharFilter
from rest_framework import filters
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import models
from rest_framework.filters import SearchFilter, OrderingFilter


class FileUploadViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    search_fields = [
        "file",
        "subfolder",
    ]
    ordering_fields = ["uploaded_at"]
    filterset_fields = [
        "subfolder",
        "uploaded_at",
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(user=user)
        return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        file = request.data.get("file")
        subfolder = request.data.get("subfolder")

        serializer_data = {
            "user": user.id,  # Assuming you want to save the user's ID in the field
            "file": file,
            "subfolder": subfolder,
        }

        serializer = self.get_serializer(data=serializer_data)
        if serializer.is_valid(raise_exception=True):
            uploaded_file = serializer.save()

            # Update file_s3_url with the complete URL
            uploaded_file.file_s3_url = uploaded_file.file.url
            uploaded_file.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
