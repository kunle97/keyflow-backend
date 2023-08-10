from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ACCOUNT_TYPE_CHOICES = (
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    stripe_account_id = models.CharField(max_length=100)
    def __str__(self):
        return self.email

class RentalProperty(models.Model):
    name = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    units = models.ManyToManyField('RentalUnit')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return f"Property {self.name} at {self.address}"

class RentalUnit(models.Model):
    name = models.CharField(max_length=100, blank=True)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE)
    lease_agreement = models.ForeignKey('LeaseAgreement', blank=True, null=True, on_delete=models.SET_NULL)
    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.address}"
    
class LeaseAgreement(models.Model):
    rental_property = models.ForeignKey('RentalProperty', on_delete=models.CASCADE)
    rental_unit = models.ForeignKey('RentalUnit', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    terms = models.TextField()
    signed_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Lease Agreement for RentalUnit {self.rental_unit} at {self.rental_property}"

class MaintenanceRequest(models.Model):
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    description = models.TextField()
    resolved = models.BooleanField(default=False)
    def __str__(self):
        return f"Request for Unit {self.rental_unit.name} at {self.rental_unit.rental_property.address}"
