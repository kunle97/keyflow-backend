import os
import stripe
from dotenv import load_dotenv
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models.user import User
from faker import Faker
from ..models.rental_property import RentalProperty
from ..models.rental_unit import RentalUnit
faker = Faker()
load_dotenv()
#----------TEST FUNCTIONS ----------------

#test to see if tooken is valid and return user info
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def test_token(request):
    return Response("passed for {}".format(request.user.username))

#Create a function to retrieve all landlord userss emails
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @authentication_classes([TokenAuthentication, SessionAuthentication])   
def get_landlord_emails(request):
    #Retrieve all landlord users
    landlords = User.objects.filter(account_type='landlord')
    #Create a list of landlord emails
    landlord_emails = []
    for landlord in landlords:
        landlord_emails.append(landlord.email)
    #Return a response
    return Response(landlord_emails, status=status.HTTP_200_OK)


@api_view(['POST'])
def generate_properties(request):
    count = request.data.get('count', 1)
    int_count = int(count)
    user_id = request.data.get('user_id')

    #create a entries for properties with faker data with count number in a loop
    while(int_count > 0):
        RentalProperty.objects.create(
            name=faker.company(),
            street=faker.street_address(),
            city=faker.city(),
            state=faker.state(),
            zip_code=faker.postcode(),
            country="Unites States",
            user=User.objects.get(id=user_id),
        )
        int_count -= 1
    #Return a response
    return Response({"message":"Properties created", "status":status.HTTP_201_CREATED}, status=status.HTTP_200_OK)

@api_view(['POST'])
def generate_units(request):
    count = request.data.get('count', 1)
    int_count = int(count)
    data=request.data.copy()
    user_id = data['user_id']
    rental_property_id = data['rental_property']
    subscription_id = data['subscription_id']
    product_id = data['product_id']

    #Retrieve all of the landlord's properties
    properties = RentalProperty.objects.filter(user_id=user_id)
    #retrieve user
    user = User.objects.get(id=user_id)
    
    stripe.api_key = os.getenv('STRIPE_SECRET_API_KEY')
    subscription = stripe.Subscription.retrieve( 
        subscription_id, #Retrieve the subscription from stripe
    )

    # If user has the premium plan, check to see if they have 10 or less units
    if product_id == os.getenv('STRIPE_STANDARD_PLAN_PRODUCT_ID'):
        if RentalUnit.objects.filter(user=user).count() >= 10 or int_count > 10 or int_count + RentalUnit.objects.filter(user=user).count() > 10:
            return Response({'message': 'You have reached the maximum number of units for your subscription plan. Please upgrade to a higher plan.'}, status=status.HTTP_400_BAD_REQUEST)
    #If user has the pro plan, increase the metered usage for the user based on the new number of units
    if product_id == os.getenv('STRIPE_PRO_PLAN_PRODUCT_ID'):
        #Update the subscriptions quantity to the new number of units
        subscription_item=stripe.SubscriptionItem.modify(
            subscription['items']['data'][0].id,
            quantity=RentalUnit.objects.filter(user=user).count() + int_count,
        )
    while(int_count > 0):
        #if rental_property_id is None Choose a random property
        if rental_property_id is None:
            property = properties.order_by('?').first() #random property
        else:
            property = properties.get(id=rental_property_id)
        #Create a rental unit for the property
        RentalUnit.objects.create(
            name=faker.lexify(text='?#'), #Generate a 2 charachter string that the first character is a random letter and the 2nd character is a random number  using faker 
            rental_property=property,
            beds=faker.pyint(min_value=1, max_value=5),
            baths=faker.pyint(min_value=1, max_value=5),
            user=user,
            size=faker.pyint(min_value=500, max_value=5000)
        )
        int_count -= 1
    #Return a response
    return Response({"message":"Units created", "status":status.HTTP_201_CREATED}, status=status.HTTP_200_OK)