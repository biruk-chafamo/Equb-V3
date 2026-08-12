from django.db import models
from django.utils import timezone

from .bidding import Bid
from .equb import Equb
from .identity import User
from .requests import assign_notification_perm


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
            self.delete()  # delete notification if read by receiver
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
            cls.objects.create(
                equb=equb, receiver=member, 
                round=equb.balance_manager.finished_rounds + 1)


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

class NewPaymentConfirmationRequestNotification(Notification):
    @classmethod
    def notify(cls, payment_confirmation_request):
        cls.objects.create(
            equb=payment_confirmation_request.equb, 
            receiver=payment_confirmation_request.receiver
        )


class OutBidNotification(Notification):
    """
    instantiated after one bid outbids another
    """
    round = models.IntegerField(default=0)
    previous_highest_bid = models.ForeignKey(to=Bid, on_delete=models.CASCADE, null=True, related_name='+')
    new_highest_bid = models.ForeignKey(to=Bid, on_delete=models.CASCADE, related_name='+')

    @classmethod
    def notify(cls, equb, previous_highest_bid, new_highest_bid):
        for member in equb.members.all():
            cls.objects.create(
                equb=equb, previous_highest_bid=previous_highest_bid, 
                new_highest_bid=new_highest_bid, receiver=member, 
                round=equb.balance_manager.finished_rounds + 1
            )
