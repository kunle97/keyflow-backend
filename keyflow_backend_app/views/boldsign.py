# views.py
import os
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from dotenv import load_dotenv
import requests
import json
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.models.account_type import Owner, Tenant

load_dotenv()
BOLDSIGN_API_KEY = os.getenv("BOLDSIGN_API_KEY")
BOLDSIGN_API_BASE_URL = (
    "https://api.boldsign.com/v1"  # Update to the correct BoldSign API URL
)


class CreateEmbeddedTemplateCreateLinkView(APIView):
    parser_classes = (MultiPartParser,)

    def post(
        self, request, *args, **kwargs
    ):  # This will be called when a user  confirms the uploaded file int the lease term flow
        url = "https://api.boldsign.com/v1/template/createEmbeddedTemplateUrl"
        owner_signer_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            owner_signer_email = "owner@boldsign.dev"
        else:
            owner_signer_email = request.data.get("owner_email")
        payload = {
            "Title": request.data.get("template_title"),
            "Description": request.data.get("template_description"),
            "DocumentTitle": request.data.get("document_title"),
            "DocumentMessage": request.data.get("document_description"),
            "AllowMessageEditing": "true",
            "Roles[0][name]": "Tenant",
            "Roles[0][index]": "1",
            "Roles[1][name]": "Owner",
            "Roles[1][index]": "2",
            "Roles[1][defaultSignerName]": request.data.get("owner_name"),
            "Roles[1][defaultSignerEmail]": owner_signer_email,
            "ShowToolbar": "true",
            "ShowSaveButton": "true",
            "ShowSendButton": "false",
            "ShowPreviewButton": "true",
            "ShowNavigationButtons": "true",
            "ShowTooltip": "true",
            "ViewOption": "PreparePage",
        }
        uploaded_file = request.FILES["file"]
        files = {
            "Files": (
                uploaded_file.name,
                uploaded_file.file,
                "application/pdf",
            )
        }
        headers = {"X-API-KEY": BOLDSIGN_API_KEY}
        response = requests.request(
            "POST", url, headers=headers, data=payload, files=files
        )
        if response.status_code == 201:
            return JsonResponse(
                {
                    "message": "Template created successfully",
                    "url": response.json()["createUrl"],
                    "template_id": response.json()["templateId"],
                    "status": response.status_code,
                }
            )
        else:
            return JsonResponse(
                {
                    "error": "Failed to create document",
                    "status_code": response.status_code,
                }
            )


class CreateEmbeddedTemplateEditView(APIView):
    def post(self, request, *args, **kwargs):
        url = (
            "https://api.boldsign.com/v1/template/getEmbeddedTemplateEditUrl?templateId="
            + request.data.get("template_id")
        )
        payload = {
            "ShowToolbar": "true",
            "ViewOption": "PreparePage",
            "ShowSaveButton": "true",
            "ShowCreateButton": "true",
            "ShowPreviewButton": "true",
            "ShowNavigationButtons": "true",
            "ShowTooltip": "true",
        }
        headers = {"Accept": "application/json", "X-API-KEY": BOLDSIGN_API_KEY}

        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 201:
            return JsonResponse(
                {
                    "message": "Template created successfully",
                    "url": response.json()["editUrl"],
                    "status": response.status_code,
                },
                status=response.status_code,
            )
        else:
            return Response(
                {
                    "error": "Failed to create document",
                    "status_code": response.status_code,
                },
                status=response.status_code,
            )


