from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication 
from rest_framework.permissions import IsAuthenticated 
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.models.portfolio import Portfolio
from ..serializers.portfolio_serializer import PortfolioSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["name", "description", "created_at"]
    search_fields = ["name", "description", "created_at"]
    filterset_fields = ["name"]

    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        return Portfolio.objects.filter(owner=owner)
