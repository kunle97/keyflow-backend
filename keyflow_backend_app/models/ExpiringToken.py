from django.utils import timezone
from django.db import models
from rest_framework.authtoken.models import Token

class ExpiringToken(Token):
    expiration_date = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expiration_date
