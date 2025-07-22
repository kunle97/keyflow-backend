# views/authentication.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token
from token_extension.models import ExpiringToken
from django.utils import timezone

from rest_framework.authtoken.models import Token
from token_extension.models import ExpiringToken

class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise AuthenticationFailed("Invalid token")

        try:
            exp_token = ExpiringToken.objects.get(token=token)
        except ExpiringToken.DoesNotExist:
            token.delete()
            raise AuthenticationFailed("Token expired or invalid")

        if exp_token.expiration_date < timezone.now():
            exp_token.delete()
            token.delete()
            raise AuthenticationFailed("Token has expired")

        if not token.user.is_active:
            raise AuthenticationFailed("User inactive or deleted")

        return (token.user, token)