from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.models.portfolio import Portfolio
from keyflow_backend_app.models.lease_template import LeaseTemplate

default_rental_property_preferences = """
[
    {
        "type": "property_preferences",
        "hidden": false,
        "label": "Accept Rental Applications",
        "name": "accept_rental_applications",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting rental applications for this property"
    },
    {
        "type": "property_preferences",
        "hidden": false,
        "label": "Acccept Lease Renewals",
        "name": "accept_lease_renewals",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting lease renewals for this property"
    },
    {
        "type": "property_preferences",
        "hidden": false,
        "label": "Accept Lease Cancellations",
        "name": "accept_lease_cancellations",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting lease cancellations for this property"
    },
    {
        "type": "unit_preferences",
        "hidden": false,
        "label": "Allow Lease Auto Renewal",
        "name": "allow_lease_auto_renewal",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is allowing tenants in subsequent units to enable auto renewal of their lease"
    }
]
"""


class RentalProperty(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=100, blank=False, null=False, default=None)
    street = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(blank=True, null=True)
    country = models.CharField(max_length=100, default='United States', blank=True, null=True)
    lease_template = models.ForeignKey(LeaseTemplate, on_delete=models.SET_NULL, related_name='rental_properties', default=None, blank=True, null=True)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.SET_NULL, related_name='rental_properties', default=None, blank=True, null=True)
    preferences = models.TextField(blank=True, null=True, default=default_rental_property_preferences) #JSON string of property preferences
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'rental_properties'

    def __str__(self):
        return f"Property {self.name} at {self.street} {self.city}, {self.state} {self.zip_code}"
