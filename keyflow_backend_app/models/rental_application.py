from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.rental_unit import RentalUnit

class RentalApplication(models.Model):
    # Existing fields
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=False) 
    date_of_birth = models.DateField(default=None, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    desired_move_in_date = models.DateField()
    is_archived = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approval_hash = models.CharField(max_length=100, blank=True, null=True, default=None, unique=True)
    unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, default=None) #Unit that the application is for
    other_occupants = models.BooleanField(default=None)
    pets = models.BooleanField(default=None)
    vehicles = models.BooleanField(default=None)
    convicted = models.BooleanField(default=None)
    bankrupcy_filed = models.BooleanField(default=None)
    evicted = models.BooleanField(default=None)
    employment_history = models.TextField(blank=True, null=True)
    residential_history = models.TextField(blank=True, null=True)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_application_landlord') #related landlord that created the application
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True, related_name='tenant_application_tenant') #related tenant that created the application
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'rental_applications'

    def __str__(self):
        return f"{self.first_name} {self.last_name} Rental Application"


