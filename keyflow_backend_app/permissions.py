from rest_framework import permissions

class IsLandlordOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.property.user == request.user and request.user.account_type == 'landlord'

class IsTenantOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.unit.property.user == request.user and request.user.account_type == 'tenant'
