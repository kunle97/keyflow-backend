from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.rental_unit import RentalUnit

class MaintenanceRequest(models.Model):
    SERVICE_TYPE_CHOICES = (
        ('plumbing', 'Plumbling'),
        ('electrical', 'Electrical'),
        ('appliance', 'Appliance'),
        ('structural', 'Structural'),
        ('hvac', 'HVAC'),
        ('other', 'Other'),
    )
    STATUS_TYPE_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    type = models.CharField(max_length=35, choices=SERVICE_TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_TYPE_CHOICES, default='pending')
    is_archived = models.BooleanField(default=False)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #related landlord
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_maintenance_request') #related tenant that created the request
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'maintenance_requests'

    def __str__(self):
        return f"Maintenance Request for Unit {self.rental_unit.name} at {self.rental_unit.rental_property.address}"
   