class CreateDocumentFromTemplateView(APIView):
    def post(self, request, *args, **kwargs):
        url = (
            "https://api.boldsign.com/v1/template/send?templateId="
            + request.data.get("template_id")
        )
        tenant_first_name = request.data.get("tenant_first_name")
        tenant_last_name = request.data.get("tenant_last_name")

        if tenant_first_name is None:
            tenant_first_name = ""
        if tenant_last_name is None:
            tenant_last_name = ""

        tenant_name = tenant_first_name + " " + tenant_last_name
        owner = Owner.objects.get(id=request.data.get("owner_id"))
        owner_user = owner.user
        owner_name = owner_user.first_name + " " + owner_user.last_name

        tenant_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            tenant_email = "tenant@boldsign.dev"
        else:
            tenant_email = request.data.get("tenant_email")

        owner_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            owner_email = "owner@boldsign.dev"
        else:
            owner_email = owner_user.email

        payload = {
            "title": request.data.get("document_title"),
            "message": request.data.get("message"),
            "roles": [
                {
                    "roleIndex": 1,
                    "signerName": tenant_name,
                    "signerEmail": tenant_email,
                },
                {
                    "roleIndex": 2,
                    "signerName": owner_name,
                    "signerEmail": owner_email,
                    "formFields": [
                        {
                            "fieldType": "Signature",
                            "pageNumber": 1,
                            "bounds": {"x": 100, "y": 100, "width": 100, "height": 50},
                        }
                    ],
                },
            ],
            "sendForSignatureTemplate": True,
            # 'OnBehalfOf': 'luthercooper@cubeflakes.com',/
        }

        headers = {
            "Accept": "application/json",
            "X-API-KEY": BOLDSIGN_API_KEY,
            "Content-Type": "application/json;odata.metadata=minimal;odata.streaming=true",
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # Print the response content (the full response body)

        try:
            if response.status_code == 429:
                return JsonResponse(
                    {
                        "error": "Too many requests",
                        "status_code": 429,
                    }
                )
            else:
                response_json = response.json()
                if "documentId" in response_json:
                    return JsonResponse(response_json)
                else:
                    return JsonResponse(
                        {
                            "errors": response_json.get("errors", []),
                            "status_code": 500,
                        }
                    )
        except json.JSONDecodeError:
            # Handle JSONDecodeError here (e.g., log the error, return an error response).
            return JsonResponse(
                {
                    "error": "Failed to parse JSON response",
                    "status_code": 500,
                }
            )


class CreateSigningLinkView(APIView):
    # Create a GET method to retrieve a signing link for a specific document using this  link "https://api.boldsign.com/v1/document/getEmbeddedSignLink?documentId=17882g56-xxxx-xxxx-xxxx-ce5737751234&signerEmail=alexgayle@cubeflakes.com&redirectUrl=https://www.syncfusion.com/&signLinkValidTill=10/14/2022"
    def post(self, request, *args, **kwargs):
        url = f"https://api.boldsign.com/v1/document/getEmbeddedSignLink"
        tenant_email = ""
        if os.getenv("ENVIRONMENT") == "development":
            tenant_email = "tenant@boldsign.dev"
        else:
            tenant_email = request.data.get("tenant_email")
        # Create params object for the url query params
        params = {
            "documentId": request.data.get("document_id"),
            "signerEmail": tenant_email,
            "redirectUrl": request.data.get("redirect_url"),
            "signLinkValidTill": request.data.get("sign_link_valid_till"),
        }

        headers = {"X-API-KEY": BOLDSIGN_API_KEY}
        response = requests.request("GET", url, headers=headers, params=params)


        if response.status_code == 429:
            return JsonResponse(
                {
                    "error": "Too many requests. Please try again later.",
                    "status": 429,
                },
                status=429,
            )
        if response.status_code == 200:
            return JsonResponse(
                {"data": response.json(), "status": response.status_code}, status=200
            )
        else:
            return Response(
                {
                    "error": "Failed to retrieve signing link",
                    "status": 500,
                },
                status=500,
            )


# Create a class that donwloads a doccument using the url  https://api.boldsign.com/v1/document/download and params documentId
class DownloadBoldSignDocumentView(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        document_id = request.data.get('document_id')
        lease_agreement = None

        if user.account_type == "owner":
            owner = Owner.objects.get(user=user)
            lease_agreement = LeaseAgreement.objects.filter(owner=owner, document_id=document_id)
        elif user.account_type == "tenant":
            tenant = Tenant.objects.get(user=user)
            lease_agreement = LeaseAgreement.objects.filter(document_id=document_id)
        else:
            return Response({"error": "Access Denied"}, status=400)

        #Check if the lease agreement exists
        if not lease_agreement.exists():
            return Response({"error": "Lease agreement not found"}, status=404)            
        
        if not document_id:
            return Response({"error": "Document ID is required"}, status=400)

        url = f"https://api.boldsign.com/v1/document/download?documentId={document_id}"
        headers = {"accept": "application/json", "X-API-KEY": f"{BOLDSIGN_API_KEY}"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'application/pdf')
            response = HttpResponse(response.content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{document_id}.pdf"'
            return response
        else:
            return HttpResponse('Failed to download document', status=response.status_code)