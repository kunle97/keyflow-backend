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
class DocuSignCreateUserView(APIView):
    def post(request):
        # Get the access token from your storage (e.g., database)
        access_token = "YOUR_ACCESS_TOKEN"  # Retrieve the access token from where you stored it
    
        # Define the endpoint for user creation
        user_creation_url = 'https://account-d.docusign.com/oauth/restapi/v2/accounts/YOUR_ACCOUNT_ID/users'
    
        # Define the user data you want to create (customize this as needed)
        user_data = {
            "user_name": "newuser@example.com",
            "email": "newuser@example.com",
            "password": "UserPassword123",
            "user_settings": {
                "can_send_envelopes": True,
                "can_send_envelopes_from_template": True,
                "can_use_draft_envelopes": True
            }
        }
    
        # Set up headers with the access token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
        # Make the POST request to create the user
        response = requests.post(user_creation_url, json=user_data, headers=headers)
    
        if response.status_code == 201:
            return JsonResponse({'status': 'User created successfully'}, status=201)
        else:
            return JsonResponse({'error': 'User creation failed'}, status=response.status_code)

class DocuSignUploadDocumentCreateTemplateView(APIView):
    def post(request):
        
        # Define the access token
        access_token = "YOUR_ACCESS_TOKEN"  # Replace with the actual access token
    
        # Define the DocuSign API base URL
        api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL
    
        # Define the headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
        # Define the user's DocuSign account ID
        user_account_id = "YOUR_USER_ACCOUNT_ID"  # Replace with the user's account ID
    
        # Step 1: Upload the document to the user's account
        base64_file = None
        try:
            # Check if a file was uploaded in the request
            if 'file' in request.FILES:
                uploaded_file = request.FILES['file']
    
                # Get the file extension
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
                # Check if the file extension is allowed (PDF or DOCX)
                if file_extension not in ('.pdf', '.docx'):
                    return JsonResponse({'error': 'Invalid file type. Only PDF and DOCX are allowed.'}, status=400)
    
                # Read the content of the uploaded file
                file_content = uploaded_file.read()
    
                # Encode the file content to base64
                base64_file = base64.b64encode(file_content).decode()
    
                # You can now use 'base64_content' in your API request
            else:
                return JsonResponse({'error': 'No file uploaded.'}, status=400)
                
        document_data = {
            "documentName": "My Document.pdf",
            "documentBase64": base64_file,  # Replace with the actual base64-encoded document content
        }
    
        upload_document_endpoint = f"{api_base_url}/accounts/{user_account_id}/envelopes"
        
        response = requests.post(upload_document_endpoint, json=document_data, headers=headers)
        
        if response.status_code == 201:
            response_data = response.json()
            document_id = response_data.get("envelopeId")
            print(f"Document uploaded successfully with ID: {document_id}")
            
            # Step 2: Create a template from the uploaded document
            template_data = {
                "documents": [
                    {
                        "documentBase64": "BASE64_ENCODED_DOCUMENT_CONTENT",  # Replace with the actual base64-encoded document content
                        "documentName": "My Document.pdf",
                        "fileExtension": "pdf",
                        "order": "1",
                    }
                ],
                "name": "My Template",
            }
    
            create_template_endpoint = f"{api_base_url}/accounts/{user_account_id}/templates"
            
            response = requests.post(create_template_endpoint, json=template_data, headers=headers)
            
            if response.status_code == 201:
                response_data = response.json()
                template_id = response_data.get("templateId")
                print(f"Template created successfully with ID: {template_id}")
                
                # Step 3: Tether the template to the user
                tether_data = {
                    "envelopeTemplateDefinition": {
                        "templateId": template_id,
                        "name": "Tethered Template"
                    }
                }
    
                tether_template_endpoint = f"{api_base_url}/accounts/{user_account_id}/templates/{template_id}"
                
                response = requests.put(tether_template_endpoint, json=tether_data, headers=headers)
                
                if response.status_code == 200:
                    print(f"Template tethered successfully to the user.")
                else:
                    print(f"Failed to tether the template. Status code: {response.status_code}")
                    print(response.text)
            
            else:
                print(f"Failed to create the template. Status code: {response.status_code}")
                print(response.text)
            
        else:
            print(f"Failed to upload the document. Status code: {response.status_code}")
            print(response.text)
