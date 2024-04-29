from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner

class Portfolio(models.Model):
    default_portfolio_preferences = """
    [
        {
            "type": "portfolio_preferences",
            "hidden": false,
            "label": "Accept Rental Applications",
            "name": "accept_rental_applications",
            "inputType": "switch",
            "value": true,
            "description": "Indicates if the landlord is accepting rental applications for this portfolio"
        },
        {
            "type": "portfolio_preferences",
            "hidden": false,
            "label": "Acccept Lease Renewals",
            "name": "accept_lease_renewals",
            "inputType": "switch",
            "value": true,
            "description": "Indicates if the landlord is accepting lease renewals for this portfolio"
        },
        {
            "type": "portfolio_preferences",
            "hidden": false,
            "label": "Accept Lease Cancellations",
            "name": "accept_lease_cancellations",
            "inputType": "switch",
            "value": true,
            "description": "Indicates if the landlord is accepting lease cancellations for this portfolio"
        }
    ]
    """

    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    preferences = models.TextField(blank=True, null=True, default=default_portfolio_preferences) #JSON string of property preferences
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'portfolios'
    def __str__(self):
        return f"{self}"