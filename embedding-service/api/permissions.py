from rest_framework.permissions import BasePermission


class IsAuthenticatedCustom(BasePermission):
    """
    Custom permission class that works with our JWT middleware.
    """
    
    def has_permission(self, request, view):
        # Check if the middleware has set the is_authenticated attribute
        return getattr(request, 'is_authenticated', False)