# views.py
import os
from re import sub
import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from ..models.uploaded_file import UploadedFile
from ..models.user import User
from ..serializers.uploaded_file_serializer import UploadedFileSerializer
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated 
from rest_framework.filters import SearchFilter, OrderingFilter
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from django.shortcuts import get_object_or_404

load_dotenv()

#Create a class to retrieve a unit's images by its subfolder using the class name RetrieveUnitImagesBySubfolderView
class UnauthenticatedRetrieveImagesBySubfolderView(APIView): #TODO: secure this endpoint 
    def post(self, request):
        subfolder = request.data.get('subfolder')
        files = UploadedFile.objects.filter(subfolder=subfolder)
        serializer = UploadedFileSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FileUploadViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
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

    # def get_queryset(self):
    #     user = self.request.user
    #     queryset = super().get_queryset().filter(user=user)
    #     return queryset

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.account_type == "owner":
            owner = user.owner
            owner_uploaded_files = UploadedFile.objects.filter(user=owner.user)
            owner_permission_data = OwnerPlanAccessControl(owner)
            if len(owner_uploaded_files) >= owner_permission_data.plan_data["max_file_uploads"]:
                return Response(
                    {"message": "You have reached the maximum number of file uploads for your plan. Please upgrade your plan to upload more files.", "status":status.HTTP_400_BAD_REQUEST},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
        serializer = UploadedFileSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            uploaded_file = serializer.save()
            # Optionally, store the S3 URL in your model
            uploaded_file.file_s3_url = uploaded_file.file.url
            uploaded_file.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create list function to retrieve the user's uploaded files by using the user id
    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        subfolder = request.query_params.get("subfolder")
        user = get_object_or_404(User, id=user_id)
        queryset = UploadedFile.objects.filter(user=user, subfolder=subfolder)
        serializer = UploadedFileSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class S3FileDeleteView(APIView):
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]

    def post(self, request):
        file_id = request.data.get("id")
        file_key = request.data.get(
            "file_key"
        )  # Assuming you send the file key for deletion

        # Delete the file from S3
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_S3_REGION_NAME"),
        )

        try:
            s3_client.delete_object(
                Bucket=os.getenv("AWS_STORAGE_BUCKET_NAME"),
                Key=file_key,
            )
            # Delete the file from your model
            uploaded_file = UploadedFile.objects.get(id=file_id)
            uploaded_file.delete()
            return Response(
                {"message": "File deleted successfully"}, status=status.HTTP_200_OK
            )
        except ClientError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
