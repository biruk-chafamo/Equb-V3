from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone
import datetime

from rest_framework import serializers
from guardian.shortcuts import assign_perm


class User(AbstractUser):
    bank_account = models.DecimalField(max_digits=13, decimal_places=2, null=True)
    friends = models.ManyToManyField("self", through='Friendship', blank=True, related_name='friends')

    def delete(self, *args, **kwargs):
        for equb in (self.joined_equbs.all() | self.created_equbs.all()):
            if equb.is_active and not equb.is_completed:
                raise NotImplementedError("Cannot delete user that is part of active equbs.") # Todo Change error type
        super().delete()

    def remove_friend(self, friend: 'User') -> None:
        self.friends.remove(friend)


class Friendship(models.Model):
    friend = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='friendships')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_joined']

    # TODO removing friend


def deleted_user():
    return User.objects.get_or_create(username='deleted')[0]


class Equb(models.Model):
    name = models.CharField(max_length=150, unique=True)
    amount = models.DecimalField(max_digits=13, decimal_places=2)
    members = models.ManyToManyField(to=User, through='EqubMembership', related_name='joined_equbs')
    max_members = models.IntegerField(
        validators=[MinValueValidator(limit_value=2, message='at least two members required')]
    )
    cycle = models.DurationField(default=datetime.timedelta(days=1))
    current_round = models.IntegerField(default=0)
    creator = models.ForeignKey(to=User, on_delete=models.SET_NULL, null=True, related_name='created_equbs')
    creation_date = models.DateTimeField(default=timezone.now)
    is_private = models.BooleanField(default=False)  # if true, creator's friends are notified of the equb's creation
    is_active = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creation_date']

    def __str__(self):
        return f"{self.creator.username}'s {self.name}"

    def activate(self) -> None:
        self.is_active = True
        # freezing all requests or invitations to join this equb
        map(lambda req: req.freeze_instance(), EqubInviteRequest.objects.filter(equb=self))
        map(lambda req: req.freeze_instance(), EqubJoinRequest.objects.filter(equb=self))
        # expiring all requests or invitations to join this equb
        EqubInviteRequest.objects.filter(equb=self).update(is_expired=True)
        EqubJoinRequest.objects.filter(equb=self).update(is_expired=True)
        # TODO activate background task
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class EqubMembership(models.Model):
    member = models.ForeignKey(to=User, on_delete=models.CASCADE)
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_joined']


class Request(models.Model):
    sender = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='sent_%(class)ss')
    receiver = models.ForeignKey(to=User, on_delete=models.SET(deleted_user), related_name='received_%(class)ss')
    creation_date = models.DateTimeField(default=timezone.now)
    is_accepted = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    def accept(self):
        raise NotImplementedError('must implement accept method for request subclass')

    def __reject(self):
        # TODO delete if rejected
        pass

    def save(self, *args, **kwargs):
        if self.pk:
            # ensures existing equb_request is not accepted
            if self.is_accepted and not self.__class__.objects.get(pk=self.pk).is_accepted:
                super().save(*args, **kwargs)
                self.accept()
            else:
                raise serializers.ValidationError({"is_accepted": "You cannot update this request"})
        else:
            super().save(*args, **kwargs)


class EqubJoinRequest(Request):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='%(class)ss')

    def accept(self):
        if not self.equb.is_active and self.sender:
            self.equb.members.add(self.sender)
        else:
            raise serializers.ValidationError({"is_accepted": f"{self.equb.name} has already began"})


class EqubInviteRequest(Request):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='%(class)ss')

    def accept(self):
        # equb must not be active
        if not self.equb.is_active:
            self.equb.members.add(self.receiver)
        else:
            raise serializers.ValidationError({"is_accepted": f"{self.equb.name} has already began"})


class FriendRequest(Request):

    def accept(self):
        self.receiver.friends.add(self.sender)


def assign_notification_perm(sender, instance, created, **kwargs):
    if created:
        perm = sender._meta.model_name
        assign_perm(f'moneypool.change_{sender._meta.model_name}', instance.receiver)
        assign_perm(f'change_{sender._meta.model_name}', instance.receiver, instance)


class Notification(models.Model):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE)
    receiver = models.ForeignKey(to=User, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        models.signals.post_save.connect(receiver=assign_notification_perm, sender=cls)

    @classmethod
    def notify(cls, *args):
        raise NotImplementedError('must implement notify method for a Notification subclass ')

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    def save(self, *args, **kwargs):
        if self.is_read:
            self.delete()  # delete notification if read by everyone in the equb
        else:
            super().save(*args, **kwargs)


class NewRoundNotification(Notification):
    """
    instantiated after equb starts a new round
    """
    round = models.IntegerField(default=0)

    @classmethod
    def notify(cls, equb):
        for member in equb.members.all():
            cls.objects.create(equb=equb, receiver=member, round=equb.current_round)


class NewMemberNotification(Notification):
    """
    instantiated after a user's join request is accepted by creator or user receives and accepts invite from creator
    """
    new_member = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='+')

    @classmethod
    def notify(cls, equb, new_member):
        members = list(equb.members.all())[:-1]
        for member in members:  # includes all members except the latest member
            cls.objects.create(equb=equb, receiver=member, new_member=new_member)


class NewEqubNotification(Notification):
    @classmethod
    def notify(cls, equb):
        if not equb.is_private:
            for friend in equb.creator.friends.all():
                cls.objects.create(equb=equb, receiver=friend)
