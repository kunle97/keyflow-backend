from django.db import models
from datetime import datetime

#Create a model that storse password reset tokens for users that forget their password and want to reset it
class PasswordResetToken(models.Model):
    email = models.EmailField(unique=False)
    token = models.CharField(max_length=100, blank=True, null=True, default=None, unique=True)
    expires_at = models.DateTimeField(default=datetime.now,  blank=False)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'password_reset_tokens'

    def __str__(self):
        return f"Password Reset for {self.user}"
    