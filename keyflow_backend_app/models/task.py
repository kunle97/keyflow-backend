from tracemalloc import start
from turtle import title
from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Staff

class Task(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None) #Owner of the task
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, default=None, related_name='staff_task', blank=True, null=True) #Staff assigned to the task
    title = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True, null=True, default=None)
    status = models.CharField(max_length=100, blank=True, null=True, default="incomplete") #Status of the task values: ['incomplete', 'in_progress', 'completed']
    due_date = models.DateTimeField(blank=True, null=True, default=None)
    start_date = models.DateTimeField(blank=True, null=True, default=None)
    completed_date = models.DateTimeField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'tasks'
    def __str__(self):
        return self.title
    