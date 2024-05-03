from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password

from .models import *


class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'url', 'username', 'first_name', 'last_name',
            'email', 'password', 'password2', 'bank_account',
        ]

    def validate(self, attrs):
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

    #  TODO: update (pull requests) dont work. The problem is password

    # def update(self, instance, validated_data):
    #     password = validated_data.pop('password', '')
    #     validated_data.pop('password2', '')
    #     user = User.objects.create(**validated_data)
    #     if password:
    #         user.set_password(validated_data['password'])
    #     user.save()
    #     return user


class ListUserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'first_name', 'last_name', 'friends']  # TODO: remove friends from list


class FriendshipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Friendship
        fields = ['url', 'friend']


class EqubSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Equb
        fields = [
            'url', 'name', 'creator', 'amount', 'max_members', 'members',
            'cycle', 'is_private', 'is_active', 'is_completed'
        ]
        # read_only_fields = ['creator', 'is_active', 'is_completed']
        read_only_fields = ['creator', 'members', 'is_active', 'is_completed']


class EqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

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
        fields = ['url', 'sender', 'receiver', 'equb']
        read_only_fields = ['sender', 'receiver']


class AcceptEqubJoinRequestSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = EqubJoinRequest
        fields = ['url', 'sender', 'receiver', 'equb', 'is_accepted']
        read_only_fields = ['sender', 'receiver', 'equb']


class EqubInviteRequestSerializer(serializers.HyperlinkedModelSerializer):

    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')
        equb = attrs.get('equb')

        # Todo: what about members sending invites (should that be allowed)
        if sender != equb.creator:
            raise serializers.ValidationError({"sender": "Only the equb creator can send an invitation."})
        if receiver in equb.members.all():
            raise serializers.ValidationError({"receiver": f'{receiver.username} is already a member of {equb.name}.'})
        if equb.is_active or equb.is_completed:
            raise serializers.ValidationError({"equb": f"You can no longer invite others to join {equb.name}"})
        return attrs

    class Meta:
        model = EqubInviteRequest
        fields = ['url', 'sender', 'receiver', 'equb']
        read_only_fields = ['sender']


class AcceptEqubInviteRequestSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = EqubJoinRequest
        fields = ['url', 'sender', 'receiver', 'equb', 'is_accepted']
        read_only_fields = ['sender', 'receiver', 'equb']


class FriendRequestSerializer(serializers.HyperlinkedModelSerializer):

    def validate(self, attrs):
        sender = self.context.get('request').user
        receiver = attrs.get('receiver')

        if sender == receiver:
            raise serializers.ValidationError({"receiver": f'you cannot send a friend request to yourself.'})
        if receiver in sender.friends.all():
            raise serializers.ValidationError({"receiver": f'{receiver.username} is already your friend.'})
        return attrs

    class Meta:
        model = FriendRequest
        fields = ['url', 'sender', 'receiver']
        read_only_fields = ['sender']


class AcceptFriendRequestSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FriendRequest
        fields = ['url', 'sender', 'receiver', 'is_accepted']
        read_only_fields = ['sender', 'receiver']