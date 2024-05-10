from rest_framework import serializers
from ..models.task import Task
from .account_type_serializer import OwnerSerializer, StaffSerializer
class TaskSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(many=False, read_only=True)
    staff = StaffSerializer(many=False, read_only=True)
    
    class Meta:
        model = Task
        fields = '__all__'