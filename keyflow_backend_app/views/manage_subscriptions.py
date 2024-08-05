import os
import stripe
from dotenv import load_dotenv
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models.user import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
load_dotenv()


class RetrieveOwnerSubscriptionPriceView(APIView):
    def post(self, request):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        #New Standard Plan
        owner_standard_plan_product = stripe.Product.retrieve(
            os.getenv("STRIPE_OWNER_STANDARD_PLAN_PRODUCT_ID")
        )
        owner_standard_plan_price = stripe.Price.retrieve(owner_standard_plan_product.default_price)
        
        #New Professional Plan
        owner_professional_plan_product = stripe.Product.retrieve(
            os.getenv("STRIPE_OWNER_PROFESSIONAL_PLAN_PRODUCT_ID")
        )
        owner_professional_plan_price = stripe.Price.retrieve(owner_professional_plan_product.default_price)
        
        #New Enterprise Plan
        owner_enterprise_plan_product = stripe.Product.retrieve(
            os.getenv("STRIPE_OWNER_ENTERPRISE_PLAN_PRODUCT_ID")
        )
        owner_enterprise_plan_price = stripe.Price.retrieve(owner_enterprise_plan_product.default_price)

        serialized_products = [
            {
                "product_id": owner_standard_plan_product.id,
                "name": owner_standard_plan_product.name,
                "price": owner_standard_plan_price.unit_amount / 100,  # Convert to dollars
                "price_id": owner_standard_plan_price.id,
                "features": owner_standard_plan_product.marketing_features,
                "billing_scheme": owner_standard_plan_price.recurring,
            },
            {
                "product_id": owner_professional_plan_product.id,
                "name": owner_professional_plan_product.name,
                "price": owner_professional_plan_price.unit_amount / 100,  # Convert to dollars
                "price_id": owner_professional_plan_price.id,
                "features": owner_professional_plan_product.marketing_features,
                "billing_scheme": owner_professional_plan_price.recurring,
            },
            {
                "product_id": owner_enterprise_plan_product.id,
                "name": owner_enterprise_plan_product.name,
                "price": owner_enterprise_plan_price.unit_amount / 100,  # Convert to dollars
                "price_id": owner_enterprise_plan_price.id,
                "features": owner_enterprise_plan_product.marketing_features,
                "billing_scheme": owner_enterprise_plan_price.recurring,
            },
        ]
        return Response({"products": serialized_products}, status=status.HTTP_200_OK)

# Create a class that handles manageing a tenants stripe subscription (rent) called ManageTenantSusbcriptionView
class ManageTenantSubscriptionView(viewsets.ModelViewSet):
    # TODO: Investigate why authentication CLasses not working
    queryset = User.objects.all()
    