class DocuSignGenerateTemplateEditorView(APIView):
    # views.py
    def post(request):
        # Get the access token from your storage (e.g., database)
        access_token = "YOUR_ACCESS_TOKEN"  # Retrieve the access token from where you stored it
    
        # Define the endpoint for creating an envelope with a template
        envelope_creation_url = 'https://demo.docusign.net/restapi/v2.1/accounts/YOUR_ACCOUNT_ID/envelopes'
    
        # Define the envelope data, including the template ID
        envelope_data = {
            "templateId": "YOUR_TEMPLATE_ID",
            "status": "sent",
            "templateRoles": [
                {
                    "roleName": "Signer1",
                    "name": "Recipient Name",
                    "email": "recipient@example.com"
                }
            ]
        }
    
        # Set up headers with the access token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
        # Make the POST request to create the envelope
        response = requests.post(envelope_creation_url, json=envelope_data, headers=headers)
    
        if response.status_code == 201:
            envelope_id = response.json().get('envelopeId')
    
            # Generate the URL for the recipient view
            envelope_view_url = f'https://demo.docusign.net/Signing/startinsession.aspx?t={envelope_id}'
    
            return JsonResponse({'url': envelope_view_url}, status=201)
        else:
            return JsonResponse({'error': 'Envelope creation failed'}, status=response.status_code)

class DocuSignListUserTemplatesView(APIView):
    post(request):
        api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
        get_templates_endpoint = f"{api_base_url}/accounts/{user_account_id}/templates"
    
        response = requests.get(get_templates_endpoint, headers=headers)
    
        if response.status_code == 200:
            return response.json().get("envelopeTemplates")
        else:
            return None
        
            except Exception as e:
                return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

class DocuSignRetrieveUserTemplateView(APIView):
    post(request):
        user_account_id = request.data.get('user_account_id') 
        access_token  = request.data.get('access_token') 
        template_id = request.data.get('template_id')
        api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL
    
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
        get_template_endpoint = f"{api_base_url}/accounts/{user_account_id}/templates/{template_id}"
    
        response = requests.get(get_template_endpoint, headers=headers)
    
        if response.status_code == 200:
            return response.json()
        else:
            return None

class DocuSignListUserEnvelopesView(APIView):
    post(request):
        try:
            access_token = "YOUR_ACCESS_TOKEN"  # Replace with the user's access token
            account_id = "YOUR_ACCOUNT_ID"  # Replace with the user's account ID
    
            api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL
    
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
    
            list_envelopes_endpoint = f"{api_base_url}/accounts/{account_id}/envelopes"
    
            response = requests.get(list_envelopes_endpoint, headers=headers)
    
            if response.status_code == 200:
                saved_envelopes = response.json()
                return JsonResponse({'saved_envelopes': saved_envelopes})
            else:
                return JsonResponse({'error': 'Failed to retrieve saved envelopes.'}, status=400)
    
        except Exception as e:
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

class DocuSignRetrieveUserEnvelopeView(APIView):
    post(request):
        user_account_id = request.data.get('user_account_id') 
        access_token  = request.data.get('access_token') 
        envelope_id = request.data.get('envelope_id')
        api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL
    
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
        get_envelope_endpoint = f"{api_base_url}/accounts/{user_account_id}/envelopes/{envelope_id}"
    
        response = requests.get(get_envelope_endpoint, headers=headers)
    
        if response.status_code == 200:
            return response.json()
        else:
            return None


class DocuSignSendEnvelopeView(APIView):
    def post(request):
        user_account_id = request.data.get('user_account_id'), 
        access_token = request.data.get('access_token'), 
        envelope_id = request.data.get('envelope_id'), 
        recipient_email = request.data.get('recipient_email'), 
        recipient_name = request.data.get('recipient_name')
        api_base_url = "https://demo.docusign.net/restapi/v2"  # Replace with the correct base URL
    
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
        send_envelope_endpoint = f"{api_base_url}/accounts/{user_account_id}/envelopes/{envelope_id}/createSenderView"
    
        recipient_data = {
            "email": recipient_email,
            "name": recipient_name,
        }
    
        data = {
            "recipient_view_request": {
                "authentication_method": "email",
                "return_url": "http://your-redirect-uri.com",  # Replace with the actual redirect URL
                "client_user_id": recipient_email,
                "recipient": recipient_data,
            }
        }
    
        response = requests.post(send_envelope_endpoint, json=data, headers=headers)
    
        if response.status_code == 201:
            response_data = response.json()
            sender_view_url = response_data.get("url")
            return sender_view_url
        else:
            return None
