import os
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from datetime import timedelta, timezone, datetime
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response

from keyflow_backend_app.helpers import make_id
from ..models.user import User
from ..models.password_reset_token import PasswordResetToken
from ..serializers.password_reset_token_serializer import PasswordResetTokenSerializer
load_dotenv()


#Create a modle viewset that will handle the CRUD operations for PasswordResetTokens
class PasswordResetTokenView(viewsets.ModelViewSet):
    serializer_class = PasswordResetTokenSerializer
    queryset = PasswordResetToken.objects.all()
    
    #Create a function that validates a password reset token 
    @action(detail=False, methods=['post'], url_path='validate-token')
    def validate_token(self, request, pk=None):
        data = request.data.copy()
        token = data['token']
        password_reset_token = PasswordResetToken.objects.get(token=token)
        if password_reset_token is None:
            return Response({'message': 'Invalid token.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Token is valid.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    #Create a function to create a password reset token for a user but verifies that the email exdists first
    @action(detail=False, methods=['post'], url_path='create-reset-token')
    def create_reset_token(self, request, pk=None):
        data = request.data.copy()
        email = data['email']

        # user = User.objects.get(email=email).DoesNotExist
        if User.objects.filter(email=email).exists() is False:
            return Response({'message': 'Error creating password reset token.', 'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
        
        #delete any existing password reset tokens matching with this email
        existing_password_reset_tokens = PasswordResetToken.objects.filter(email=email)
        if existing_password_reset_tokens is not None:
            existing_password_reset_tokens.delete()

        #create a password reset token for the user
        password_reset_token = PasswordResetToken.objects.create(
            email=email,
            token=make_id(100),
            #set token to expire in an hour
            expires_at=datetime.now(timezone.utc)+timedelta(hours=1)
        )

        #Send email to user with the password reset token
        client_hostname = os.getenv("CLIENT_HOSTNAME")
        #Send Activation Email
        postmark = PostmarkClient(server_token=os.getenv('POSTMARK_SERVER_TOKEN'))
        to_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            to_email = "keyflowsoftware@gmail.com"
        else:
            to_email = email
        reset_link = f'{client_hostname}/dashboard/reset-password/{password_reset_token.token}'
        postmark.emails.send(
            From=os.getenv('KEYFLOW_SENDER_EMAIL'),
            To=to_email,
            # To="info@keyflow.co", #TODO: Change this to user.email when postmark is verified
            Subject='KeyFlow Account Password Reset',
            HtmlBody=f'Click <a href="{reset_link}">here</a> to reset your password',
        )
        #Return response with susccess message and status 200
        return Response({'message': 'Password reset token created successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

    #create a custom function that validates a password reset token and resets the password
    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        data = request.data.copy()
        token = data['token']
        password = data['new_password']
        password_reset_token = PasswordResetToken.objects.get(token=token)
        if password_reset_token is None:
            return Response({'message': 'Invalid token.', 'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        #Retrieve user via email
        user = User.objects.get(email=password_reset_token.email) 
        user.set_password(password)
        user.save()
        #Create an email notification for the user that the password has been changed
        postmark   =  PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
        to_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            to_email = "keyflowsoftware@gmail.com"
        else:
            to_email = user.email
        postmark.emails.send(
            From=os.getenv("KEYFLOW_SENDER_EMAIL"),
            To=to_email,
            Subject="Keyflow Password Changed",
            HtmlBody=f"Your password has been changed successfully. If you did not make this change, please contact us immediately.",
        )
        #delete the password reset token
        password_reset_token.delete()
        return Response({'message': 'Password reset successfully.','status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
