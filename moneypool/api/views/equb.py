from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q
from django.conf import settings
import stripe

from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework_simplejwt.tokens import RefreshToken
from enum import Enum

from ..serializers import *
from ...models import *
from ..permissions import *
from ...services import equb_service
from ...adapters.django_notifier import default_notifier


class EqubViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    equbs joined by a user to be viewed or edited.
    """

    serializer_class = EqubSerializer

    def get_queryset(self):
        user = self.request.user
        joined_equbs = user.joined_equbs.all()
        invited_equbs = Equb.objects.filter(id__in=user.received_equbinviterequests.values_list('equb__id', flat=True))
        recommended_equbs = Equb.objects.filter(id__in=NewEqubNotification.objects.filter(receiver=user, equb__is_active=False).values_list('equb__id', flat=True))
        combined_equbs = joined_equbs | invited_equbs | recommended_equbs
        return combined_equbs.distinct()
        
    def perform_create(self, serializer):
        equb = equb_service.create_equb(creator=self.request.user, **serializer.validated_data)
        serializer.instance = equb

    @action(detail=False, methods=['get'], url_path='activeequbs')
    def active_equbs(self, request):
        """
        get equbs that user has joined and are active
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_active=True, is_completed=False)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pendingequbs')
    def pending_equbs(self, request):
        """
        get equbs that user has joined and are not active but not completed
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_active=False, is_completed=False)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='invitedequbs')
    def invited_equbs(self, request):
        """
        get equbs that user has been invited to
        """
        user = self.request.user
        invitations = user.received_equbinviterequests.all()
        equbs = [invitation.equb for invitation in invitations]
        # making sure that the equbs are not active and user has not joined them
        equbs = [equb for equb in equbs if not equb.is_active and not user.joined_equbs.filter(id=equb.id).exists()]
        equbs = list(set(equbs))
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pastequbs')
    def past_equbs(self, request):
        """
        get equbs that user has completed
        """
        user = self.request.user
        equbs = user.joined_equbs.filter(is_completed=True)
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='recommendedequbs')
    def recommended_equbs(self, request):
        """
        get new public equbs that have been created by users friends
        """
        user = self.request.user
        new_equb_notifications = NewEqubNotification.objects.filter(receiver=user, equb__is_active=False)
        equbs = [notification.equb for notification in new_equb_notifications]
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
   
    @action(detail=False, methods=['get'], url_path='by-user')
    def by_user(self, request):
        """
        get public equbs that a specific user has joined, or the specified user's private 
        equbs that the current user has access to through invitation or shared membership.
        """
        user_id = request.query_params.get('user')
        if not user_id:
            return Response(
                {"detail": "User is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.get(id=user_id)
        current_user = self.request.user
        public_equbs = user.joined_equbs.filter(is_private=False)
        shared_private_equbs = user.joined_equbs.filter(is_private=True, members__in=[current_user])
        current_user_invited_equbs = Equb.objects.filter(id__in=user.received_equbinviterequests.values_list('equb__id', flat=True))
        invited_private_equbs = current_user_invited_equbs.filter(is_private=True, members__in=[user])
        equbs = public_equbs | shared_private_equbs | invited_private_equbs
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
