import os
from dotenv import load_dotenv
from datetime import timedelta, datetime
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models.user import User
from ..models.rental_unit import RentalUnit
from ..models.lease_agreement import LeaseAgreement
from ..models.transaction import Transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta
import stripe

load_dotenv()


class RetrieveLandlordSubscriptionPriceView(APIView):
    def post(self, request):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        standard_plan_product = stripe.Product.retrieve(
            os.getenv("STRIPE_STANDARD_PLAN_PRODUCT_ID")
        )
        standard_plan_price = stripe.Price.retrieve(standard_plan_product.default_price)
        pro_plan_product = stripe.Product.retrieve(
            os.getenv("STRIPE_PRO_PLAN_PRODUCT_ID")
        )
        pro_plan_price = stripe.Price.retrieve(pro_plan_product.default_price)
        serialized_products = [
            {
                "product_id": standard_plan_product.id,
                "name": standard_plan_product.name,
                "price": standard_plan_price.unit_amount / 100,  # Convert to dollars
                "price_id": standard_plan_price.id,
                "features": standard_plan_product.features,
                "billing_scheme": standard_plan_price.recurring,
            },
            {
                "product_id": pro_plan_product.id,
                "name": pro_plan_product.name,
                "price": pro_plan_price.unit_amount / 100,  # Convert to dollars
                "price_id": pro_plan_price.id,
                "features": pro_plan_product.features,
                "billing_scheme": pro_plan_price.recurring,
            },
        ]
        return Response({"products": serialized_products}, status=status.HTTP_200_OK)


# Create a class that handles manageing a tenants stripe subscription (rent) called ManageTenantSusbcriptionView
class ManageTenantSubscriptionView(viewsets.ModelViewSet):
    # TODO: Investigate why authentication CLasses not working
    # queryset = User.objects.all()
    # serializer_class = UserSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [DisallowUserCreatePermission]

    # Create a method to cancel a subscription called turn_off_autopay
    @action(detail=False, methods=["post"], url_path="turn-off-autopay")
    def turn_off_autopay(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        # Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        # Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        # Retrieve the subscription id from the lease agreement object
        subscription_id = lease_agreement.stripe_subscription_id
        print(f"Subscription id: {subscription_id}")
        stripe.Subscription.modify(
            subscription_id,
            pause_collection={"behavior": "void"},
        )
        lease_agreement.auto_pay_is_enabled = False
        lease_agreement.save()
        # Return a response
        return Response(
            {
                "message": "Subscription paused successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    # Create a method to create a subscription called turn_on_autopay
    @action(detail=False, methods=["post"], url_path="turn-on-autopay")
    def turn_on_autopay(self, request, pk=None):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        # Retrieve the unit object from the user object
        unit = RentalUnit.objects.get(tenant=user)
        # Retrieve the lease agreement object from the unit object
        lease_agreement = LeaseAgreement.objects.get(rental_unit=unit)
        subscription_id = lease_agreement.stripe_subscription_id

        stripe.Subscription.modify(
            subscription_id,
            pause_collection="",
        )
        lease_agreement.auto_pay_is_enabled = True
        lease_agreement.save()
        # Return a response
        return Response(
            {
                "message": "Subscription resumed successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    # Create a get function to retrieve the next payment date for rent for a specific user
    @action(detail=False, methods=["post"], url_path="next-payment-date")
    def next_payment_date(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        lease_agreement = LeaseAgreement.objects.filter(tenant=user, is_active=True).first()
        # Retrieve the lease agreement object from the unit object

        # Input lease start date (replace with your actual start date)
        lease_start_date = datetime.fromisoformat(
            f"{lease_agreement.start_date}"
        )  # Example: February 28, 2023

        # Calculate the current date
        current_date = datetime.now()

        # Calculate the next payment date
        while lease_start_date < current_date:
            next_month_date = lease_start_date + timedelta(
                days=30
            )  # Assuming monthly payments
            # Ensure that the result stays on the same day even if the next month has fewer days
            # For example, if input_date is January 31, next_month_date would be February 28 (or 29 in a leap year)
            # This code snippet adjusts it to February 28 (or 29)
            if lease_start_date.day != next_month_date.day:
                next_month_date = next_month_date.replace(day=lease_start_date.day)
                lease_start_date = next_month_date
            else:
                lease_start_date += timedelta(days=30)  # Assuming monthly payments

        next_payment_date = lease_start_date
        # Return a response
        return Response(
            {"next_payment_date": next_payment_date, "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )

    # Create a method to retrieve all payment dates for a specific user's subscription
    @action(detail=False, methods=["post"], url_path="payment-dates")
    def payment_dates(self, request, pk=None):
        # Retrieve user id from request body
        user_id = request.data.get("user_id")
        # Retrieve the user object from the database by id
        user = User.objects.get(id=user_id)
        lease_agreement = LeaseAgreement.objects.get(tenant=user, is_active=True)
        # Retrieve the unit object from the user object
        unit = lease_agreement.rental_unit
        # Retrieve the lease agreement object from the unit object

        # Input lease start date (replace with your actual start date)
        lease_start_date = datetime.fromisoformat(
            f"{lease_agreement.start_date}"
        )  # Example: February 28, 2023

        # Calculate the lease end date
        lease_end_date = datetime.fromisoformat(
            f"{lease_agreement.end_date}"
        )  # Example: February 28, 2023

        # Create a ppayment dates list
        payment_dates = [
        ]

        # Calculate the next payment date
        while lease_start_date <= lease_end_date:
            # Check for transaction in database to see if payment has been made
            transaction_paid = Transaction.objects.filter(
                rental_unit=unit,
                created_at__date=lease_start_date.date()  # Extracts only the date part for comparison
            ).exists()
            
            event_title = "Rent Due"  # Default title
            
            if transaction_paid:
                event_title = "Rent Paid"
            #check if the 
            payment_dates.append({
                "title": event_title,
                "payment_date": lease_start_date,
                "transaction_paid": transaction_paid,
            })
            
            # Move to the next month's payment date
            lease_start_date += timedelta(days=30)  # Assuming monthly payments
            
            # Ensure that the next month's date doesn't exceed the lease_end_date
            if lease_start_date > lease_end_date:
                break

            # Check if the next month's date exceeds the lease_end_date
            # If so, set the payment date to the lease_end_date
            if lease_start_date + timedelta(days=30) > lease_end_date:
                lease_start_date = lease_end_date

            # Check if the payment for the next month has already been made
            # If so, update the lease_start_date to that payment date
            transaction_paid_next_month = Transaction.objects.filter(
                rental_unit=unit,
                created_at__date=lease_start_date.date()  # Extracts only the date part for comparison
            ).exists()

            if transaction_paid_next_month:
                lease_start_date += timedelta(days=30)

        # Return a response with the payment dates list
        return Response(
            {"payment_dates": payment_dates, "status": status.HTTP_200_OK},
            status=status.HTTP_200_OK,
        )
