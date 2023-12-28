from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner
class RentalProperty(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=100, blank=True)
    street = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(blank=True, null=True)
    country = models.CharField(max_length=100, default='United States')
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'rental_properties'

    def __str__(self):
        return f"Property {self.name} at {self.street} {self.city}, {self.state} {self.zip_code}"
