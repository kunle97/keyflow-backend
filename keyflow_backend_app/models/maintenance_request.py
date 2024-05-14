from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Tenant
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
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None) #related owner
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, related_name='tenant_maintenance_request') #related tenant that created the request
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    priority = models.IntegerField(default=1) #1-5 scale with 5 being the highest priority. COnvertewd to text as 1=low, 2=moderate, 3=high, 4=urgent, 5=emergency
    type = models.CharField(max_length=35, choices=SERVICE_TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_TYPE_CHOICES, default='pending')
    is_archived = models.BooleanField(default=False)
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'maintenance_requests'

    def __str__(self):
        return f"Maintenance Request for Unit {self.rental_unit.name} at {self.rental_unit.rental_property.name}"
   