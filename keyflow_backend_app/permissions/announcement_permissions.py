from rest_framework.permissions import BasePermission

class IsResourceOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an announcement to edit or delete it.
    Everyone else can only view (read) the announcements.
    """

    def has_permission(self, request, view):
        # Allow any authenticated user to list and create announcements
        if view.action in ['list', 'retrieve', 'create']:
            return request.user and request.user.is_authenticated

        # Allow safe methods (GET, HEAD, OPTIONS) for authenticated users
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated

        # Otherwise, only allow access if the user is authenticated and is the owner
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to the owner of the announcement
        return obj.owner.user == request.user