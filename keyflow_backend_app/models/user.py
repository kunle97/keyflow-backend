from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
class User(AbstractUser):
    ACCOUNT_TYPE_CHOICES = (
        ('owner', 'Owner'),
        ('tenant', 'Tenant'),
        ('staff', 'Staff'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'users'
        app_label = 'keyflow_backend_app' 

    def __str__(self):
        return self.email
