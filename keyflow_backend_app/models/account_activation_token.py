from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User    

#Create a model that stores Account Activation tokens for users that register and need to activate their account
class AccountActivationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    email = models.EmailField(unique=False)
    token = models.CharField(max_length=100, blank=True, null=True, default=None, unique=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'account_activation_tokens'

    def __str__(self):
        return f"Account Activation for {self.user}"
