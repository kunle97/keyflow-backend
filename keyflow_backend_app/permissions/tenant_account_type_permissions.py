from rest_framework import permissions

class IsTenantOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow tenants of an object to edit it.
    Assumes the model instance has an `tenant` attribute.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.account_type == "tenant"

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the tenant of the object
        return obj.tenant.user == request.user
