from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from .models import *


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'url', 'username', 'first_name', 'last_name',
            'email', 'password', 'password2', 'bank_account', 'profile_picture'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        profile_picture = data.get('profile_picture')
        if profile_picture is not None:
            data['profile_picture'] = self.context['request'].build_absolute_uri(profile_picture)
        else:   
            data['profile_picture'] = None

        return data


    def validate(self, attrs):
        # not setting uniquness an non-null constraint in the ORM to avoid back filling the database
        if attrs.get('email') == '' or attrs.get('email') is None:
            raise serializers.ValidationError({"email": "This field may not be blank."})
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({"email": "This email is already used by a different account."})
        
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', '')
        validated_data.pop('password2', '')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    #  TODO: update (put requests) dont work. The problem is password

    # def update(self, instance, validated_data):
    #     password = validated_data.pop('password', '')
    #     validated_data.pop('password2', '')
    #     user = User.objects.create(**validated_data)
    #     if password:
    #         user.set_password(validated_data['password'])
    #     user.save()
    #     return user

class FriendshipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Friendship
        fields = ['id', 'url', 'friend']

class PaymentMethodSerializer(serializers.HyperlinkedModelSerializer):
    def validate(self, attrs):
        user = self.context.get('request').user
        service = attrs.get('service')
        detail = attrs.get('detail')
        
        if PaymentMethod.objects.filter(user=user, service=service, detail=detail).exists():
            raise serializers.ValidationError(
                'A payment method with this user, service, and detail already exists.'
            )
        return attrs
    class Meta:
        model = PaymentMethod
        fields = ['id', 'url', 'user', 'service', 'detail']
        read_only_fields = ['id', 'user']

class ListUserSerializer(serializers.HyperlinkedModelSerializer):
    selected_payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    joined_equbs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'first_name', 'last_name', 'friends', 'score', 'selected_payment_methods', 'joined_equbs', 'profile_picture']  # TODO: remove friends from list
        read_only_fields = ['first_name', 'last_name', 'friends', 'score', 'joined_equbs']


class EditUserSerializer(serializers.HyperlinkedModelSerializer):
    selected_payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    joined_equbs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    class Meta:
        model = User
        fields = ['id', 'url', 'username', 'first_name', 'last_name', 'email', 'bank_account', 'profile_picture', 'score', 'selected_payment_methods', 'friends', 'joined_equbs']
        read_only_fields = ['id', 'username', 'score', 'selected_payment_methods', 'friends', 'joined_equbs']
class EqubSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        max_members = attrs.get('max_members')

        if max_members < 2:
            raise serializers.ValidationError({"max_members": "An equb must have at least 2 members."})
        if max_members > 20:
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
        return balace_manager.calculate_winners_award(balace_manager.current_round())
    
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


class BidSerializer(serializers.HyperlinkedModelSerializer):

    def validate(self, attrs):
        user = self.context.get('request').user
        equb = attrs.get('equb')

        if user not in equb.members.all():
            raise serializers.ValidationError({"user": f'You are not a member of {equb.name}.'})
        if user in equb.balance_manager.received.all():
            raise serializers.ValidationError({"user": f'You cannot place a bid because you have already won a round for {equb.name}.'})
        if equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer place a bid in {equb.name}."})
        if not equb.is_active:
            raise serializers.ValidationError({"equb": f"{equb.name} is not yet active."})
        if equb.is_in_payment_stage:
            raise serializers.ValidationError({"equb": f"you cannot place a bid in {equb.name} because it is in the payment stage."})
        return attrs
    amount = serializers.DecimalField(max_digits=10, decimal_places=3, max_value=Decimal(1.000), min_value=Decimal(0.001))
    class Meta:
        model = Bid
        fields = ['id', 'url', 'equb', 'amount']
        read_only_fields = ['user', 'date', 'round']


class EqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        return response
    
    def validate(self, attrs):
        sender = self.context.get('request').user
        equb = attrs.get('equb')

        if sender in equb.members.all():
            raise serializers.ValidationError({"receiver": f'You are already a member of {equb.name}.'})
        if equb.is_active or equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer request to join {equb.name}."})
        return attrs

    class Meta:
        model = EqubJoinRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_expired', 'is_accepted']
        read_only_fields = ['sender', 'receiver', 'is_expired', 'is_accepted']


class AcceptEqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSerializer(instance.equb, context=self.context).data
        return response
    class Meta:
        model = EqubJoinRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_expired', 'is_accepted', 'creation_date']
        read_only_fields = ['sender', 'receiver', 'equb', 'creation_date']


class EqubInviteRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSerializer(instance.equb, context=self.context).data
        return response
    
    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')
        equb = attrs.get('equb')

        if EqubInviteRequest.objects.filter(receiver=receiver, equb=equb, is_accepted=False, is_expired=False).exists():
            raise serializers.ValidationError({"receiver": f'You or another member of {equb.name} has already sent an invitation to {receiver.username}.'})
        # TODO: think about how invitations should be handled
        # if sender != equb.creator:
        #     raise serializers.ValidationError({"sender": "Only the equb creator can send an invitation."})
        if sender not in equb.members.all():
            raise serializers.ValidationError({"sender": f'only members of {equb.name} can send invitations.'})
        if receiver in equb.members.all():
            raise serializers.ValidationError({"receiver": f'{receiver.username} is already a member of {equb.name}.'})
        if equb.is_active or equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer invite others to join {equb.name}"})
        return attrs

    class Meta:
        model = EqubInviteRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_expired', 'creation_date', 'is_accepted', 'is_rejected']
        read_only_fields = ['sender', 'is_expired', 'creation_date', 'is_accepted', 'is_rejected']


class AcceptEqubInviteRequestSerializer(serializers.HyperlinkedModelSerializer):
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSerializer(instance.equb, context=self.context).data
        return response
    
    class Meta:
        model = EqubJoinRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_accepted', 'is_expired', 'creation_date', 'is_rejected']
        read_only_fields = ['sender', 'receiver', 'equb', 'creation_date']


class FriendRequestSerializer(serializers.HyperlinkedModelSerializer):
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        response['sender'] = ListUserSerializer(instance.sender, context=self.context).data
        return response
    
    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')

        if sender == receiver:
            raise serializers.ValidationError({"receiver": f'you cannot send a friend request to yourself.'})
        if receiver in sender.friends.all():
            raise serializers.ValidationError({"receiver": f'{receiver.username} is already your friend.'})
        if FriendRequest.objects.filter(sender=sender, receiver=receiver, is_accepted=False, is_expired=False, is_rejected=False).exists():
            raise serializers.ValidationError({"receiver": f'You have already sent a friend request to {receiver.username}.'})
        return attrs

    class Meta:
        model = FriendRequest
        fields = ['id', 'url', 'sender', 'receiver', 'is_accepted', 'creation_date']
        read_only_fields = ['sender', 'is_accepted', 'creation_date']

class AcceptFriendRequestSerializer(serializers.HyperlinkedModelSerializer):
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        response['sender'] = ListUserSerializer(instance.sender, context=self.context).data
        return response
    class Meta:
        model = FriendRequest
        fields = ['id', 'url', 'sender', 'receiver', 'is_accepted', 'creation_date']
        read_only_fields = ['sender', 'receiver', 'creation_date']

class AddressPaymentConfirmationRequestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PaymentConfirmationRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['id', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'creation_date']
    
    sender = ListUserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)

    def validate(self, attrs):
        if attrs.get('is_accepted') and attrs.get('is_rejected'):
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

    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')
        equb = attrs.get('equb')
        round = attrs.get('round')
        
        # if payment method is not shared between sender and receiver then raise error
        if not PaymentMethod.objects.filter(user=receiver, service=attrs.get('payment_method').service).exists():
            raise serializers.ValidationError({"payment_method": "You must use a payment method that is also used by the receiver."})
        if not equb.is_active:
            raise serializers.ValidationError({"equb": f"{equb.name} is not yet active."})
        if equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer send payment requests for {equb.name}."})
        if equb.balance_manager.wins.filter(round=round).count() == 0:
            raise serializers.ValidationError({"equb": f"Payment requests cannot be sent until a winner is determined."})
        if PaymentConfirmationRequest.objects.filter(sender=sender, receiver=receiver, equb=equb, round=round, is_accepted=False).exists():
            raise serializers.ValidationError({"receiver": f'You have an existing pending payment request to {receiver.username} for this round.'})
        if sender == receiver:
            raise serializers.ValidationError({"receiver": f'you cannot send a payment request to yourself.'})
        return attrs
    
    # service = serializers.ChoiceField(choices=ServiceChoices.choices)
    sender = ListUserSerializer(read_only=True)
    # payment_method = PaymentMethodSerializer()

    class Meta:
        model = PaymentConfirmationRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'round', 'payment_method', 'message', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['id', 'sender', 'receiver', 'is_accepted', 'is_rejected', 'creation_date']