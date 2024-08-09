from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """
    Custom permission to only allow owners to access their own lease templates.
    """

    def has_permission(self, request, view):
        # Allow access only to authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Owners can access their own lease templates
        return obj.owner.user == request.user
