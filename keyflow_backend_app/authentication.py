from .models.expiring_token import ExpiringToken
from rest_framework.authentication import TokenAuthentication

class ExpiringTokenAuthentication(TokenAuthentication):
    model = ExpiringToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            return None

        if token.is_expired():
            token.delete()
            return None

        if not token.user.is_active:
            return None

        return (token.user, token)