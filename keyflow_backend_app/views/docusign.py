# views.py
import os
from dotenv import load_env
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
load_env()
class DocuSignAuthorizationView(APIView):
    def get(self, request):
        # Step 1: Redirect to DocuSign authorization URL
        authorization_url = f"https://account-d.docusign.com/oauth/auth?response_type=code&scope=signature&client_id={os.getenv('DOCUSIGN_INTEGRATION_KEY')}&redirect_uri={os.getenv('DOCUSIGN_REDIRECT_URI')}"
        return Response({'authorization_url': authorization_url})

    def post(self, request):
        # Step 2: Handle the callback from DocuSign
        code = request.data.get('code')
        if not code:
            return Response({'error': 'Authorization code not provided'}, status=400)

        # Step 3: Exchange authorization code for an access token
        token_url = 'https://account-d.docusign.com/oauth/token'
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': os.getenv('DOCUSIGN_INTEGRATION_KEY'),
            'client_secret': os.getenv('DOCUSIGN_SECRET_KEY'),
            'redirect_uri': os.getenv('DOCUSIGN_REDIRECT_URI')
        }
        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            access_token = response.json().get('access_token')

            # Step 4: Store the access token securely (e.g., in your database)
            # Your code to store the access token here

            return Response({'access_token': access_token})
        else:
            return Response({'error': 'Failed to obtain access token'}, status=400)
