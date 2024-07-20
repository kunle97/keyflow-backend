import json
import os
import stripe
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from datetime import timedelta, timezone, datetime, date
from django.utils import timezone as tz
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import action, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from keyflow_backend_app.helpers.helpers import calculate_final_price_in_cents, make_id, create_rent_invoices
from keyflow_backend_app.views.boldsign import CreateDocumentFromTemplateView, CreateSigningLinkView
from keyflow_backend_app.models.account_type import Tenant
from keyflow_backend_app.models.tenant_invite import TenantInvite
from ..models.notification import Notification
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.lease_renewal_request import LeaseRenewalRequest
from ..models.transaction import Transaction
from ..models.rental_application import RentalApplication
from ..models.account_activation_token import AccountActivationToken
from ..models.announcement import Announcement
from ..serializers.user_serializer import UserSerializer
from ..serializers.rental_unit_serializer import RentalUnitSerializer
from ..serializers.lease_agreement_serializer import LeaseAgreementSerializer
from ..serializers.lease_template_serializer import LeaseTemplateSerializer
from ..serializers.transaction_serializer import TransactionSerializer
from ..serializers.annoucement_serializer import AnnouncementSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.test import RequestFactory
from rest_framework.test import force_authenticate
load_dotenv()

class TenantVerificationView(APIView):
    # Create a function that verifies the lease agreement id and approval hash
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        lease_agreement_id = request.data.get("lease_agreement_id")

        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        # check if the approval hash is valid with the lease agreement
        if lease_agreement.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # return a response for the lease being signed successfully
        return Response(
            {"message": "Approval hash valid.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


class TenantInviteVerificationView(APIView):
    # Create a function that verifies the tenant invite and approval hash
    def post(self, request):
        approval_hash = request.data.get("approval_hash")
        tenant_invite_id = request.data.get("tenant_invite_id")

        tenant_invite = TenantInvite.objects.get(id=tenant_invite_id)
        # check if the approval hash is valid with the lease agreement
        if tenant_invite.approval_hash != approval_hash:
            return Response(
                {"message": "Invalid data.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # return a response for the lease being signed successfully
        return Response(
            {"message": "Approval hash valid.", "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )


class OldTenantViewSet(viewsets.ModelViewSet):
    # ... (existing code)
    @action(detail=True, methods=["post"], url_path="make-payment")
    @authentication_classes([TokenAuthentication, SessionAuthentication])
    def make_payment_intent(self, request, pk=None):
        data = request.data.copy()
        user_id = request.data.get("user_id")  # retrieve user id from the request
        tenant = User.objects.get(id=user_id)  # retrieve the user object
        unit = RentalUnit.objects.get(tenant=tenant)  # retrieve the unit object
        owner = unit.owner  # Retrieve owner object from unit object
        lease_template = (
            unit.lease_template
        )  # Retrieve lease term object from unit object
        amount = lease_template.rent  # retrieve the amount from the lease term object

        # Call Stripe API to create a payment
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            payment_method_types=["card"],
            customer=tenant.stripe_customer_id,
            payment_method=data["payment_method_id"],
            transfer_data={
                "destination": owner.stripe_account_id  # The Stripe Connected Account ID
            },
            confirm=True,
        )

        # create a transaction object
        transaction = Transaction.objects.create(
            type="rent_payment",
            description=f"{tenant.first_name} {tenant.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name} for owner {owner.first_name} {owner.last_name}",
            rental_property=unit.rental_property,
            rental_unit=unit,
            owner=owner,
            user=owner.user,
            tenant=tenant,
            amount=amount,
            payment_method_id=data["payment_method_id"],
            payment_intent_id=payment_intent.id,
        )

        # Create a notification for the owner that the tenant has paid the rent
        notification = Notification.objects.create(
            user=owner.user,
            message=f"{tenant.first_name} {tenant.last_name} has paid rent for the amount of ${amount} for unit {unit.name} at {unit.rental_property.name}",
            type="rent_paid",
            title="Rent Paid",
            resource_url=f"/dashboard/owner/transactions/{transaction.id}",
        )

        # serialize transaction object and return it
        serializer = TransactionSerializer(transaction)
        transaction_data = serializer.data

        return Response(
            {
                "payment_intent": payment_intent,
                "transaction": transaction_data,
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )


class RetrieveTenantDashboardData(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        current_date = tz.now().date()
        auto_renew_response = None
        try:
            user = User.objects.get(id=user_id)
            tenant = Tenant.objects.get(user=user)
        except (User.DoesNotExist, Tenant.DoesNotExist):
            return Response({"error": "User or tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        lease_agreements = LeaseAgreement.objects.filter(tenant=tenant)
        # recently_ended_lease_agreement = lease_agreements.order_by("-end_date").first()#uncomment to test the auto_renew_lease function
        # auto_renew_response = self.auto_renew_lease(tenant, recently_ended_lease_agreement) #uncomment to test the auto_renew_lease function

        active_leases = []
        leases_to_deactivate = []
        
        #Automatically deactivate lease agreements that have ended and activate lease agreements that should be active
        for lease_agreement in lease_agreements:
            #Check if the lease agreement has ended/expired
            if current_date > lease_agreement.end_date:
                leases_to_deactivate.append(lease_agreement)
            #Check if the lease agreement should be active
            elif lease_agreement.start_date <= current_date <= lease_agreement.end_date:
                lease_agreement.is_active = True
                lease_agreement.save()
                active_leases.append(lease_agreement)
        
        LeaseAgreement.objects.filter(id__in=[lease.id for lease in leases_to_deactivate]).update(is_active=False)
        # LeaseAgreement.objects.filter(id__in=[lease.id for lease in leases_to_deactivate]).delete()
        if len(active_leases) == 0 and tenant.auto_renew_lease_is_enabled == False:# If there are no active leases, return an empty response
            return Response({"next_payment_date": None, "payment_dates": [], "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
        elif len(active_leases) == 0 and tenant.auto_renew_lease_is_enabled == True:# If there are no active leases but auto renew is enabled, renew the lease
        #    recently_ended_lease_agreement = lease_agreements.order_by("-end_date").first()#retrieve the most recently ended lease agreement
        #    auto_renew_response = self.auto_renew_lease(tenant, recently_ended_lease_agreement) #Real implementation of auto renew lease

            pass
        lease_agreement = active_leases[0]

        unit = lease_agreement.rental_unit

        lease_terms = json.loads(unit.lease_terms)

        payment_dates = self.calculate_payment_dates(lease_agreement, unit, lease_terms)
        late_fees = self.calculate_late_fees(lease_agreement, payment_dates, lease_terms)
        total_balance = self.calculate_total_balance(lease_agreement, unit, lease_terms)
        current_balance = self.calculate_current_balance(lease_agreement, unit, lease_terms)

        unit_data = RentalUnitSerializer(unit).data
        lease_template_data = LeaseTemplateSerializer(lease_agreement.lease_template).data
        lease_agreement_data = LeaseAgreementSerializer(lease_agreement).data

        related_announcements = self.get_related_announcements(unit)

        return Response({
            "unit": unit_data,
            "lease_template": lease_template_data,
            "lease_agreement": lease_agreement_data,
            "auto_renew_response": auto_renew_response,
            "auto_renew_lease_is_enabled": tenant.auto_renew_lease_is_enabled,
            "payment_dates": payment_dates,
            "late_fees": late_fees,
            "total_balance": total_balance,
            "current_balance": current_balance,
            "announcements": related_announcements,
            "status": status.HTTP_200_OK,
        }, status=status.HTTP_200_OK)

    def auto_renew_lease(self, tenant, recently_ended_lease_agreement):
        #Create a lease renewal request
        owner = recently_ended_lease_agreement.owner
        rental_unit = recently_ended_lease_agreement.rental_unit
        rental_property = rental_unit.rental_property
        rental_unit_preferences = json.loads(rental_unit.lease_terms)
        rent_frequency = next(
            (item for item in rental_unit_preferences if item["name"] == "rent_frequency"),
        )
        lease_term = next(
            (item for item in rental_unit_preferences if item["name"] == "term"),
        )
        #Create a move in date that is one day after the end of the lease
        move_in_date = recently_ended_lease_agreement.end_date + timedelta(days=1)
        
        lease_renewal_request = LeaseRenewalRequest.objects.create(
            tenant=tenant,
            owner=owner,
            rental_unit=rental_unit,
            rental_property=rental_property,
            request_date=datetime.now(),
            move_in_date=move_in_date,
            request_term=lease_term["value"],
            rent_frequency=rent_frequency["value"],
            comments="Auto-renewed lease",
            status="approved"
        )
        data = {
            "owner_id": owner.id,
            "template_id": rental_unit.template_id,
            "tenant_first_name": tenant.user.first_name,
            "tenant_last_name": tenant.user.last_name,
            "tenant_email": tenant.user.email,
            "document_title": f"{tenant.user.first_name} {tenant.user.last_name} Lease Agreement (Renewal) for unit {rental_unit.name} at {rental_property.name}",
            "message": "Please sign the document to offically renew your lease agreement",
        }

        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/boldsign/create-document-from-template/', data, content_type='application/json')
        force_authenticate(request, user=tenant.user)
        
        # Call the `post` method of the view
        view = CreateDocumentFromTemplateView.as_view()
        response = view(request)
        response_content = response.content  # This gives you the response content in bytes
        response_str = response_content.decode('utf-8')  # Decode the bytes to a string
        response_json = json.loads(response_str)  # Parse the JSON string
        document_id = response_json.get('documentId')  # Access the documentId
        end_date = None
        #Calculate the end date using the rent frequency and term   
        if rent_frequency["value"] == "month":
            end_date = move_in_date + relativedelta(months=int(lease_term["value"]))
        elif rent_frequency["value"] == "year":
            end_date = move_in_date + relativedelta(years=int(lease_term["value"]))
        elif rent_frequency["value"] == "week":
            end_date = move_in_date + relativedelta(weeks=int(lease_term["value"]))
        elif rent_frequency["value"] == "day":
            end_date = move_in_date + relativedelta(days=int(lease_term["value"]))

        #Create a lease agreement from the lease renewal request and document id
        lease_agreement = LeaseAgreement.objects.create(
            tenant=tenant,
            owner=owner,
            rental_unit=rental_unit,
            start_date=move_in_date,
            end_date=end_date,
            lease_template=rental_unit.lease_template,
            document_id=document_id,
            approval_hash=make_id(64),
            is_active=False,
            lease_renewal_request=lease_renewal_request
        )
        tenant_email = tenant.user.email
        if os.getenv("ENVIRONMENT") == "development":
            tenant_email = "tenant@boldsign.dev"
        #Call the CreateSigningLinkView's post method to create a signing link for the lease agreement
        data = {
            "document_id": document_id,
            "tenant_email": tenant_email,
            "redirect_url": f"/dashboard/tenant/",
        }            

          # Create a mock request
        factory = RequestFactory()
        create_signing_link_request = factory.post('/boldsign/create-signing-link/', data, content_type='application/json')
        force_authenticate(create_signing_link_request, user=tenant.user)
        
        # Call the `post` method of the view
        create_signing_link_view = CreateSigningLinkView.as_view()
        create_signing_link_response = create_signing_link_view(create_signing_link_request)
        create_signing_link_response_content = create_signing_link_response.content  # This gives you the response content in bytes
        create_signing_link_response_str = create_signing_link_response_content.decode('utf-8')  # Decode the bytes to a string
        create_signing_link_response_json = json.loads(create_signing_link_response_str)  # Parse the JSON string
        boldsign_sign_link = None
        #Check if data is in create_signing_link_response_json 
        if "data" in create_signing_link_response_json:
            boldsign_sign_link = create_signing_link_response_json["data"]["signLink"]
            # TODO: Add notification for tenant that lease has been auto-renewed and is ready to be signed. Message  should contain keyflow sign link

        return {
                "boldsign_sign_link": boldsign_sign_link,
                "keyflow_sign_link": f"/sign-lease-agreement/{lease_agreement.id}/{lease_agreement.approval_hash}",
                "document_id": document_id,
                "lease_agreement_id": lease_agreement.id,
                "approval_hash": lease_agreement.approval_hash,
            }
        
    def get_related_announcements(self, unit):
        if unit is None:
            return []

        related_announcements = []
        owner = unit.owner
        announcements = Announcement.objects.filter(
            owner=owner,
            start_date__lte=datetime.now(timezone.utc),
            end_date__gte=datetime.now(timezone.utc),
        )
        
        for announcement in announcements:
            target = json.loads(announcement.target)
            if ("rental_unit" in target and target["rental_unit"] == unit.id) or \
            ("rental_property" in target and target["rental_property"] == getattr(unit.rental_property, 'id', None)) or \
            ("portfolio" in target and target["portfolio"] == getattr(getattr(unit.rental_property, 'portfolio', None), 'id', None)):
                related_announcements.append(announcement)

        return AnnouncementSerializer(related_announcements, many=True).data



    def reset_lease_and_unit(self, lease_agreement):
        lease_agreement.is_active = False
        lease_agreement.tenant = None
        lease_agreement.save()

        rental_unit = lease_agreement.rental_unit
        rental_unit.is_occupied = False
        rental_unit.save()
        
    def calculate_late_fees(self, lease_agreement, payment_dates, lease_terms):
        transactions = Transaction.objects.filter(
            tenant=lease_agreement.tenant, type="rent_payment"
        )
        late_fee_amount = next(
            (item for item in lease_terms if item["name"] == "late_fee"),
            None,
        )
        # Get today's date for comparison
        today_date = date.today()

        # Check for missed payments not found in payment_dates
        for transaction in transactions:
            payment_date = transaction.timestamp.date()
            is_payment_found = any(
                payment["payment_date"] == payment_date for payment in payment_dates
            )
            is_payment_overdue = payment_date < today_date

            if not is_payment_found or is_payment_overdue:
                payment_dates.append(
                    {
                        "title": "Rent Due",
                        "payment_date": payment_date,
                        "transaction_paid": False,
                        "is_late": True,
                    }
                )

        # Recalculate overdue payments with updated payment_dates
        overdue_payments = sum(1 for payment in payment_dates if payment["is_late"])
        # Calculate late fee by multiplying late fee amount with the number of overdue payments
        late_fees = float(late_fee_amount["value"]) * int(overdue_payments)
        return float(late_fees)

    def calculate_payment_dates(self, lease_agreement, unit, lease_terms):
        lease_start_date = lease_agreement.start_date
        lease_end_date = lease_agreement.end_date
        payment_dates = []

        while lease_start_date <= lease_end_date:
            transaction_date = lease_start_date

            # Check if a transaction exists for the current lease_start_date
            transaction_exists = Transaction.objects.filter(
                rental_unit=unit,
                timestamp__date=transaction_date,
            ).exists()

            # Calculate due date for the current payment
            due_date = lease_start_date  # This can be adjusted based on your specific due date logic

            # Determine if payment is late
            is_late = transaction_exists and transaction_date > due_date

            event_title = "Rent Due" if not transaction_exists else "Rent Paid"

            payment_dates.append(
                {
                    "title": event_title,
                    "payment_date": transaction_date,
                    "transaction_paid": transaction_exists,
                    "is_late": is_late,
                }
            )

            rent_frequency = next(
                (item for item in lease_terms if item["name"] == "rent_frequency"),
                None,
            )
            # Get the value property from the rent_frequency object
            rent_frequency_value = rent_frequency["value"]
            # Move to the next payment date based on lease frequency
            if rent_frequency_value == "month":
                lease_start_date += relativedelta(months=1)
            elif rent_frequency_value == "year":
                lease_start_date += relativedelta(years=1)
            elif rent_frequency_value == "week":
                lease_start_date += relativedelta(weeks=1)
            elif rent_frequency_value == "day":
                lease_start_date += relativedelta(days=1)
            else:
                # Handle other frequencies here
                # Set lease_start_date to lease_end_date to break the loop for non-supported frequencies
                lease_start_date = lease_end_date

        return payment_dates

    def calculate_current_balance(self, lease_agreement, unit, lease_terms):
        rent_pref = next(
            (item for item in lease_terms if item["name"] == "rent"),
            None,
        )
        rent = rent_pref["value"]
        term_pref = next(
            (item for item in lease_terms if item["name"] == "rent"),
            None,
        )
        term = term_pref["value"]
        frequency_pref = next(
            (item for item in lease_terms if item["name"] == "rent_frequency"),
            None,
        )
        frequency = frequency_pref["value"]

        additional_charges_dict = json.loads(unit.additional_charges)


        # Get today's date for comparison
        today_date = date.today()

        # Initialize variables to track total amount due up to the current date
        total_due = 0.0

        # Calculate the total amount due up to the current date
        current_date = lease_agreement.start_date
        while current_date <= today_date:
            total_due += float(rent)
            for charge in additional_charges_dict:
                if charge["frequency"] == frequency:
                    total_due += float(charge["amount"])

            if frequency == "month":
                current_date += relativedelta(months=1)
            elif frequency == "year":
                current_date += relativedelta(years=1)
            elif frequency == "week":
                current_date += relativedelta(weeks=1)
            elif frequency == "day":
                current_date += relativedelta(days=1)
            else:
                # Handle other frequencies as needed
                break

        # Get all rent payment transactions made by the tenant
        transactions = Transaction.objects.filter(
            tenant=lease_agreement.tenant,
            type="rent_payment",
            timestamp__lte=today_date,
        )

        # Calculate the total amount paid up to the current date
        total_paid = sum(transaction.amount for transaction in transactions)

        # Calculate the total amount due up to the current date
        total_due -= total_paid
        return total_due

    def calculate_total_balance(self, lease_agreement, unit, lease_terms):
        rent_pref = next(
            (item for item in lease_terms if item["name"] == "rent"),
            None,
        )
        rent = rent_pref["value"]
        term_pref = next(
            (item for item in lease_terms if item["name"] == "term"),
            None,
        )
        term = term_pref["value"]
        frequency_pref = next(
            (item for item in lease_terms if item["name"] == "rent_frequency"),
            None,
        )
        frequency = frequency_pref["value"]

        additional_charges_dict = json.loads(unit.additional_charges)

        # Get today's date for comparison
        today_date = date.today()

        # Calculate the total rent due for the entire lease term
        total_rent_due = 0.0
        for i in range(int(term)):
            total_rent_due += float(rent)
            for charge in additional_charges_dict:
                if charge["frequency"] == frequency:
                    total_rent_due += float(charge["amount"])

        # Get all rent payment transactions made by the tenant
        transactions = Transaction.objects.filter(
            tenant=lease_agreement.tenant,
            type="rent_payment",
            timestamp__lte=today_date,
        )

        # Calculate the total amount paid
        total_paid = sum(transaction.amount for transaction in transactions)

        # Calculate the current balance
        current_balance = total_rent_due - total_paid
        return current_balance

class CreateRentInvoicesForTenantRenewal(APIView):
    def post(self, request):
        tenant_id = request.data.get("tenant_id")
        tenant = Tenant.objects.get(id=tenant_id)
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
        if Tenant.objects.get(user=request.user).id != tenant_id:
            return Response(
                {
                    "message": "You do not have permission to perform this action.",
                    "status": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        lease_agreement_id = request.data.get("lease_agreement_id")
        lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
        unit = RentalUnit.objects.get(tenant=tenant)
        lease_terms = json.loads(unit.lease_terms)
        lease_start_date = lease_agreement.start_date

        rent_amount = float(next(
            item for item in lease_terms if item["name"] == "rent"
        )["value"])
        rent_frequency = next(
            item for item in lease_terms if item["name"] == "rent_frequency"
        )["value"]
        lease_term = int(next(
            item for item in lease_terms if item["name"] == "term"
        )["value"])
        security_deposit = float(next(
            item for item in lease_terms if item["name"] == "security_deposit"
        )["value"])

        customer_id = tenant.stripe_customer_id
        additional_charges_dict = json.loads(unit.additional_charges)

        # Convert lease_start_date to a datetime object
        lease_start_date_time = datetime.combine(lease_start_date, datetime.min.time())

        # Create due date that is the day of the first day of the first month of the lease agreement duration
        due_date_timestamp = int(datetime.timestamp(lease_start_date_time.replace(day=1)))

        #Create a stripe invoice for the security deposit
        if security_deposit > 0:
            security_deposit_invoice = stripe.Invoice.create(
                customer=customer.id,
                auto_advance=True,
                collection_method="send_invoice",
                due_date=due_date_timestamp,
                metadata={
                    "type": "security_deposit",
                    "description": "Security Deposit Payment",
                    "tenant_id": tenant.id,
                    "owner_id": unit.rental_property.owner.id,
                    "rental_property_id": unit.rental_property.id,
                    "rental_unit_id": unit.id,
                },
                transfer_data={"destination": unit.owner.stripe_account_id},
            )
            # Create stripe price for security deposit
            price = stripe.Price.create(
                unit_amount=int(security_deposit * 100),
                currency="usd",
                product_data={
                    "name": str(
                        f"Security Deposit for unit {unit.name} at {unit.rental_property.name}"
                    )
                },
            )
            stripe.InvoiceItem.create(
                customer=customer.id,
                price=price.id,
                currency="usd",
                description=f"{tenant.user.first_name} {tenant.user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                invoice=security_deposit_invoice.id,
            )    
            #Add Invoice item for stripe fee
            stripe_fee_in_cents = calculate_final_price_in_cents(security_deposit)["stripe_fee_in_cents"]
            stripe_fee_product = stripe.Product.create(
                name=f"Payment processing fee",
                type="service",
            )
            stripe_fee_price = stripe.Price.create(
                unit_amount=int(stripe_fee_in_cents),
                currency="usd",
                product=stripe_fee_product.id,
            )
            stripe.InvoiceItem.create(
                customer=customer.id,
                price=stripe_fee_price.id,
                currency="usd",
                description=f"Payment processing fee",
                invoice=security_deposit_invoice.id,
            )
            # Finalize the invoice
            stripe.Invoice.finalize_invoice(security_deposit_invoice.id)

        create_rent_invoices(
            lease_start_date,
            rent_amount,
            rent_frequency,
            lease_term,
            customer_id,
            unit,
            additional_charges_dict,
            lease_agreement
        )

        return Response(
            {
                "message": "Rent invoices created successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

# Create an endpoint that registers a tenant (DEPRIECATED)
class TenantRegistrationView(APIView):
    def post(self, request):
        data = request.data.copy()

        # Hash the password before saving the user
        data["password"] = make_password(data["password"])

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            tenant_user = User.objects.get(email=data["email"])

            # Initialize unit here to get the larndlord object
            unit_id = data["unit_id"]
            unit = RentalUnit.objects.get(id=unit_id)

            # retrieve owner from the unit
            owner = unit.owner

            # set the account type to tenant
            tenant_user.account_type = "tenant"
            # Create a stripe customer id for the user
            stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
            customer = stripe.Customer.create(
                email=tenant_user.email,
                metadata={
                    "owner_id": owner.id,
                },
            )

            tenant_user.is_active = False
            tenant_user.save()

            tenant = Tenant.objects.create(
                user=tenant_user,
                stripe_customer_id=customer.id,
                owner=owner,
            )
            try:
                owner_preferences = json.loads(owner.preferences)
                # Retrieve the object in the array who's "name" key value is "tenant_registered"
                notification_preferences = next(
                    item for item in owner_preferences if item["name"] == "new_tenant_registration_complete"
                )
                # Retrieve the "values" key value of the object
                notification_preferences_values = notification_preferences["values"]
                for value in notification_preferences_values:
                    if value["name"] == "push" and value["value"] == True:

                        # Create a notification for the owner that a tenant has been added
                        notification = Notification.objects.create(
                            user=owner.user,
                            message=f"{tenant_user.first_name} {tenant_user.last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}",
                            type="tenant_registered",
                            title="Tenant Registered",
                            resource_url=f"/dashboard/owner/tenants/{tenant_user.id}",
                        )
                    elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                        #Create an email notification for the owner that a new tenant has been added
                        client_hostname = os.getenv("CLIENT_HOSTNAME")
                        postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                        to_email = ""
                        if os.getenv("ENVIRONMENT") == "development":
                            to_email = "keyflowsoftware@gmail.com"
                        else:
                            to_email = owner.user.email
                        # Send email to owner
                        postmark.emails.send(
                            From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                            To=to_email,
                            Subject="New Tenant Added",
                            HtmlBody=f"{tenant_user.first_name} {tenant_user.last_name} has been added as a tenant to unit {unit.name} at {unit.rental_property.name}. <a href='{client_hostname}/dashboard/owner/tenants/{tenant_user.id}'>View Tenant</a>",
                        )
            except StopIteration:
                # Handle case where "new_tenant_registration_complete" is not found

                pass
            except KeyError:
                # Handle case where "values" key is missing in "new_tenant_registration_complete"

                pass
            # Retrieve unit from the request unit_id parameter

            unit.tenant = tenant
            unit.save()

            # Retrieve lease agreement from the request lease_agreement_id parameter
            lease_agreement_id = data["lease_agreement_id"]
            lease_agreement = LeaseAgreement.objects.get(id=lease_agreement_id)
            lease_agreement.tenant = tenant
            lease_agreement.save()

            # Retrieve rental application from the request approval_hash parameter
            approval_hash = data["approval_hash"]
            rental_application = RentalApplication.objects.get(
                approval_hash=approval_hash
            )
            rental_application.tenant = tenant
            rental_application.save()

            # Retrieve price id from lease term using lease_agreement
            lease_template = unit.lease_template

            # Attach payment method to the customer adn make it default
            payment_method_id = data["payment_method_id"]
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            owner = unit.owner
            owner_user = owner.user
            # TODO: implement secutrity deposit flow here. Ensure subsicption is sety to a trial period of 30 days and then charge the security deposit immeediatly
            if lease_template.security_deposit > 0:
                # Retrieve owner from the unit
                security_deposit_payment_intent = stripe.PaymentIntent.create(
                    amount=int(lease_template.security_deposit * 100),
                    currency="usd",
                    payment_method_types=["card"],
                    customer=customer.id,
                    payment_method=data["payment_method_id"],
                    transfer_data={
                        "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                    },
                    confirm=True,
                    # Add Metadata to the transaction signifying that it is a security deposit
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": owner_user.id,
                        "tenant_id": tenant.id,
                        "owner_id": owner.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )

                # create a transaction object for the security deposit
                security_deposit_transaction = Transaction.objects.create(
                    type="security_deposit",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    owner=owner,
                    user=owner_user,
                    tenant=tenant,
                    amount=int(lease_template.security_deposit),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id=security_deposit_payment_intent.id,
                )
                try:
                    owner_preferences = json.loads(owner.preferences)
                    # Retrieve the object in the array who's "name" key value is "security_deposit_paid"
                    security_deposit_preferences = next(
                        item for item in owner_preferences if item["name"] == "security_deposit_paid"
                    )
                    # Retrieve the "values" key value of the object
                    security_deposit_preferences_values = security_deposit_preferences["values"]
                    for value in security_deposit_preferences_values:
                        if value["name"] == "push" and value["value"] == True:
                            # Create a notification for the owner that the security deposit has been paid
                            notification = Notification.objects.create(
                                user=owner_user,
                                message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the security deposit for the amount of ${lease_template.security_deposit} for unit {unit.name} at {unit.rental_property.name}",
                                type="security_deposit_paid",
                                title="Security Deposit Paid",
                                resource_url=f"/dashboard/owner/transactions/{security_deposit_transaction.id}",
                            )
                        elif value["name"] == "email" and value["value"] == True and os.getenv("ENVIRONMENT") == "production":
                            #Create an email notification for the owner that the security deposit has been paid
                            client_hostname = os.getenv("CLIENT_HOSTNAME")
                            postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                            to_email = ""
                            if os.getenv("ENVIRONMENT") == "development":
                                to_email = "keyflowsoftware@gmail.com"
                            else:
                                to_email = owner_user.email
                            # Send email to owner
                            postmark.emails.send(
                                From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                                To=to_email,
                                Subject="Security Deposit Paid",
                                HtmlBody=f"{tenant_user.first_name} {tenant_user.last_name} has paid the security deposit for the amount of ${lease_template.security_deposit} for unit {unit.name} at {unit.rental_property.name}. <a href='{client_hostname}/dashboard/owner/transactions/{security_deposit_transaction.id}'>View Transaction</a>",
                            )
                except StopIteration:
                    # Handle case where "security_deposit_paid" is not found

                    pass
                except KeyError:
                    # Handle case where "values" key is missing in "security_deposit_paid"

                    pass
            subscription = None
            if lease_template.grace_period != 0:
                # Convert the ISO date string to a datetime object
                start_date = datetime.fromisoformat(f"{lease_agreement.start_date}")

                # Number of months to add
                months_to_add = lease_template.grace_period

                # Calculate the end date by adding months
                end_date = start_date + relativedelta(months=months_to_add)

                # Convert the end date to a Unix timestamp
                grace_period_end = int(end_date.timestamp())
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[
                        {"price": lease_template.stripe_price_id},
                    ],
                    default_payment_method=payment_method_id,
                    trial_end=grace_period_end,
                    transfer_data={
                        "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                    },
                    # Cancel the subscription after at the end date specified by lease term
                    cancel_at=int(
                        datetime.fromisoformat(
                            f"{lease_agreement.end_date}"
                        ).timestamp()
                    ),
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant_user.id,
                        "owner_id": owner.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )
            else:
                grace_period_end = lease_agreement.start_date
                # Create a stripe subscription for the user and make a default payment method
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[
                        {"price": lease_template.stripe_price_id},
                    ],
                    transfer_data={
                        "destination": owner.stripe_account_id  # The Stripe Connected Account ID
                    },
                    cancel_at=int(
                        datetime.fromisoformat(
                            f"{lease_agreement.end_date}"
                        ).timestamp()
                    ),
                    default_payment_method=payment_method_id,
                    metadata={
                        "type": "revenue",
                        "description": f"{tenant_user.first_name} {tenant_user.last_name} Security Deposit Payment for unit {unit.name} at {unit.rental_property.name}",
                        "user_id": tenant_user.id,
                        "tenant_id": tenant.id,
                        "owner_id": owner.id,
                        "rental_property_id": unit.rental_property.id,
                        "rental_unit_id": unit.id,
                        "payment_method_id": data["payment_method_id"],
                    },
                )

                # create a transaction object for the rent payment (stripe subscription)
                subscription_transaction = Transaction.objects.create(
                    type="rent_payment",
                    description=f"{tenant_user.first_name} {tenant_user.last_name} Rent Payment for unit {unit.name} at {unit.rental_property.name}",
                    rental_property=unit.rental_property,
                    rental_unit=unit,
                    owner=owner,
                    user=owner.user,
                    tenant=tenant,
                    amount=int(lease_template.rent),
                    payment_method_id=data["payment_method_id"],
                    payment_intent_id="subscription",
                )
                # Create a notification for the owner that the tenant has paid the fisrt month's rent
                notification = Notification.objects.create(
                    user=owner,
                    message=f"{tenant_user.first_name} {tenant_user.last_name} has paid the first month's rent for the amount of ${lease_template.rent} for unit {unit.name} at {unit.rental_property.name}",
                    type="first_month_rent_paid",
                    title="First Month's Rent Paid",
                    resource_url=f"/dashboard/owner/transactions/{subscription_transaction.id}",
                )
                #Create an email notification for the owner that the first month's rent has been paid
                client_hostname = os.getenv("CLIENT_HOSTNAME")
                postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_TOKEN"))
                to_email = ""
                if os.getenv("ENVIRONMENT") == "development":
                    to_email = "keyflowsoftware@gmail.com"
                else:
                    to_email = owner.email
                # Send email to owner
                postmark.emails.send(
                    From=os.getenv("KEYFLOW_SENDER_EMAIL"),
                    To=to_email,
                    Subject="First Month's Rent Paid",
                    HtmlBody=f"{tenant_user.first_name} {tenant_user.last_name} has paid the first month's rent for the amount of ${lease_template.rent} for unit {unit.name} at {unit.rental_property.name}. <a href='{client_hostname}/dashboard/owner/transactions/{subscription_transaction.id}'>View Transaction</a>",
                )
            # add subscription id to the lease agreement
            lease_agreement.stripe_subscription_id = subscription.id
            lease_agreement.save()
            account_activation_token = AccountActivationToken.objects.create(
                user=tenant_user,
                email=tenant_user.email,
                token=data["activation_token"],
            )
            return Response(
                {
                    "message": "Tenant registered successfully.",
                    "user": serializer.data,
                    "isAuthenticated": True,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
