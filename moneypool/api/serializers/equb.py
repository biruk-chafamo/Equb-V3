from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation
from ...services import settlement_service
from .identity import NestedUserSerializer, WinnerUserSerializer


class EqubSummarySerializer(serializers.ModelSerializer):
    """An equb as a feed row, and nested inside an invite."""

    members = NestedUserSerializer(many=True, read_only=True)
    creator_id = serializers.IntegerField(read_only=True)
    latest_winner = serializers.SerializerMethodField(method_name='get_latest_winner')
    current_round = serializers.SerializerMethodField(method_name='get_current_round')
    current_award = serializers.SerializerMethodField(method_name='get_current_award')
    current_highest_bid = serializers.SerializerMethodField(method_name='get_current_highest_bid')
    percent_joined = serializers.SerializerMethodField(method_name='get_percent_joined')
    percent_completed = serializers.SerializerMethodField(method_name='get_percent_completed')
    is_won_by_user = serializers.SerializerMethodField(method_name='get_is_won_by_user')
    user_payment_status = serializers.SerializerMethodField(method_name='get_user_payment_status')
    time_left_till_next_round = serializers.SerializerMethodField(method_name='get_time_left_till_next_round')
    current_user_is_member = serializers.SerializerMethodField(method_name='get_current_user_is_member')
    pending_join_request_count = serializers.SerializerMethodField()
    current_user_join_request_status = serializers.SerializerMethodField()

    def _memo(self, equb, key, compute):
        """Derive a value once per equb per request."""
        cache = equb.__dict__.setdefault('_serializer_memo', {})
        if key not in cache:
            cache[key] = compute()
        return cache[key]

    def _current_round(self, equb):
        return self._memo(equb, 'current_round', equb.balance_manager.current_round)

    def _highest_bid(self, equb):
        """The current round's HighestBid row."""
        def find():
            target = self._current_round(equb)
            for highest_bid in equb.highest_bids.all():
                if highest_bid.round == target:
                    return highest_bid
            return None
        return self._memo(equb, 'highest_bid', find)

    def _latest_winner(self, equb):
        return self._memo(equb, 'latest_winner', equb.balance_manager.latest_winner)

    def _round_requests(self, equb):
        """This round's payment confirmation requests, fetched once."""
        return self._memo(
            equb, 'round_requests', equb.balance_manager.round_payment_requests
        )

    def _payers(self, equb, kind):
        return self._memo(
            equb,
            kind,
            lambda: getattr(equb.balance_manager, kind)(self._round_requests(equb)),
        )

    def _undecided_join_requests(self, equb):
        # reads the prefetch cache; .filter() would defeat it
        return self._memo(equb, 'undecided_join_requests', lambda: [
            join_request for join_request in equb.equbjoinrequests.all()
            if not (join_request.is_accepted or join_request.is_rejected or join_request.is_expired)
        ])

    def get_pending_join_request_count(self, equb):
        if not self.get_current_user_is_member(equb):
            return 0
        return len(self._undecided_join_requests(equb))

    def get_current_user_join_request_status(self, equb):
        user = self.context.get('request').user
        if any(r.sender_id == user.id for r in self._undecided_join_requests(equb)):
            return 'pending'
        rejected = any(
            r.sender_id == user.id and r.is_rejected for r in equb.equbjoinrequests.all()
        )
        return 'rejected' if rejected else 'none'

    def get_current_user_is_member(self, equb):
        # reads the prefetch cache; .exists() would defeat it
        return self.context.get('request').user in equb.members.all()

    def get_time_left_till_next_round(self, equb):
        return equb.balance_manager.time_left_till_next_round()

    def get_current_round(self, equb):
        return self._current_round(equb)

    def get_current_award(self, equb):
        balace_manager = equb.balance_manager
        return settlement_service.calculate_winners_award(balace_manager, balace_manager.current_round())

    def get_current_highest_bid(self, equb):
        highest_bid = self._highest_bid(equb)
        if highest_bid is not None and highest_bid.bid:
            return highest_bid.bid.amount
        return 0

    def get_percent_joined(self, equb):
        return equb.balance_manager.percent_joined()

    def get_percent_completed(self, equb):
        return equb.balance_manager.percent_completed()

    def get_is_won_by_user(self, equb):
        return equb.balance_manager.check_received(self.context.get('request').user)

    def get_user_payment_status(self, equb):
        user = self.context.get('request').user
        current_winner = self._latest_winner(equb)

        if user == current_winner:
            return 'winner'
        elif user in self._payers(equb, 'confirmed_payers'):
            return 'confirmed'
        elif user in self._payers(equb, 'unconfirmed_payers'):
            return 'unconfirmed'
        elif user in self._payers(equb, 'rejected_payers'):
            return 'rejected'
        else:
            return 'unpaid'

    def get_latest_winner(self, equb):
        latest_winner = self._latest_winner(equb)
        if latest_winner:
            return WinnerUserSerializer(latest_winner, context=self.context).data
        return None

    class Meta:
        model = Equb
        fields = [
            'id', 'name', 'amount', 'max_members', 'cycle', 'creation_date',
            'is_private', 'is_active', 'is_completed', 'is_in_payment_stage',
            'current_round', 'current_award', 'current_highest_bid',
            'percent_joined', 'percent_completed',
            'is_won_by_user', 'user_payment_status', 'current_user_is_member',
            'pending_join_request_count', 'current_user_join_request_status',
            'time_left_till_next_round', 'latest_winner', 'members', 'creator_id',
        ]


