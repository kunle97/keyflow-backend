from rest_framework.permissions import BasePermission

class IsOwnerOrTenant(BasePermission):
    """
    Custom permission to only allow Owners to access all their maintenance requests,
    and Tenants to only access their own maintenance requests.
    """

    def has_permission(self, request, view):
        # Allow access only to authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.account_type == "owner":
            return obj.owner.user == user
        elif user.account_type == "tenant":
            return obj.tenant.user == user
        return False
