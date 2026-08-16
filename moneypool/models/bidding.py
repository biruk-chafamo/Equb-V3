from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from ..domain import settlement
from .equb import Equb
from .identity import User


class Bid(models.Model):
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='sent_bids', null=True)
    amount = models.DecimalField(
        max_digits=5, decimal_places=3, default=0, 
        validators=[MinValueValidator(0.001), MaxValueValidator(1.000)]
    )
    round = models.PositiveIntegerField()
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-round', '-amount']
        indexes = [
            models.Index(fields=['equb', 'round']),
        ]

    def __str__(self):
        return str(self.user.username) + ' to ' + str(self.equb.name) + ' round ' + str(self.round) + ' ' + str(self.amount)

    def get_round(self):
        return str(self.round)

    @classmethod
    def new_bid(cls, user, equb, bid_amount):
        current_round = equb.balance_manager.finished_rounds + 1
        bid = Bid(equb=equb, user=user, round=current_round, amount=bid_amount)
        bid.save()
        return bid

    def is_highest_bid(self):
        highest_bid = HighestBid.objects.get(equb=self.equb, round=self.round)
        current_highest_amount = highest_bid.bid.amount if highest_bid.bid else None
        return settlement.is_higher_bid(self.amount, current_highest_amount)

    def make_highest_bid(self):
        highest_bid = HighestBid.objects.get(equb=self.equb, round=self.round)
        highest_bid.bid = self
        highest_bid.save()


class HighestBid(models.Model):

    """
    highest bid object is always created whenever an equb is created in create_equb view.
    However the bid attribute is set to null.
    """

    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE, related_name='highest_bids')
    bid = models.OneToOneField(to=Bid, on_delete=models.SET_NULL, null=True, blank=True)
    round = models.PositiveIntegerField()
    winner = models.ForeignKey(to=User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['equb', 'round'], name='unique_equb_round_highest_bid'),
        ]