class EqubSerializer(EqubSummarySerializer):
    """A single equb, in full."""

    def validate(self, attrs):
        max_members = attrs.get('max_members')

        if validation.is_max_members_too_low(max_members):
            raise serializers.ValidationError({"max_members": "An equb must have at least 2 members."})
        if validation.is_max_members_too_high(max_members):
            raise serializers.ValidationError({"max_members": "An equb cannot have more than 20 members."})
        if self.instance:
            raise serializers.ValidationError({"equb": "Equbs cannot be updated once created."})
        return attrs

    cycle = serializers.DurationField(max_value=timedelta(days=365), min_value=timedelta(minutes=1))
    current_highest_bidder_id = serializers.SerializerMethodField(method_name='get_current_highest_bidder_id')
    rejected_payer_ids = serializers.SerializerMethodField(method_name='get_rejected_payer_ids')
    confirmed_payer_ids = serializers.SerializerMethodField(method_name='get_confirmed_payer_ids')
    unconfirmed_payer_ids = serializers.SerializerMethodField(method_name='get_unconfirmed_payer_ids')
    unpaid_member_ids = serializers.SerializerMethodField(method_name='get_unpaid_member_ids')
    payment_collection_dates = serializers.SerializerMethodField(method_name='get_payment_collection_dates')
    is_created_by_user = serializers.SerializerMethodField(method_name='get_is_created_by_user')

    def get_is_created_by_user(self, equb):
        return self.context.get('request').user == equb.creator

    def get_payment_collection_dates(self, equb):
        return equb.balance_manager.payment_collection_dates()

    def get_current_highest_bidder_id(self, equb):
        highest_bid = self._highest_bid(equb)
        if highest_bid is not None and highest_bid.bid:
            return highest_bid.bid.user_id
        return None

    def get_rejected_payer_ids(self, equb):
        return [user.id for user in self._payers(equb, 'rejected_payers')]

    def get_unconfirmed_payer_ids(self, equb):
        return [user.id for user in self._payers(equb, 'unconfirmed_payers')]

    def get_confirmed_payer_ids(self, equb):
        return [user.id for user in self._payers(equb, 'confirmed_payers')]

    def get_unpaid_member_ids(self, equb):
        return [user.id for user in self._memo(
            equb,
            'unpaid_members',
            lambda: equb.balance_manager.unpaid_members(self._round_requests(equb)),
        )]

    class Meta(EqubSummarySerializer.Meta):
        fields = EqubSummarySerializer.Meta.fields + [
            'url', 'end_date',
            'current_highest_bidder_id', 'payment_collection_dates', 'is_created_by_user',
            'confirmed_payer_ids', 'unconfirmed_payer_ids', 'unpaid_member_ids', 'rejected_payer_ids',
        ]
        read_only_fields = [
            'id', 'is_active', 'is_completed', 'creation_date', 'end_date', 'is_in_payment_stage',
        ]
