from rest_framework import permissions
from rest_framework.permissions import  BasePermission
from .models.rental_property import RentalProperty
from .models.rental_unit import RentalUnit
from .models.message import Message
from rest_framework.response import Response
from rest_framework import status
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user and request.user.account_type == 'owner'

class IsTenantOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.unit.rental_property.user == request.user and request.user.account_type == 'tenant'
    
class CustomUpdatePermission(BasePermission):
    """
    General Permission class to check that a user can update his own resource only
    """

    # check that its an update request and user is modifying his resource only
    def has_permission(self, request, view):
        request_id = request.user.id #id of the user making the request
        #check if view.kwargs.get('pk', None) is a string
        if type(view.kwargs.get('pk', None)) is str: 
            url_id = int(view.kwargs.get('pk', None)) #id in the url
        else:
            url_id = view.kwargs.get('pk', None) #id in the url converted to int
        if (request.method  == 'PUT' or request.method =='PATCH') and url_id != request_id:
            return False # not grant access
        return True # grant access otherwise


#create a custom permission class that does not allow the creation of a User
class DisallowUserCreatePermission(BasePermission):
    """
    Permission class to check that a user can create his own resource only
    """

    def has_permission(self, request, view):
        # check that its a create request and user is creating a resource only
        print(f"Request Method {request.method}")
        print(f"View Action  {view.action}")
        if request.method  == 'POST' or view.action == 'create':
            return False # not grant access
        return True # grant access otherwise

#create a custom permission class for creating a resource
class PropertyCreatePermission(BasePermission):
    """
    Permission class to check that a user can create his own property resource only
    """

    def has_permission(self, request, view):
        # check that its a create request and user is creating a resource only
        request_id = request.user.id #id of the user making the request
        #create variable for request body
        request_body_user = request.data.get('user')
         #check if view.kwargs.get('pk', None) is a string

        if type(request_body_user) is str: 
            user_id = int(request_body_user) #id in the url converted from string to int
        else:
            user_id = view.kwargs.get('pk', None) #id in the url as an int

        if request.method  == 'POST' and (int(request_body_user) != int(request_id)):
            return False # not grant access
        return True # grant access otherwise

class CustomDeletePermission(BasePermission):
    """
    Permission class to check that a user can delete his own resource only
    """
        
    def has_permission(self, request, view):
        request_id = request.user.id #id of the user making the request
        #check if view.kwargs.get('pk', None) is a string
        if type(view.kwargs.get('pk', None)) is str: 
            url_id = int(view.kwargs.get('pk', None)) #id in the url
        else:
            url_id = view.kwargs.get('pk', None) #id in the url converted to int
        if (request.method == 'DELETE' and url_id != request_id):
            if not request.user.is_authenticated:
                return False
        return True

#Unit Permissions
#Verify
#Create custom permission class for creating a unit, maintenance request, lease_agreement, etc. where only users who own the property can make a unit for that property
class ResourceCreatePermission(BasePermission):
    """
    Permission class to check that a user can create his own unit resource only
    """

    def has_permission(self, request, view):
        # check that its a create request and user is creating a resource only
        request_id = request.user.id #id of the user making the request
        
        if(request.method  == 'POST' ):
            #create variable for request body
            request_body_property = request.data.get('rental_property')
            #retrieve property object from  request_body_property variable
            print(f"Request body proprerty {request_body_property}")
            property_object = RentalProperty.objects.get(pk=request_body_property)
            property_user_id = property_object.owner.user.id #id of the user who owns the property
            if request.method  == 'POST' and (property_user_id != int(request_id)):
                return False # not grant access
            
        return True # grant access otherwise

#Create Custome permission class for updating a unit where only users who own the property can update a unit for that property
# class UnitUpdatePermission(BasePermission):
#     """
#     Permission class to check that a user can update his own unit resource only
#     """

#     def has_permission(self, request, view):
#         # check that its a create request and user is creating a resource only
#         request_id = request.user.id #id of the user making the request
        
#         #create variable for request body
#         request_body_property = request.data.get('rental_property')

#         #retrieve property object from  request_body_property variable
#         property_object = RentalProperty.objects.get(id=request_body_property)
#         property_user_id = property_object.user.id #id of the user who owns the property

#         if (request.method  == 'PUT' or request.method  == 'PATCH') and (property_user_id != int(request_id)):
#             return False # not grant access
#         return True # grant access otherwise
    
# #Create Custome permission class for deleting a unit where only users who own the property can delete a unit for that property
# class UnitDeletePermission(BasePermission):
#     """
#     Permission class to check that a user can delete his own unit resource only
#     """

#     def has_permission(self, request, view):
#         # check that its a create request and user is creating a resource only
#         request_id = request.user.id #id of the user making the request
        
#         #create variable for request body
#         request_body_property = request.data.get('rental_property')

#         #retrieve property object from  request_body_property variable
#         property_object = RentalProperty.objects.get(id=request_body_property)
#         property_user_id = property_object.user.id #id of the user who owns the property

#         if request.method  == 'DELETE' and (property_user_id != int(request_id)):
#             return False # not grant access
#         return True # grant access otherwise

