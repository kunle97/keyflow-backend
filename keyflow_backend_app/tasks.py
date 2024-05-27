# myapp/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import LeaseAgreement

@shared_task
def check_lease_agreements():
    current_date = timezone.now().date()
    expired_leases = LeaseAgreement.objects.filter(end_date__lt=current_date, is_active=True)
    for lease_agreement in expired_leases:
        lease_agreement.is_active = False
        lease_agreement.tenant = None
        lease_agreement.save()
        
        rental_unit = lease_agreement.rental_unit
        rental_unit.is_occupied = False
        rental_unit.signed_lease_document_file = None
        rental_unit.tenant = None
        rental_unit.save()
    return f"{expired_leases.count()} lease agreements have been updated."

@shared_task
def add(x, y):
    return x + y