from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.rental_property import RentalProperty

class RentalUnit(models.Model):
    name = models.CharField(max_length=100, blank=True)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE, related_name='rental_units')
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #Owner of the unit
    size = models.PositiveIntegerField(default=0)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_unit', blank=True, null=True) #Tenant of the unit
    lease_template = models.ForeignKey('LeaseTemplate', on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='rental_units')
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'rental_units'

    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.street}"
    