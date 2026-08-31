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


EQUB_PREFETCH = (
    'members',
    'balance_manager__received',
    'balance_manager__wins__user',
    'highest_bids__bid__user',
    'equbjoinrequests',
)


def with_related(queryset):
    return queryset.select_related('balance_manager').prefetch_related(*EQUB_PREFETCH)


def visible_to(user):
    """Equbs a user may open: their own, ones they were invited to, and public equbs by a friend."""
    invited = Equb.objects.filter(
        id__in=user.received_equbinviterequests.values_list('equb__id', flat=True)
    )
    friends_public = Equb.objects.filter(is_private=False, creator__in=user.friends.all())
    return (user.joined_equbs.all() | invited | friends_public).distinct()


class EqubViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    equbs joined by a user to be viewed or edited.
    """

    serializer_class = EqubSerializer

    def get_serializer_class(self):
        if self.action in {'retrieve', 'create', 'update', 'partial_update'}:
            return EqubSerializer
        return EqubSummarySerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'action', None) == 'list':
            return with_related(self._feed(user))
        return with_related(visible_to(user))

    def _feed(self, user):
        """The home feed: what to surface, which is narrower than what may be opened."""
        invited_equbs = Equb.objects.filter(id__in=user.received_equbinviterequests.values_list('equb__id', flat=True))
        recommended_equbs = Equb.objects.filter(id__in=NewEqubNotification.objects.filter(receiver=user, equb__is_active=False).values_list('equb__id', flat=True))
        return (user.joined_equbs.all() | invited_equbs | recommended_equbs).distinct()
        
    def perform_create(self, serializer):
        equb = equb_service.create_equb(creator=self.request.user, **serializer.validated_data)
        serializer.instance = equb

    @action(detail=False, methods=['get'], url_path='activeequbs')
    def active_equbs(self, request):
        """
        get equbs that user has joined and are active
        """
        user = self.request.user
        equbs = with_related(user.joined_equbs.filter(is_active=True, is_completed=False))
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pendingequbs')
    def pending_equbs(self, request):
        """
        get equbs that user has joined and are not active but not completed
        """
        user = self.request.user
        equbs = with_related(user.joined_equbs.filter(is_active=False, is_completed=False))
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='invitedequbs')
    def invited_equbs(self, request):
        """
        get equbs that user has been invited to
        """
        user = self.request.user
        equbs = with_related(
            Equb.objects
            .filter(id__in=user.received_equbinviterequests.values_list('equb_id', flat=True))
            .filter(is_active=False)
            .exclude(id__in=user.joined_equbs.values_list('id', flat=True))
            .distinct()
        )
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='pastequbs')
    def past_equbs(self, request):
        """
        get equbs that user has completed
        """
        user = self.request.user
        equbs = with_related(user.joined_equbs.filter(is_completed=True))
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='recommendedequbs')
    def recommended_equbs(self, request):
        """
        get new public equbs that have been created by users friends
        """
        user = self.request.user
        equbs = with_related(
            Equb.objects.filter(
                id__in=NewEqubNotification.objects
                .filter(receiver=user, equb__is_active=False)
                .values_list('equb_id', flat=True)
            ).distinct()
        )
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
   
    @action(detail=False, methods=['get'], url_path='by-user')
    def by_user(self, request):
        """
        get the equbs a specific user has joined that the viewer is allowed to open
        """
        user_id = request.query_params.get('user')
        if not user_id:
            return Response(
                {"detail": "User is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.get(id=user_id)
        current_user = self.request.user
        # only what the viewer could open anyway, so the profile never lists a 404
        equbs = with_related(
            visible_to(current_user).filter(
                id__in=user.joined_equbs.values_list('id', flat=True)
            )
        )
        serializer = self.get_serializer(equbs, many=True)
        return Response(serializer.data)
