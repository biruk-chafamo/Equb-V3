from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.conf import settings

from guardian.shortcuts import assign_perm

from .models import *


@receiver(signal=post_save, sender=User)
def assign_user_perm(sender, instance, created, **kwargs):
    user = instance
    if created and user.username != settings.ANONYMOUS_USER_NAME:
        # allowing user to make changes to self
        assign_perm("moneypool.change_user", user)
        assign_perm("change_user", user, user)


@receiver(signal=post_save, sender=Equb)
def set_creator_membership(sender, instance, created, **kwargs):
    equb = instance
    if created:
        # including creator as a member
        equb.members.add(equb.creator)
        # allowing creator to make changes to equb
        assign_perm("moneypool.change_equb", equb.creator)
        assign_perm("change_equb", equb.creator, equb)


@receiver(signal=post_save, sender=Equb)
def new_equb_action(sender, instance, created, **kwargs):
    equb = instance
    if created:
        NewEqubNotification.notify(equb=equb)


# TODO: send a 'round_changed' signal inside background tasks instead of checking round change for each post_save signal
@receiver(signal=post_save, sender=Equb)
def new_round_action(sender, instance, created, **kwargs):
    equb = instance
    if equb.current_round != sender.objects.get(pk=equb.pk).current_round:
        NewRoundNotification.notify(equb=equb)


@receiver(signal=m2m_changed, sender=Equb.members.through)
def new_member_action(sender, instance, **kwargs):
    equb = instance
    if kwargs['action'] == 'post_add':
        new_member = equb.members.first()  # equb members are ordered by date_joined
        NewMemberNotification.notify(equb=equb, new_member=new_member)
        if equb.members.all().count() == equb.max_members:
            equb.activate()
            


@receiver(signal=post_save, sender=EqubJoinRequest)
def assign_equb_join_request_perm(sender, instance, created, **kwargs):
    equb_request = instance
    if created:
        assign_perm('moneypool.change_equbjoinrequest', equb_request.receiver)
        assign_perm('change_equbjoinrequest', equb_request.receiver, equb_request)


@receiver(signal=post_save, sender=EqubInviteRequest)
def assign_equb_invite_request_perm(sender, instance, created, **kwargs):
    equb_request = instance
    if created:
        assign_perm('moneypool.change_equbinviterequest', equb_request.receiver)
        assign_perm('change_equbinviterequest', equb_request.receiver, equb_request)


@receiver(signal=post_save, sender=FriendRequest)
def assign_friend_request_perm(sender, instance, created, **kwargs):
    friend_request = instance
    if created:
        assign_perm('moneypool.change_friendrequest', friend_request.receiver)
        assign_perm('change_friendrequest', friend_request.receiver, friend_request)


