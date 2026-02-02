from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey


class HeaderAPIKeyAuthentication(BaseAuthentication):
    """
    Client sends:  X-API-Key: <key>
    """
    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request):
        key = request.META.get(self.header_name)
        if not key:
            return None  # DRF will treat as unauthenticated

        api_key = APIKey.objects.filter(key=key, is_active=True).first()
        if not api_key:
            raise AuthenticationFailed("Invalid or inactive API key")

        # DRF expects (user, auth) tuple; we don't use Django User here
        return (None, api_key)
