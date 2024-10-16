from django.db import models
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.uploaded_file import UploadedFile

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    body = models.TextField()
    file = models.ForeignKey(UploadedFile, related_name='messages', on_delete=models.CASCADE, null=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'

    def __str__(self):
        return f"Message from {self.sender} to {self.recipient} - {self.timestamp}"
