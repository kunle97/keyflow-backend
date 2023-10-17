from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models.user import User

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