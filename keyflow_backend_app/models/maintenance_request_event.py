from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Tenant
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.maintenance_request import MaintenanceRequest

class MaintenanceRequestEvent(models.Model):
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='maintenance_request_events')
    title = models.CharField(max_length=225)
    type = models.CharField(max_length=225)
    description = models.TextField()
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'maintenance_request_events'
    
    def __str__(self):
        return f"{self.title} for Maintenance Request {self.maintenance_request.pk}"