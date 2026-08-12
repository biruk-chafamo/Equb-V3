from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation


class BidSerializer(serializers.HyperlinkedModelSerializer):

    def validate(self, attrs):
        user = self.context.get('request').user
        equb = attrs.get('equb')

        if not validation.is_member(user, equb.members.all()):
            raise serializers.ValidationError({"user": f'You are not a member of {equb.name}.'})
        if validation.is_member(user, equb.balance_manager.received.all()):
            raise serializers.ValidationError({"user": f'You cannot place a bid because you have already won a round for {equb.name}.'})
        if equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer place a bid in {equb.name}."})
        if not equb.is_active:
            raise serializers.ValidationError({"equb": f"{equb.name} is not yet active."})
        if equb.is_in_payment_stage:
            raise serializers.ValidationError({"equb": f"you cannot place a bid in {equb.name} because it is in the payment stage."})
        if validation.is_final_round(equb.balance_manager.current_round(), equb.max_members):
            raise serializers.ValidationError({"equb": f"There is only one member left to receive the pot in {equb.name} -- bidding has no effect on the final round."})
        return attrs
    amount = serializers.DecimalField(max_digits=10, decimal_places=3, max_value=Decimal(1.000), min_value=Decimal(0.001))
    class Meta:
        model = Bid
        fields = ['id', 'url', 'equb', 'amount']
        read_only_fields = ['user', 'date', 'round']
