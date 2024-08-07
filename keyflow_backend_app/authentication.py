from .models.expiring_token import ExpiringToken
from rest_framework.authentication import TokenAuthentication

class ExpiringTokenAuthentication(TokenAuthentication):
    model = ExpiringToken

    def authenticate(self, request):
        auth = request.headers.get('Authorization', '').split()
        
        if not auth or auth[0].lower() != 'bearer':
            return None

        if len(auth) == 1:
            return None
        elif len(auth) > 2:
            return None

        try:
            key = auth[1]
        except UnicodeError:
            return None

        return self.authenticate_credentials(key)

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