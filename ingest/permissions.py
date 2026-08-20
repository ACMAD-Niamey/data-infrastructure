from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    """
    Allows access when either HeaderAPIKeyAuthentication (X-API-Key) or
    DRF's TokenAuthentication (Authorization: Token ...) succeeded — both
    populate request.auth on success (an APIKey instance or a Token
    instance respectively), so this check works for either without caring
    which one actually authenticated the request.
    """
    def has_permission(self, request, view):
        return request.auth is not None
