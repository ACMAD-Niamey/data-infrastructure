from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    """
    Allows access only when HeaderAPIKeyAuthentication succeeded.
    """
    def has_permission(self, request, view):
        return request.auth is not None
