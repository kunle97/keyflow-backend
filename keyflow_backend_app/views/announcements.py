from rest_framework import viewsets, status
from datetime import datetime, timezone, timedelta
from rest_framework.response import Response
from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from keyflow_backend_app.models.announcement import Announcement
from keyflow_backend_app.serializers.annoucement_serializer import AnnouncementSerializer
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from keyflow_backend_app.models.account_type import Owner


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication, SessionAuthentication]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["target"]
    search_fields = ["title", "body"]
    ordering_fields = ["title", "body","created_at","start_date","end_date"]


    def get_queryset(self):
        user = self.request.user
        owner = Owner.objects.get(user=user)
        queryset = super().get_queryset().filter(owner=owner)
        return queryset
    
    #Create a function that the tenant will call to get the announcements
    def get_announcements_for_tenant(self, tenant):
        queryset = super().get_queryset().filter(target=tenant)
        return queryset
    
    #Create a "create" function that will used to overrride the POST method
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        owner = Owner.objects.get(user=user)
        owner_plan_permission = OwnerPlanAccessControl(owner)

        if not owner_plan_permission.can_use_announcements():
            return Response({"message": "To access the announcements feature, you need to upgrade your subscription plan to the Keyflow Owner Standard Plan or higher."}, status=status.HTTP_400_BAD_REQUEST)

        title = data['title']
        body = data['body']
        severity = data['severity']
        target = data['target']
        start_date = data['start_date']
        end_date = data['end_date']

        start_date_str = start_date[:-5]  # Remove the 'Z' at the end
        end_date_str = end_date[:-5]  # Remove the 'Z' at the end

        start_date_utc = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
        end_date_utc = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
        #ADd a day to the end date and start date
        start_date_updated = start_date_utc + timedelta(days=1)
        end_date_updated = end_date_utc + timedelta(days=1)
        announcement = Announcement.objects.create(
            title=title,
            body=body,
            severity=severity,
            target=target,
            owner=owner,
            start_date=start_date_updated,
            end_date=end_date_updated
        )
        announcement.save()
        return Response({"message": "Announcement created successfully"}, status=status.HTTP_201_CREATED)
    
    #Create a "partial_update" function that will used to overrride the PATCH method
    # def partial_update(self, request, *args, **kwargs):
    #     data = request.data.copy()
    #     user = request.user
    #     owner = Owner.objects.get(user=user)
    #     title = data['title']
    #     body = data['body']
    #     severity = data['severity']
    #     target = data['target']
    #     start_date = data['start_date']
    #     end_date = data['end_date']

    #     start_date_str = start_date[:-5]  # Remove the 'Z' at the end
    #     end_date_str = end_date[:-5]  # Remove the 'Z' at the end

    #     start_date_utc = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
    #     end_date_utc = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
    #     #ADd a day to the end date
    #     end_date_utc = end_date_utc + timedelta(days=1)
    #     announcement = Announcement.objects.get(id=kwargs['pk'])
    #     announcement.title = title
    #     announcement.body = body
    #     announcement.severity = severity
    #     announcement.target = target
    #     announcement.start_date = start_date_utc
    #     announcement.end_date = end_date_utce
    #     announcement.save()
    #     return Response({"message": "Announcement updated successfully"}, status=status.HTTP_200_OK)