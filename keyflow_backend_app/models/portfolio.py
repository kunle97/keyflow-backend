from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner

class Portfolio(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'portfolios'
    def __str__(self):
        return f"{self}"