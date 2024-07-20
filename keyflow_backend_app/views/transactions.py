from rest_framework import viewsets
from django.db.models import Q
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from keyflow_backend_app.models.account_type import Owner, Tenant 
from ..models.transaction import Transaction
from ..serializers.transaction_serializer import  TransactionSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
#Create a viewset for transactions model
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]#IsResourceOwner, ResourceCreatePermission
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'type' ,"amount", "timestamp"]
    ordering_fields = ['description', 'type', 'amount', 'timestamp' ]
    filterset_fields = ['description', 'type', 'timestamp' ]
    def get_queryset(self):
        user = self.request.user  # Get the current user
        if user.account_type == 'tenant':
            tenant = Tenant.objects.get(user=user)
            queryset = super().get_queryset().filter(tenant=tenant)
            return queryset
        elif user.account_type == 'owner':
            owner = Owner.objects.get(user=user)  # Get the owner object for the current user
            queryset = super().get_queryset().filter(Q(owner=owner) | Q(user=user))
            return queryset
        else:
            # Handle other account types or raise an error if unexpected
            return super().get_queryset().none()  # or some other appropriate handling