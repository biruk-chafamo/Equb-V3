from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import approval, validation
from .equb import EqubSummarySerializer
from .identity import NestedUserSerializer


class EqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):
    """A request to join, with the tally and trust signal members vote on."""

    equb_id = serializers.IntegerField(read_only=True)
    approvals = serializers.SerializerMethodField()
    rejections = serializers.SerializerMethodField()
    required_approvals = serializers.SerializerMethodField()
    current_user_vote = serializers.SerializerMethodField()
    trusted_by = serializers.SerializerMethodField()
    trusted_by_count = serializers.SerializerMethodField()

    def _votes(self, instance):
        return instance.votes.all()

    def _trusted_by(self, instance):
        # both sides read their prefetch cache; .filter() would defeat it
        friends = {friend.id for friend in instance.sender.friends.all()}
        return [member for member in instance.equb.members.all() if member.id in friends]

    def get_approvals(self, instance):
        return sum(1 for vote in self._votes(instance) if vote.approve)

    def get_rejections(self, instance):
        return sum(1 for vote in self._votes(instance) if not vote.approve)

    def get_required_approvals(self, instance):
        return approval.required_approvals(
            len(instance.equb.members.all()), instance.equb.join_approval_policy
        )

    def get_current_user_vote(self, instance):
        user = self.context.get('request').user
        for vote in self._votes(instance):
            if vote.voter_id == user.id:
                return vote.approve
        return None

    def get_trusted_by(self, instance):
        return NestedUserSerializer(self._trusted_by(instance), many=True, context=self.context).data

    def get_trusted_by_count(self, instance):
        return len(self._trusted_by(instance))

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['sender'] = NestedUserSerializer(instance.sender, context=self.context).data
        return response

    def validate(self, attrs):
        sender = self.context.get('request').user
        equb = attrs.get('equb')

        if equb.members.filter(pk=sender.pk).exists():
            raise serializers.ValidationError({"receiver": f'You are already a member of {equb.name}.'})
        if equb.is_active or equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer request to join {equb.name}."})
        if EqubJoinRequest.objects.filter(
            sender=sender, equb=equb, is_accepted=False, is_rejected=False, is_expired=False
        ).exists():
            raise serializers.ValidationError({"equb": f'You have already asked to join {equb.name}.'})
        return attrs

    class Meta:
        model = EqubJoinRequest
        fields = [
            'id', 'url', 'sender', 'receiver', 'equb', 'equb_id', 'creation_date',
            'is_expired', 'is_accepted', 'is_rejected',
            'approvals', 'rejections', 'required_approvals', 'current_user_vote',
            'trusted_by', 'trusted_by_count',
        ]
        read_only_fields = ['sender', 'receiver', 'creation_date', 'is_expired', 'is_accepted', 'is_rejected']


class EqubJoinRequestVoteSerializer(serializers.Serializer):
    approve = serializers.BooleanField()


class AcceptEqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSummarySerializer(instance.equb, context=self.context).data
        return response
    class Meta:
        model = EqubJoinRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_expired', 'is_accepted', 'is_rejected', 'creation_date']
        read_only_fields = ['sender', 'receiver', 'equb', 'creation_date']


class EqubInviteRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSummarySerializer(instance.equb, context=self.context).data
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
        if not equb.members.filter(pk=sender.pk).exists():
            raise serializers.ValidationError({"sender": f'only members of {equb.name} can send invitations.'})
        if equb.members.filter(pk=receiver.pk).exists():
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
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['equb'] = EqubSummarySerializer(instance.equb, context=self.context).data
        return response
    
    class Meta:
        model = EqubJoinRequest
        fields = ['id', 'url', 'sender', 'receiver', 'equb', 'is_accepted', 'is_expired', 'creation_date', 'is_rejected']
        read_only_fields = ['sender', 'receiver', 'equb', 'creation_date']


class FriendRequestSerializer(serializers.HyperlinkedModelSerializer):
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['sender'] = NestedUserSerializer(instance.sender, context=self.context).data
        return response
    
    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')

        if validation.is_self_request(sender, receiver):
            raise serializers.ValidationError({"receiver": f'you cannot send a friend request to yourself.'})
        if sender.friends.filter(pk=receiver.pk).exists():
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
        response['receiver'] = NestedUserSerializer(instance.receiver, context=self.context).data
        response['sender'] = NestedUserSerializer(instance.sender, context=self.context).data
        return response
    class Meta:
        model = FriendRequest
        fields = ['id', 'url', 'sender', 'receiver', 'is_accepted', 'creation_date']
        read_only_fields = ['sender', 'receiver', 'creation_date']
