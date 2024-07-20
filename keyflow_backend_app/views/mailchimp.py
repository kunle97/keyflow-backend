import os
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
from django.http import JsonResponse
from dotenv import load_dotenv
from rest_framework.views import APIView
load_dotenv()


class RequestDemoSubscribeView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")

        if email:
            try:
                # Initialize Mailchimp client
                client = MailchimpMarketing.Client()
                client.set_config(
                    {
                        "api_key": os.getenv("MAILCHIMP_API_KEY"),
                        "server": os.getenv("MAILCHIMP_SERVER_PREFIX"),
                    }
                )

                # Add subscriber to the audience
                audience_id = os.getenv("MAILCHIMP_REQUEST_DEMO_AUDIENCE_ID")
                subscriber = {"email_address": email, "status": "subscribed"}

                response = client.lists.add_list_member(audience_id, subscriber)

                if response.get("status") == "subscribed":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Subscribed successfully!",
                            "status": 200,
                        },
                        status=200,
                    )
                else:
                    return JsonResponse(
                        {"success": False, "message": "Failed to subscribe."},
                        status=400,
                    )
            except ApiClientError as e:
                return JsonResponse({"success": False, "message": str(e)}, status=500)
        return JsonResponse(
            {"success": False, "message": "Invalid request"}, status=400
        )
