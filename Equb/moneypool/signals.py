from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from django_rest_passwordreset.signals import reset_password_token_created

from guardian.shortcuts import assign_perm

from .models import *

logger = logging.getLogger(__name__)

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
def assign_payment_method_perm(sender, instance, created, **kwargs):
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
        'reset_password_url': f"https://equbfinance.com/#/password_reset/{reset_password_token.key}",
    }

    print(context)

    # render email text
    email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        "Password Reset for Equb Finance",
        email_plaintext_message,
        "noreply@somehost.local",
        [reset_password_token.user.email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()
