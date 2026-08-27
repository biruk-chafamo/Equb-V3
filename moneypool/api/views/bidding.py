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
from ..pagination import BoundedPagination
from ...services import equb_service
from ...adapters.django_notifier import default_notifier


class BidViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    """
    place and view bids for an equb.
    """

    serializer_class = BidSerializer
    pagination_class = BoundedPagination

    def get_queryset(self):
        equbs = self.request.user.joined_equbs.all()
        if equbs is None:
            return None
        return Bid.objects.filter(equb__in=equbs) # all bids that belong to equbs joined by current user

    def perform_create(self, serializer):
        bid = equb_service.place_bid(
            user=self.request.user,
            equb=serializer.validated_data['equb'],
            amount=serializer.validated_data['amount'],
        )
        serializer.instance = bid
