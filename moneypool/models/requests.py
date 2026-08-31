from django.db import models
from django.utils import timezone

from rest_framework import serializers
from guardian.shortcuts import assign_perm

from .equb import Equb
from .identity import PaymentMethod, User, deleted_user


class Request(models.Model):
    sender = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='sent_%(class)ss')
    receiver = models.ForeignKey(to=User, on_delete=models.SET(deleted_user), related_name='received_%(class)ss')
    creation_date = models.DateTimeField(default=timezone.now)
    is_accepted = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    def accept(self):
        raise NotImplementedError('must implement accept method for request subclass')

    def reject(self):
        pass

    def save(self, *args, **kwargs):
        if self.pk: # if instance exists
            stored = self.__class__.objects.values('is_accepted', 'is_rejected', 'is_expired').get(pk=self.pk)
            addressed_before = stored['is_accepted'] or stored['is_rejected'] or stored['is_expired']
            if self.is_accepted and not addressed_before:
                super().save(*args, **kwargs)
                self.accept()
            elif self.is_rejected and not addressed_before:
                super().save(*args, **kwargs)
                self.reject()
            else:
                raise serializers.ValidationError({"is_accepted": "You cannot update this request"})
        else:
            super().save(*args, **kwargs)

class EqubJoinRequest(Request):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='%(class)ss')

    def accept(self):
        if not self.equb.is_active and self.sender:
            from ..services.equb_service import add_member
            add_member(self.equb, self.sender)
        else:
            raise serializers.ValidationError({"is_accepted": f"{self.equb.name} has already began"})


class EqubJoinRequestVote(models.Model):
    request = models.ForeignKey(to=EqubJoinRequest, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='equb_join_request_votes')
    approve = models.BooleanField()
    creation_date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-creation_date']
        constraints = [
            models.UniqueConstraint(fields=['request', 'voter'], name='unique_join_request_vote'),
        ]

    def __str__(self):
        return f"{self.voter.username} {'approved' if self.approve else 'declined'} join request {self.request_id}"


class EqubInviteRequest(Request):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='%(class)ss')

    def accept(self):
        if not self.equb.is_active:
            from ..services.equb_service import add_member 
            add_member(self.equb, self.receiver)
        else:
            raise serializers.ValidationError({"is_accepted": f"{self.equb.name} has already began"})


class PaymentConfirmationRequest(Request):
    """
    When a winner is selected at the end of each round, other members 
    must send payment confirmation requests to the winner. The winner 
    must confirm that they have received the payment by accepting the
    request. This is to ensure that the winner actually receives the
    payment. 
    """
    amount = models.DecimalField(max_digits=13, decimal_places=2, default=0.00)
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='sent_%(class)ss')
    payment_method = models.ForeignKey(to=PaymentMethod, on_delete=models.CASCADE, null=True, related_name='%(class)ss')
    round = models.IntegerField(default=1)
    message = models.TextField(blank=True)

    class Meta(Request.Meta):
        indexes = [
            models.Index(fields=['equb', 'round']),
        ]

    def accept(self):
        """
        If all loosers' payments have been confirmed by the winner,
        the next round is ready to be set up.
        """
        if len(self.equb.balance_manager.confirmed_payers()) == self.equb.members.count() - 1:
            from ..services.settlement_service import setup_next_round
            setup_next_round(self.equb.balance_manager)

class FriendRequest(Request):

    def accept(self):
        self.receiver.friends.add(self.sender)


def assign_notification_perm(sender, instance, created, **kwargs):
    if created:
        perm = sender._meta.model_name
        assign_perm(f'moneypool.change_{sender._meta.model_name}', instance.receiver)
        assign_perm(f'change_{sender._meta.model_name}', instance.receiver, instance)


def grant_change_permission(model_class, instances):
    """Give each instance's receiver change permission on that instance."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from guardian.utils import get_user_obj_perms_model

    instances = list(instances)
    if not instances:
        return

    content_type = ContentType.objects.get_for_model(model_class)
    permission = Permission.objects.get(
        content_type=content_type,
        codename=f'change_{model_class._meta.model_name}',
    )

    user_permissions = User.user_permissions.through
    user_permissions.objects.bulk_create(
        [
            user_permissions(user_id=receiver_id, permission_id=permission.pk)
            for receiver_id in {instance.receiver_id for instance in instances}
        ],
        ignore_conflicts=True,
    )

    object_permission = get_user_obj_perms_model(model_class)
    if not object_permission.objects.is_generic():
        raise NotImplementedError(
            'grant_change_permission expects guardian\'s generic object permission model'
        )

    object_permission.objects.bulk_create(
        [
            object_permission(
                permission=permission,
                content_type=content_type,
                object_pk=str(instance.pk),
                user_id=instance.receiver_id,
            )
            for instance in instances
        ],
        ignore_conflicts=True,
    )
