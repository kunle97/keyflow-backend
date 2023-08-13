from rest_framework import permissions
from rest_framework.permissions import  BasePermission
from .models import RentalProperty
class IsLandlordOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user and request.user.account_type == 'landlord'

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


        if request.method  == 'POST' and (user_id != int(request_id)):
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
        
        #create variable for request body
        request_body_property = request.data.get('rental_property')
        #retrieve property object from  request_body_property variable
        property_object = RentalProperty.objects.get(pk=request_body_property)
        print(f"REequest body proprerty {request_body_property}")
        property_user_id = property_object.user.id #id of the user who owns the property

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
        print(f"request.user: {request.user.id}")
        print(f"obj.user: {obj.user.id}")
        return obj.user == request.user
    
    def has_permission(self, request, view):
        # Allow resource creation (POST) only if the user is the owner
        if view.action == 'create':
            return True
        return request.user and request.user.is_authenticated