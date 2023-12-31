from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.rental_unit import RentalUnit 
from keyflow_backend_app.models.rental_property import RentalProperty

#Create a model for transactions that will be used to create a transaction history for each user
class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('expense', 'Expense'),
        ('revenue', 'Revenue'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #landlord related to the transaction
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    description = models.TextField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None, blank=True, null=True)
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE,default=None, blank=True, null=True)
    payment_intent_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    payment_method_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    timestamp = models.DateTimeField(default=datetime.now,  blank=True)\

    class Meta:
        db_table = 'transactions'

    def __str__(self):
        return f"Transaction for {self.user} on {self.timestamp}"
