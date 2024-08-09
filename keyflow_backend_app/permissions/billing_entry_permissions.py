from rest_framework.permissions import BasePermission
from ..models.account_type import Owner

class IsResourceOwner(BasePermission):
    """
    Custom permission to only allow owners to create, edit, or delete billing entries.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and is an owner
        return request.user and request.user.is_authenticated and Owner.objects.filter(user=request.user).exists()

    def has_object_permission(self, request, view, obj):
        # Check if the user is authenticated and is an owner
        return request.user and request.user.is_authenticated and Owner.objects.filter(user=request.user).exists()

