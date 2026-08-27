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
from .equb import EQUB_PREFETCH
from ..pagination import BoundedPagination
from ...services import equb_service
from ...adapters.django_notifier import default_notifier


class EqubJoinRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):

    def get_queryset(self):
        user = self.request.user
        return (user.received_equbjoinrequests.all() | user.sent_equbjoinrequests.all()) \
            .select_related('sender', 'receiver', 'equb')

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptEqubJoinRequestSerializer
        else:
            return EqubJoinRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, receiver=serializer.validated_data['equb'].creator)


class EqubInviteRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    pagination_class = BoundedPagination

    def get_queryset(self):
        user = self.request.user
        equbs = user.joined_equbs.all()
        invites_to_joined_equbs = EqubInviteRequest.objects.filter(equb__in=equbs)
        received = user.received_equbinviterequests.all()
        return (received | invites_to_joined_equbs).select_related(
            'sender', 'receiver', 'equb', 'equb__balance_manager'
        ).prefetch_related(*(f'equb__{p}' for p in EQUB_PREFETCH))

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptEqubInviteRequestSerializer
        else:
            return EqubInviteRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        """
        get equb invitations received by user
        """
        user = self.request.user
        # making sure that the equbs are not active and user has not joined them
        invitations = (
            self.get_queryset()
            .filter(receiver=user, is_accepted=False, is_rejected=False, is_expired=False)
            .exclude(equb_id__in=user.joined_equbs.values_list('id', flat=True))
        )
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-equb')
    def by_equb(self, request):
        """
        get equb invitations sent to anyone for a specific equb
        """
        equb_id = request.query_params.get('equb')
        if not equb_id:
            return Response(
                {"detail": "Equb is a required parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
        invitations = self.get_queryset().filter(equb=equb_id)
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

class FriendRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        received = user.received_friendrequests.all()
        sent = user.sent_friendrequests.all()
        return received | sent

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AcceptFriendRequestSerializer
        else:
            return FriendRequestSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        """
        get friend requests received by user
        """
        user = self.request.user
        requests = user.received_friendrequests.filter(is_accepted=False, is_rejected=False, is_expired=False)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='sent')
    def sent(self, request):
        """
        get friend requests sent by user
        """
        user = self.request.user
        requests = user.sent_friendrequests.filter(is_accepted=False, is_rejected=False, is_expired=False)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
