# permissions.py
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """
    Custom permission to only allow owners to access their own portfolios.
    """

    def has_permission(self, request, view):
        # Allow all authenticated users to create and read portfolios
        if request.method in ['GET', 'POST']:
            return request.user and request.user.is_authenticated
        
        # Allow update and delete actions only if the user is authenticated
        if request.method in ['PATCH', 'DELETE']:
            return request.user and request.user.is_authenticated
        
        return False

    def has_object_permission(self, request, view, obj):
        # Allow access only if the portfolio's owner matches the request user
        return obj.owner == request.user.owner
