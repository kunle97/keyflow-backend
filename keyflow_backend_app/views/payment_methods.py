from calendar import c
import os
from dotenv import load_dotenv
import stripe
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from keyflow_backend_app.models.account_type import Owner, Tenant
from ..models.user import User
from ..models.lease_agreement import LeaseAgreement
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

load_dotenv()


class ManagePaymentMethodsView(viewsets.ModelViewSet):
    # Create a function to create a payment method for a user
    @action(detail=False, methods=["post"], url_path="add-payment-method")
    def add_payment_method(self, request, pk=None):
        # Retrieve the user object from the database by id
        user_id = request.data.get("user_id")
        user = User.objects.get(id=user_id)
        payment_method_user = None
        if user.account_type == "tenant":
            payment_method_user = Tenant.objects.get(user=user)
        elif user.account_type == "owner":
            payment_method_user = Owner.objects.get(user=user)

        # Retrieve the stripe account id from the user object
        stripe_customer_id = payment_method_user.stripe_customer_id
        # Retrieve the payment method id from the request
        payment_method_id = request.data.get("payment_method_id")
        # Create a payment method for the user
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id,
        )
        # Return a response
        return Response(
            {
                "message": "Payment method added successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="delete-payment-method")
    def delete_payment_method(self, request, pk=None):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        # Retrieve payment id from the request
        payment_method_id = request.data.get("payment_method_id")
        stripe.PaymentMethod.detach(
            payment_method_id,
        )

    # Create a function to set a payment method as default
    @action(detail=False, methods=["post"], url_path="set-default-payment-method")
    def set_default_payment_method(self, request, pk=None):
        # Set your Stripe API key
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")        
        # Retrieve lease id from the request
        lease_id = request.data.get("lease_agreement_id")
        # retrieve subscription id from the lease object
        subscription_id = None
        if request.data.get("subscription_id"):
            subscription_id = request.data.get("subscription_id")
        else:
            lease = LeaseAgreement.objects.get(id=lease_id)
            subscription_id = lease.stripe_subscription_id
        # Replace with the new payment method details (e.g., card token or payment method ID)
        new_payment_method = request.data.get("payment_method_id")

        # Retrieve the subscription
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Set the default payment method on the subscription
        subscription.default_payment_method = new_payment_method
        subscription.save()
        # Return a response
        return Response(
            {
                "message": "Default payment method set successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )

    #Create function for owner to set default payment method for their subscription
    @action(detail=False, methods=["post"], url_path="set-owner-default-payment-method") #URL: /api/payment-methods/set-default-payment-owner-method-owner/
    def set_owner_default_payment_method_owner(self, request, pk=None):
        # Set your Stripe API key
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")

        #Retrieve the owner customer stripe object
        owner = Owner.objects.get(user=request.user)
        stripe_customer_id = owner.stripe_customer_id
        new_payment_method = request.data.get("payment_method_id")

        #retrieve the subscription from uaing the customer object
        subscriptions = stripe.Subscription.list(customer=stripe_customer_id)
        subscription = subscriptions.data[0]
        #Retreive subscription 
        stripe.Subscription.modify(
            subscription.id,
            default_payment_method=new_payment_method,
        )

        # Return a response
        return Response(
            {
                "message": "Default payment method set successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )
    
    # List payment methods
    @action(detail=False, methods=["post"], url_path="list-payment-methods")
    def list_payment_methods(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get("user_id"))
        payment_method_user = None
        if user.account_type == "tenant":
            payment_method_user = Tenant.objects.get(user=user)
        # Retrieve the stripe account id from the user object
        stripe_customer_id = payment_method_user.stripe_customer_id
        # Create a payment method for the user
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card",
        )
        # Return a response
        return Response(payment_methods, status=status.HTTP_200_OK)

    #Create a function to retrieve all of the owner's payment methods
    @action(detail=False, methods=["post"], url_path="list-owner-payment-methods")
    def list_owner_payment_methods(self, request):
        # Retrieve the owner object from the database by id
        owner = Owner.objects.get(user=request.user)
        stripe_customer_id = owner.stripe_customer_id
        # Create a payment method for the user
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card",
        )

        #Retrierve the default payment method from the subscription
        subscriptions = stripe.Subscription.list(customer=stripe_customer_id)
        subscription = subscriptions.data[0]
        default_payment_method = subscription.default_payment_method

        # Return a response
        return Response(
            {
                "payment_methods":payment_methods, 
                "default_payment_method":default_payment_method
            }, 
        status=status.HTTP_200_OK
        )

    # Create a function to retrieve a stripe subscription by its id
    @action(detail=False, methods=["post"], url_path="retrieve-subscription")
    def retrieve_subscription(self, request):
        # retrieve subscription id from the request
        subscription_id = request.data.get("subscription_id")
        # Create a payment method for the user
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        subscription = stripe.Subscription.retrieve(
            subscription_id,
        )
        # Return a response
        return Response(subscription, status=status.HTTP_200_OK)


    #Create a function that retireves the user'stripe_customer_id and creates a billing_portal session
    @action(detail=False, methods=["post"], url_path="create-billing-portal-session")# URL: /api/payment-methods/create-billing-portal-session/
    def create_billing_portal_session(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get("user_id"))
        return_url =""
        payment_method_user = None
        if user.account_type == "tenant":
            return_url = f'{os.getenv("CLIENT_HOSTNAME")}/dashboard/tenant/my-account'
            payment_method_user = Tenant.objects.get(user=user)
        elif user.account_type == "owner":
            return_url = f'{os.getenv("CLIENT_HOSTNAME")}/dashboard/owner/my-account'
            payment_method_user = Owner.objects.get(user=user)
        # Retrieve the stripe account id from the user object
        stripe_customer_id = payment_method_user.stripe_customer_id

        # Create a billing portal session
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        # Return a response
        return Response(session, status=status.HTTP_200_OK)

# Create a class that adds a card payment method for a user
class AddCardPaymentMethodView(APIView):
    def post(self, request):
        # Retrieve the user object from the database by id
        user = User.objects.get(id=request.data.get("user_id"))
        customer_user = None
        if user.account_type == "tenant":
            customer_user = Tenant.objects.get(user=user)
        elif user.account_type == "owner":
            customer_user = Owner.objects.get(user=user)
        # Retrieve the stripe account id from the user object
        stripe_customer_id = customer_user.stripe_customer_id

        # Retrieve the payment method id from the request
        payment_method_id = request.data.get("payment_method_id")
        # Create a payment method for the user
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id,
        )
        # Return a response
        return Response(
            {
                "message": "Payment method added successfully.",
                "status": status.HTTP_200_OK,
            },
            status=status.HTTP_200_OK,
        )


# Create a class that lists the users payment methods #TODO: Remove this class it is a duplicate of the ManagePaymentMethodsView class's list_payment_methods method
# class ListPaymentMethodsView(APIView):
#     def post(self, request):
#         # Retrieve the user object from the database by id
#         user = User.objects.get(id=request.data.get("user_id"))

#         # Retrieve the stripe account id from the user object
#         stripe_customer_id = user.stripe_customer_id
#         # Create a payment method for the user
#         stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
#         payment_methods = stripe.PaymentMethod.list(
#             customer=stripe_customer_id,
#             type="card",
#         )
#         # Return a response
#         return Response(payment_methods, status=status.HTTP_200_OK)


