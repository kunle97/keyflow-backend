from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    severity = models.CharField(max_length=255, default='info') #possible values: success,info, warning, error
    target = models.TextField(blank=False, null=False, default=None) #Will contain JSON String of the target audience. Example: {"rental_unit": 2}, {"portfolio": 1}, {"rental_property": 1}
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None, related_name='announcements')
    start_date = models.DateTimeField(default=datetime.now, blank=True)#Date the announcement is to be shown to the tenant dashboard
    end_date = models.DateTimeField(default=datetime.now, blank=True)#Date the announcement is to be removed from the tenant dashboard
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'

    def __str__(self):
        return f"Announcement: {self.title}"