from rest_framework.permissions import BasePermission

class IsResourceOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners to modify or delete lease agreements.
    """

    def has_permission(self, request, view):
        # Allow read-only access to authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Allow write permissions only for authenticated users who are owners
        return request.user.is_authenticated and request.user.account_type == 'owner'

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Owners can modify or delete their lease agreements
        if user.account_type == 'owner':
            return obj.owner.user == user
        # Tenants can only view their own lease agreements
        if user.account_type == 'tenant':
            return obj.tenant.user == user
        return False

class IsResourceOwner(BasePermission):
    """
    Custom permission to only allow access to resources owned by the user.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.account_type == 'tenant':
            return obj.tenant.user == user
        elif user.account_type == 'owner':
            return obj.owner.user == user
        return False
