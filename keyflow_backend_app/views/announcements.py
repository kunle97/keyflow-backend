import pytz
from rest_framework import viewsets, status
from datetime import datetime
from django.utils.timezone import make_aware
from rest_framework.response import Response
from keyflow_backend_app.helpers.owner_plan_access_control import OwnerPlanAccessControl
from keyflow_backend_app.models.announcement import Announcement
from keyflow_backend_app.serializers.announcement_serializer import AnnouncementSerializer
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from keyflow_backend_app.authentication import ExpiringTokenAuthentication
from keyflow_backend_app.models.account_type import Owner
from django.utils.timezone import make_aware
from ..permissions.announcement_permissions import IsResourceOwnerOrReadOnly

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, IsResourceOwnerOrReadOnly]
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
    
    # Create a "create" function that will be used to override the POST method
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

        start_date_str = start_date[:-1]  # Remove the 'Z' at the end
        end_date_str = end_date[:-1]  # Remove the 'Z' at the end

        # Convert to datetime
        start_date_local = datetime.fromisoformat(start_date_str)
        end_date_local = datetime.fromisoformat(end_date_str)

        # Define the local timezone (assuming -04:00 offset)
        local_timezone = pytz.timezone('America/New_York')

        # Set the start date's time to 12am and the end date's time to 11:59pm
        start_date_updated = start_date_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date_updated = end_date_local.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Make the dates timezone-aware in the local timezone
        start_date_aware = make_aware(start_date_updated, local_timezone)
        end_date_aware = make_aware(end_date_updated, local_timezone)

        announcement = Announcement.objects.create(
            title=title,
            body=body,
            severity=severity,
            target=target,
            owner=owner,
            start_date=start_date_aware,
            end_date=end_date_aware
        )
        announcement.save()
        return Response({"message": "Announcement created successfully"}, status=status.HTTP_201_CREATED)
    


    # Create a partial_update function that will be used to override the PATCH method
    def partial_update(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        owner = Owner.objects.get(user=user)
        owner_plan_permission = OwnerPlanAccessControl(owner)

        if not owner_plan_permission.can_use_announcements():
            return Response(
                {"message": "To access the announcements feature, you need to upgrade your subscription plan to the Keyflow Owner Standard Plan or higher."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            title = data['title']
            body = data['body']
            severity = data['severity']
            target = data['target']
            start_date = data['start_date']
            end_date = data['end_date']

            # Check if the date strings are valid ISO format
            if 'Z' in start_date:
                start_date_str = start_date[:-1]  # Remove the 'Z' at the end
            else:
                start_date_str = start_date

            if 'Z' in end_date:
                end_date_str = end_date[:-1]  # Remove the 'Z' at the end
            else:
                end_date_str = end_date

            # Convert to datetime
            start_date_local = datetime.fromisoformat(start_date_str)
            end_date_local = datetime.fromisoformat(end_date_str)


            # Define the local timezone (assuming -04:00 offset)
            local_timezone = pytz.timezone('America/New_York')

            # Set the start date's time to 12am and the end date's time to 11:59pm
            start_date_updated = start_date_local.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_updated = end_date_local.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Make the dates timezone-aware in the local timezone
            start_date_aware = make_aware(start_date_updated, local_timezone)
            end_date_aware = make_aware(end_date_updated, local_timezone)

            print("start_date: ",start_date)
            print("end_date: ",end_date)
            print("start_date_str: ",start_date_str)
            print("end_date_str: ",end_date_str)
            print("start_date_updated: ",start_date_updated)
            print("end_date_updated: ",end_date_updated)

            announcement = Announcement.objects.get(id=kwargs['pk'])
            announcement.title = title
            announcement.body = body
            announcement.severity = severity
            announcement.target = target
            announcement.start_date = start_date_updated
            announcement.end_date = end_date_updated
            announcement.save()
            return Response({"message": "Announcement updated successfully"}, status=status.HTTP_200_OK)

        except KeyError as e:
            print(f"Missing key in request data: {e}")
            return Response({"error": f"Missing key: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            print(f"Invalid date format: {e}")
            return Response({"error": f"Invalid date format: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        