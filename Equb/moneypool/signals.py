from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver, Signal
from django.conf import settings
from django.utils import timezone
import datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from django_rest_passwordreset.signals import reset_password_token_created

from guardian.shortcuts import assign_perm

from .models import *
from .tasks import select_winner_task

@receiver(signal=post_save, sender=User)
def new_user(sender, instance, created, **kwargs):
    user = instance

    # assigning permissions to edit user
    if created and user.username != settings.ANONYMOUS_USER_NAME:
        # allowing user to make changes to self
        assign_perm("moneypool.change_user", user)
        assign_perm("change_user", user, user)

    # creating a default payment method for user to be cash
    if created:
        PaymentMethod.objects.create(user=user, service=ServiceChoices.CASH)

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
        BalanceManager.objects.create(equb=equb)
        HighestBid.objects.create(equb=equb, round=1)
        NewEqubNotification.notify(equb=equb)

@receiver(signal=post_save, sender=PaymentConfirmationRequest)
def new_payment_confirmation_request_action(sender, instance, created, **kwargs):
    payment_confirmation_request = instance
    if created:       
        NewPaymentConfirmationRequestNotification.notify(payment_confirmation_request=payment_confirmation_request)

@receiver(signal=m2m_changed, sender=Equb.members.through)
def new_member_action(sender, instance, **kwargs):
    equb = instance
    if kwargs['action'] == 'post_add':
        new_member = equb.members.first()  # equb members are ordered by date_joined
        NewMemberNotification.notify(equb=equb, new_member=new_member)
        if equb.members.count() == equb.max_members:
            equb.activate()
            equb.balance_manager.activate()
            equb.balance_manager.current_round_start_date = datetime.datetime.now()
            equb.balance_manager.save()
            select_winner_task(
                equb.name, schedule=datetime.datetime.now() + equb.cycle
            )

@receiver(signal=post_save, sender=Bid)
def new_bid_action(sender, instance, created, **kwargs):
    bid = instance
    if bid.is_highest_bid():
        previous_highest_bid = HighestBid.objects.get(equb=bid.equb, round=bid.round).bid
        OutBidNotification.notify(equb=bid.equb, previous_highest_bid=previous_highest_bid, new_highest_bid=bid)
        bid.make_highest_bid()


@receiver(signal=new_round_signal, sender=BalanceManager)
def new_round_action(sender, instance, equb, **kwargs):
    balance_manager = instance
    equb = balance_manager.equb
    NewRoundNotification.notify(equb=equb)
    HighestBid(equb=equb, round=balance_manager.finished_rounds + 1).save()
    balance_manager.current_round_start_date = datetime.datetime.now()
    balance_manager.save()
    select_winner_task(equb.name, schedule=datetime.datetime.now() + equb.cycle)

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

@receiver(signal=post_save, sender=PaymentMethod)
def assign_equb_join_request_perm(sender, instance, created, **kwargs):
    payment_method = instance
    if created:
        assign_perm('moneypool.change_paymentmethod', payment_method.user)
        assign_perm('change_paymentmethod', payment_method.user, payment_method)

@receiver(signal=post_save, sender=FriendRequest)
def assign_friend_request_perm(sender, instance, created, **kwargs):
    friend_request = instance
    if created:
        assign_perm('moneypool.change_friendrequest', friend_request.receiver)
        assign_perm('change_friendrequest', friend_request.receiver, friend_request)


@receiver(signal=post_save, sender=PaymentConfirmationRequest)
def assign_payment_confirmation_request_perm(sender, instance, created, **kwargs):
    payment_confirmation_request = instance
    if created:
        assign_perm('moneypool.change_paymentconfirmationrequest', payment_confirmation_request.receiver)
        assign_perm('change_paymentconfirmationrequest', payment_confirmation_request.receiver, payment_confirmation_request)



@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):

    
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(
            instance.request.build_absolute_uri(reverse('password_reset:reset-password-confirm')),
            reset_password_token.key)
    }

    print(context)

    # render email text
    email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        "Password Reset for Equb Finanace",
        email_plaintext_message,
        "noreply@somehost.local",
        [reset_password_token.user.email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()