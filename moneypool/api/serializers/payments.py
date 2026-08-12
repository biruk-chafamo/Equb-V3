from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation
from .identity import ListUserSerializer, PaymentMethodSerializer


class AddressPaymentConfirmationRequestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PaymentConfirmationRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['id', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'creation_date']
    
    sender = ListUserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)

    def validate(self, attrs):
        if validation.is_accept_and_reject_conflict(attrs.get('is_accepted'), attrs.get('is_rejected')):
            raise serializers.ValidationError({"is_accepted": "You cannot accept and reject a payment request."})
        return attrs

class ListPaymentConfirmationRequestSerializer(serializers.HyperlinkedModelSerializer):

    sender = ListUserSerializer(read_only=True)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['payment_method'] = PaymentMethodSerializer(instance.payment_method, context=self.context).data
        return response

    class Meta:
        model = PaymentConfirmationRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['id', 'sender', 'receiver', 'is_accepted', 'is_rejected', 'creation_date']

class PaymentConfirmationRequestSerializer(serializers.HyperlinkedModelSerializer):
    sender = ListUserSerializer(read_only=True)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['payment_method'] = PaymentMethodSerializer(instance.payment_method, context=self.context).data
        return response

    def validate(self, attrs):
        sender = self.context.get('request').user
        equb = attrs.get('equb')
        round = attrs.get('round')

        if not equb.is_active:
            raise serializers.ValidationError({"equb": f"{equb.name} is not yet active."})
        if equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer send payment requests for {equb.name}."})

        win = equb.balance_manager.wins.filter(round=round).first()
        if win is None:
            raise serializers.ValidationError({"round": f"Payment requests cannot be sent until a winner is determined for this round."})
        receiver = win.user

        # if payment method is not shared between sender and receiver then raise error
        if not PaymentMethod.objects.filter(user=receiver, service=attrs.get('payment_method').service).exists():
            raise serializers.ValidationError({"payment_method": "You must use a payment method that is also used by the receiver."})
        if PaymentConfirmationRequest.objects.filter(sender=sender, receiver=receiver, equb=equb, round=round, is_accepted=False).exists():
            raise serializers.ValidationError({"receiver": f'You have an existing pending payment request to {receiver.username} for this round.'})
        if sender == receiver:
            raise serializers.ValidationError({"receiver": f'you cannot send a payment request to yourself.'})

        attrs['receiver'] = receiver
        return attrs

    class Meta:
        model = PaymentConfirmationRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['id', 'sender', 'receiver', 'is_accepted', 'is_rejected', 'creation_date']
