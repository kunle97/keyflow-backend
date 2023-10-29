# views.py
import os
from django.http import JsonResponse
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
import requests
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

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

        payload = {
            "Title": request.data.get("template_title"),
            "Description": request.data.get("template_description"),
            "DocumentTitle": request.data.get("document_title"),
            "DocumentMessage": request.data.get("document_description"),
            "AllowMessageEditing": "true",
            "Roles[0][name]": "Tenant",
            "Roles[0][index]": "1",
            "Roles[1][name]": "Landlord",
            "Roles[1][index]": "2",
            "Roles[1][defaultSignerName]": request.data.get("landlord_name"),
            "Roles[1][defaultSignerEmail]": request.data.get("landlord_email"),
            "ShowToolbar": "true",
            "ShowSaveButton": "true",
            "ShowSendButton": "false",
            "ShowPreviewButton": "true",
            "ShowNavigationButtons": "true",
            "ShowTooltip": "true",
            "ViewOption": "PreparePage",
        }
        # try:
        print("zx THe filee ", request.FILES)
        uploaded_file = request.FILES["file"]
        print(f"The FILee {uploaded_file}")
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
        # except Exception as e:
        #     print(f"File upload error: {e}")
        #     print(f'files: {request.FILES}')
        #     return JsonResponse({"error": "Failed to upload the file"})


class CreateEmbededDocumentSendLink(APIView):
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
            "ShowTooltip": "false",
        }
        headers = {
            "Accept": "application/json",
            "X-API-KEY": BOLDSIGN_API_KEY,
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            print(response.text)
            return JsonResponse(
                {"message": "Document created", "url": response.json()["editUrl"]}
            )
        else:
            return JsonResponse(
                {
                    "error": "Failed to create document",
                    "status_code": response.status_code,
                }
            )


@csrf_exempt
def create_embeded_template_editor_link(
    request,
):  # This will be called when a user is in the edit lease agreement page and selects edit lease agreement file or somthing
    url = (
        "https://api.boldsign.com/v1/template/getEmbeddedTemplateEditUrl?templateId="
        + request.POST.get("template_id")
    )
    payload = {
        "ShowToolbar": "false",
        "ViewOption": "PreparePage",
        "ShowSaveButton": "true",
        "ShowCreateButton": "true",
        "ShowPreviewButton": "true",
        "ShowNavigationButtons": "true",
        "ShowTooltip": "false",
    }
    headers = {"Accept": "application/json", "X-API-KEY": BOLDSIGN_API_KEY}

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)


def create_document(request):
    # Implement logic to create a document using BoldSign API
    # Use requests library to make a POST request to the BoldSign API
    # Return the response as JSON
    return JsonResponse({"message": "Document created"})


def create_embedded_signing_link(request):
    url = f"{BOLDSIGN_API_BASE_URL}/signing_links/embedded"

    headers = {
        "Authorization": f"Bearer {BOLDSIGN_API_KEY}",
        "Content-Type": "multipart/form-data",
    }

    data = {"document_id": "document_id_here", "expires_in_hours": 24}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        signing_link = response.json()["url"]
        return JsonResponse(
            {
                "message": "Embedded signing link created successfully",
                "signing_link": signing_link,
            }
        )
    else:
        return JsonResponse(
            {
                "error": "Failed to create embedded signing link",
                "status_code": response.status_code,
            }
        )


def create_embedded_template_editor_link(request):
    url = f"{BOLDSIGN_API_BASE_URL}/v1/template/createEmbeddedTemplateUrl"

    headers = {
        "X-API-KEY": f"{BOLDSIGN_API_KEY}",
        "Content-Type": "multipart/form-data",
    }

    data = {
        "template_id": request.POST.get("template_id"),
        "RedirectUrl": "https://boldsign.com/esignature-api/",
        "ShowToolbar": "true",
        "ViewOption": "PreparePage",
        "ShowSaveButton": "true",
        "ShowSendButton": "true",
        "ShowPreviewButton": "true",
        "ShowNavigationButtons": "true",
        "Title": "Service-level agreement",
        "Description": "A service-level agreement is a commitment between a service provider and a client. Particular aspects of the service – quality, availability, responsibilities – are agreed between the service provider and the service user.",
        "DocumentMessage": "Service level agreement metrics are a way of measuring whether your business or service provider is meeting the standards you have set for yourself.",
        # Roles[0][Name]:HR
        # Roles[0][Index]:1
        # Roles[0][DefaultSignerName]:Alex Gayle
        # Roles[0][DefaultSignerEmail]:alexgayle@cubeflakes.com
        # Roles[0][SignerOrder]:1
        # Roles[0][SignerType]:Signer
        # Roles[0][Locale]:EN
        # Roles[0][ImposeAuthentication]:EmailOTP
        # CC[0][EmailAddress]:stacywilson@cubeflakes.com
        "AllowNewRoles": "true",
        "AllowMessageEditing": "true",
        "EnableSigningOrder": "true",
        # DocumentInfo[0][Title]:Welcome
        # DocumentInfo[0][Locale]:EN
        # DocumentInfo[0][Description]:German language, German Deutsch, official language of both Germany and Austria and one of the official languages of Switzerland
        # BrandId:eb27a99a-9c09-477a-9903-b46df35a7f49
        "EnableReassign": "true",
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        editor_link = response.json()["url"]
        return JsonResponse(
            {
                "message": "Embedded template editor link created successfully",
                "editor_link": editor_link,
            }
        )
    else:
        return JsonResponse(
            {
                "error": "Failed to create embedded template editor link",
                "status_code": response.status_code,
            }
        )
