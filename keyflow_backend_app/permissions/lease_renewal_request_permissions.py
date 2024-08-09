from rest_framework.permissions import BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to allow owners to modify or delete lease renewal requests,
    and to allow tenants to create, view, and delete their own lease renewal requests.
    """

    def has_permission(self, request, view):
        # Allow read-only access to authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Allow write permissions only for authenticated users who are owners or tenants
        return request.user.is_authenticated and request.user.account_type in ['owner', 'tenant']

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Owners can modify or delete their own lease renewal requests
        if user.account_type == 'owner':
            return obj.owner.user == user
        # Tenants can create, view, and delete their own lease renewal requests
        if user.account_type == 'tenant':
            if request.method in ['DELETE', 'PATCH', 'PUT']:
                return obj.tenant.user == user
            return obj.tenant.user == user
        return False