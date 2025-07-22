from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token

class ExpiringToken(models.Model):
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='expiring_token')
    expiration_date = models.DateTimeField()
    
    class Meta:
        db_table = 'expiring_tokens'
        
    def is_expired(self):
        return timezone.now() > self.expiration_date

    def __str__(self):
        return f"Token({self.token.key}) expires at {self.expiration_date}"