from rest_framework import viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from ..models.transaction import Transaction
from ..serializers.transaction_serializer import  TransactionSerializer
from ..permissions import IsResourceOwner, ResourceCreatePermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

#Create a viewset for transactions model
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsResourceOwner, ResourceCreatePermission]
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'type' ]
    ordering_fields = ['description', 'type', 'amount', 'timestamp' ]
    filterset_fields = ['description', 'type', 'timestamp' ]
    def get_queryset(self):
        user = self.request.user  # Get the current user
        queryset = super().get_queryset().filter(user=user)
        return queryset
