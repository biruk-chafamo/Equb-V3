from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile

from ...models import *
from ...domain import validation
from .equb import EqubSerializer
from .identity import ListUserSerializer


class EqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['receiver'] = ListUserSerializer(instance.receiver, context=self.context).data
        return response
    
    def validate(self, attrs):
        sender = self.context.get('request').user
        equb = attrs.get('equb')

        if validation.is_member(sender, equb.members.all()):
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
        if not validation.is_member(sender, equb.members.all()):
            raise serializers.ValidationError({"sender": f'only members of {equb.name} can send invitations.'})
        if validation.is_member(receiver, equb.members.all()):
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

        if validation.is_self_request(sender, receiver):
            raise serializers.ValidationError({"receiver": f'you cannot send a friend request to yourself.'})
        if validation.is_member(receiver, sender.friends.all()):
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
