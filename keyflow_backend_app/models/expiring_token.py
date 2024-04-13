from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token

class ExpiringToken(Token):
    expiration_date = models.DateTimeField()

    class Meta:
        db_table = 'expiring_tokens'
        
    def is_expired(self):
        return timezone.now() > self.expiration_date
