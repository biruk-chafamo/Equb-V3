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
from ...services import equb_service, settlement_service
from ...adapters.django_notifier import default_notifier


class PaymentConfirmationRequestViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        received = user.received_paymentconfirmationrequests.all()
        sent = user.sent_paymentconfirmationrequests.all()
        return (received | sent).select_related('sender', 'receiver', 'equb', 'payment_method')

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in ['PUT', 'PATCH']:
            return AddressPaymentConfirmationRequestSerializer
        elif self.request.method in ['POST']:
            return PaymentConfirmationRequestSerializer
        else:
            return ListPaymentConfirmationRequestSerializer

    def perform_create(self, serializer):
        balance_manager = serializer.validated_data['equb'].balance_manager
        round = serializer.validated_data['round']

        sender = self.request.user
        amount = settlement_service.calculate_losers_deductions(balance_manager, sender, round)

        serializer.save(
            sender=sender,
            receiver=serializer.validated_data['receiver'],
            amount=amount,
        )
        default_notifier.payment_confirmation_requested(serializer.instance)

    @action(detail=False, methods=['get'], url_path='by-equb-round')
    def get_by_equb_and_round(self, request):
        '''
        get all confirmed or unconfirmed payment confirmation requests
        for a specific equb and round. This excludes all rejected requests.
        '''
        equb_id = request.query_params.get('equb')
        round = request.query_params.get('round')

        if not equb_id or not round:
            return Response(
                {"detail": "Equb and round are required parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = (PaymentConfirmationRequest.objects
                    .filter(equb=equb_id, round=round, is_rejected=False)
                    .select_related('sender', 'payment_method'))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PaymentMethodViewSet(AuthenticatedAndObjectPermissionMixin, viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        user = self.request.user
        return user.selected_payment_methods.all()
    
    def perform_create(self, serializer):        
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='services')
    def services(self, request):
        """
        get all available payment services as a list of strings
        """
        services = [service[0] for service in ServiceChoices.choices]
        return Response(services)