class IsResourceOwner(permissions.BasePermission):
    """
    Custom permission to only allow the owner of a resource to modify or delete it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the resource (e.g., property, unit, lease agreement)
        return obj.owner.user == request.user
    
    def has_permission(self, request, view):
        # Allow resource creation (POST) only if the user is the owner
        if view.action == 'create':
            return True
        return request.user and request.user.is_authenticated
    

#Create a permission that allows RentalAppliocation to only be created if the unit_id exists
class RentalApplicationCreatePermission(BasePermission):

    def has_permission(self, request, view):

        #create variable for request body
        request_body_unit = request.data.get('unit')

        # unit_object = RentalUnit.objects.get(id=request_body_unit)
        # unit_user_id = unit_object.rental_property.user.id #id of the user who owns the property
        
        # #Create variable for RentalApplication
        # owner_id = request.data.get('owner_id')

        # #confirm the id and unit's user id match
        # if request.method  == 'POST' and (unit_user_id != owner_id):
        #     return False # not grant access

        #retrieve unit object from  request_body_unit variable
        unit_object_exists = RentalUnit.objects.filter(id=request_body_unit).exists()
        if request.method  == 'POST' and (unit_object_exists):
            return Response({"message": "Unit does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        return True # grant access otherwise
    
#Create a permission that only allows a property to be deleted if it has no units
class PropertyDeletePermission(permissions.BasePermission):

    def has_permission(self, request, view):
        
        if request.method  == 'GET':
            print(f"Request Method {request.method}")
            return True
        #Check if method is POST and user  owns the property
        if request.method  == 'POST':
            return True 


        if request.method  == 'DELETE':
            print(f"Request Method {request.method}")
            #retrieve primarky key from url 
            url_id = view.kwargs.get('pk', None) #id in the url converted to int

            request_id = request.user.id #id of the user making the request
            #request.data.get('rental_property')
            #create variable for request body
            request_body_property = url_id

            #retrieve property object from  request_body_property variable
            property_object = RentalProperty.objects.get(id=request_body_property)
            property_user_id = property_object.owner.user.id #id of the user who owns the property

            #Check if the property has units
            property_has_units = RentalUnit.objects.filter(rental_property=property_object).count() > 0
            print(f"zx Property has units {property_has_units}")
            #return a 403 response  message if the property has units
            if property_has_units:
                return Response({"message": "You cannot delete a property that has units"}, status=status.HTTP_403_FORBIDDEN)

            #confirm the id and unit's user id match
            if (property_user_id != int(request_id)):
                return Response({"message": "You cannot delete a property that you do not own"}, status=status.HTTP_401_UNAUTHORIZED)
            return True # grant access otherwise
    
#Create a permission that only allows a unit to be deleted if it has no tenants
class UnitDeletePermission(permissions.BasePermission):
    
        def has_permission(self, request, view):
            if request.method  == 'DELETE':
                #retrieve primarky key from url 
                url_id = view.kwargs.get('pk', None) #id in the url converted to int
    
                request_id = request.user.id #id of the user making the request
                #request.data.get('rental_property')
                #create variable for request body
                request_body_unit = url_id
    
                #retrieve unit object from  request_body_property variable
                unit_object = RentalUnit.objects.get(id=request_body_unit)
                unit_user_id = unit_object.rental_property.user.id #id of the user who owns the property
    
                #Check if the unit has tenants
                unit_has_tenants = RentalUnit.objects.filter(id=unit_object.id, is_occupied=True).count() > 0
                
                #return a 403 response  message if the property has units
                if unit_has_tenants:
                    return Response({"message": "You cannot delete a unit that has tenants"}, status=status.HTTP_403_FORBIDDEN)
    
                #confirm the id and unit's user id match
                if (unit_user_id != int(request_id)):
                    return Response({"message": "You cannot delete a unit that you do not own"}, status=status.HTTP_401_UNAUTHORIZED)
                return True # grant access otherwise
            return True # grant access otherwise
        
#-----MESSAGE PERMISSIONS-----#
#Create a permission that only allows a message to be deleted if the user is the sender or recipient
class MessageDeletePermission(permissions.BasePermission):
    
        def has_permission(self, request, view):
            if request.method  == 'DELETE':
                #retrieve primarky key from url 
                url_id = view.kwargs.get('pk', None) #id in the url converted to int
    
                request_id = request.user.id #id of the user making the request
                #request.data.get('rental_property')
                #create variable for request body
                request_body_message = url_id
    
                #retrieve unit object from  request_body_property variable
                message_object = Message.objects.get(id=request_body_message)
                message_sender_id = message_object.sender.id #id of the user who owns the property
                message_recipient_id = message_object.recipient.id #id of the user who owns the property
    
                #confirm the id and unit's user id match
                if (message_sender_id != int(request_id) and message_recipient_id != int(request_id)):
                    return Response({"message": "You cannot delete a message that you did not send"}, status=status.HTTP_401_UNAUTHORIZED)
                return True # grant access otherwise
            return True # grant access otherwise

#Create permission that only allows owners to send messages to thier tenants and tenants to only send messages to their owners
class MessageCreatePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            if request.method  == 'POST':
                #retrieve primarky key from url 
                # url_id = view.kwargs.get('pk', None) #id in the url converted to int
    
                request_id = request.user.id #id of the user making the request
                #request.data.get('rental_property')
                #create variable for request body
                request_body_sender = request.data.get('sender')
                request_body_recipient = request.data.get('recipient')
    
                #retrieve unit object from  request_body_property variable
                # message_object = Message.objects.get(id=request_body_message)
                # message_sender_id = message_object.sender.id #id of the user who owns the property
                # message_recipient_id = message_object.recipient.id #id of the user who owns the property
    
                #confirm the id and unit's user id match
                if (request_body_sender != int(request_id) and request_body_recipient != int(request_id)):
                    return Response({"message": "You cannot send a message to a user that you are not associated with"}, status=status.HTTP_401_UNAUTHORIZED)
                return True # grant access otherwise
            return True # grant access otherwise