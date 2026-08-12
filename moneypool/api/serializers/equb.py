from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation
from ...services import settlement_service
from .identity import ListUserSerializer


class EqubSerializer(serializers.ModelSerializer):

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
    members = ListUserSerializer(many=True, read_only=True)
    creator = ListUserSerializer(read_only=True)
    current_round = serializers.SerializerMethodField(method_name='get_current_round')
    current_award = serializers.SerializerMethodField(method_name='get_current_award')
    current_highest_bid = serializers.SerializerMethodField(method_name='get_current_highest_bid')
    current_highest_bidder = serializers.SerializerMethodField(method_name='get_current_highest_bidder')
    percent_joined = serializers.SerializerMethodField(method_name='get_percent_joined')
    percent_completed = serializers.SerializerMethodField(method_name='get_percent_completed')
    is_won_by_user = serializers.SerializerMethodField(method_name='get_is_won_by_user')
    user_payment_status = serializers.SerializerMethodField(method_name='get_user_payment_status')
    latest_winner = serializers.SerializerMethodField(method_name='get_latest_winner')
    time_left_till_next_round = serializers.SerializerMethodField(method_name='get_time_left_till_next_round')
    rejected_payers = serializers.SerializerMethodField(method_name='get_rejected_payers')
    confirmed_payers = serializers.SerializerMethodField(method_name='get_confirmed_payers')
    unconfirmed_payers = serializers.SerializerMethodField(method_name='get_unconfirmed_payers')
    unpaid_members = serializers.SerializerMethodField(method_name='get_unpaid_members')
    current_user_is_member = serializers.SerializerMethodField(method_name='get_current_user_is_member')
    payment_collection_dates = serializers.SerializerMethodField(method_name='get_payment_collection_dates')
    is_created_by_user = serializers.SerializerMethodField(method_name='get_is_created_by_user')

    def get_is_created_by_user(self, equb):
        return self.context.get('request').user == equb.creator
    
    def get_payment_collection_dates(self, equb):
        return equb.balance_manager.payment_collection_dates()

    def get_current_user_is_member(self, equb):
        return self.context.get('request').user in equb.members.all()
    
    def get_rejected_payers(self, equb):
        return ListUserSerializer(equb.balance_manager.rejected_payers(), many=True, context=self.context).data
    
    def get_unconfirmed_payers(self, equb):
        return ListUserSerializer(equb.balance_manager.unconfirmed_payers(), many=True, context=self.context).data
           
    def get_confirmed_payers(self, equb):
        return ListUserSerializer(equb.balance_manager.confirmed_payers(), many=True, context=self.context).data
    
    def get_unpaid_members(self, equb):
        return ListUserSerializer(equb.balance_manager.unpaid_members(), many=True, context=self.context).data
    
    def get_time_left_till_next_round(self, equb):
        return equb.balance_manager.time_left_till_next_round()

    def get_current_round(self, equb):
        return equb.balance_manager.current_round()
    
    def get_current_award(self, equb):
        balace_manager = equb.balance_manager
        return settlement_service.calculate_winners_award(balace_manager, balace_manager.current_round())
    
    def get_current_highest_bid(self, equb):
        highest_bid = HighestBid.objects.get(equb=equb, round=equb.balance_manager.current_round()).bid
        if highest_bid:
            return highest_bid.amount
        return 0
    
    def get_current_highest_bidder(self, equb):
        highest_bid = HighestBid.objects.get(equb=equb, round=equb.balance_manager.current_round()).bid
        if highest_bid:
            return ListUserSerializer(highest_bid.user, context=self.context).data
        else:
            return None
    
    def get_percent_joined(self, equb):
        return equb.balance_manager.percent_joined()
    
    def get_percent_completed(self, equb):
        return equb.balance_manager.percent_completed()
    
    def get_is_won_by_user(self, equb):
        return equb.balance_manager.check_received(self.context.get('request').user)
    
    def get_user_payment_status(self, equb):
        user = self.context.get('request').user
        current_winner = equb.balance_manager.latest_winner()
        
        if user == current_winner:
            return 'winner'
        elif user in equb.balance_manager.confirmed_payers():
            return 'confirmed'
        elif user in equb.balance_manager.unconfirmed_payers():
            return 'unconfirmed'
        elif user in equb.balance_manager.rejected_payers():
            return 'rejected'
        else:
            return 'unpaid'

    
    def get_latest_winner(self, equb):
        latest_winner = equb.balance_manager.latest_winner()
        if latest_winner:
            return ListUserSerializer(latest_winner, context=self.context).data
        return None
    class Meta:
        model = Equb
        fields = [
            'id', 'url', 'name', 'creator', 'amount', 'max_members', 'members',
            'cycle', 'is_private', 'is_active', 'is_completed', 'creation_date', 'end_date', 'is_in_payment_stage',
            'current_round', 'current_award', 'current_highest_bid', 'current_highest_bidder',
            'percent_joined', 'percent_completed',
            'is_won_by_user', 'user_payment_status', 'latest_winner', 'time_left_till_next_round', 
            'confirmed_payers', 'unconfirmed_payers', 'unpaid_members', 'rejected_payers', 'current_user_is_member', 'payment_collection_dates', 'is_created_by_user'
        ]
        read_only_fields = ['id', 'creator', 'members', 'is_active', 'is_completed', 'creation_date', 'end_date', 'is_in_payment_stage']
