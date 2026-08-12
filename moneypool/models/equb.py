import datetime

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from ..domain import settlement
from .identity import User


class Equb(models.Model):
    name = models.CharField(max_length=150, unique=True)
    amount = models.DecimalField(max_digits=13, decimal_places=2, blank=False, validators=[MinValueValidator(1.00)])
    members = models.ManyToManyField(to=User, through='EqubMembership', related_name='joined_equbs')
    max_members = models.IntegerField(
        validators=[MinValueValidator(limit_value=2, message='at least two members required')]
    )
    cycle = models.DurationField(default=datetime.timedelta(days=1))
    creator = models.ForeignKey(to=User, on_delete=models.SET_NULL, null=True, related_name='created_equbs')
    creation_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_private = models.BooleanField(default=False)  # if true, creator's friends are notified of the equb's creation
    is_active = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_in_payment_stage = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creation_date']

    def __str__(self):
        return f"{self.creator.username  if self.creator else 'deleted user'}'s {self.name}"

    def activate(self) -> None:
        from .requests import EqubInviteRequest, EqubJoinRequest

        self.is_active = True
        self.save()

        # freezing all requests or invitations to join this equb
        map(lambda req: req.freeze_instance(), EqubInviteRequest.objects.filter(equb=self))
        map(lambda req: req.freeze_instance(), EqubJoinRequest.objects.filter(equb=self))
        
        # expiring all requests or invitations to join this equb
        EqubInviteRequest.objects.filter(equb=self).update(is_expired=True)
        EqubJoinRequest.objects.filter(equb=self).update(is_expired=True)

        

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class EqubMembership(models.Model):
    member = models.ForeignKey(to=User, on_delete=models.CASCADE)
    equb = models.ForeignKey(to=Equb, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_joined']

class Win(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    round = models.PositiveIntegerField()
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-round']

    def __str__(self):
        return str(self.user.username) + ' won round ' + str(self.round)

class BalanceManager(models.Model):
    equb = models.OneToOneField(to=Equb, on_delete=models.CASCADE, related_name='balance_manager')
    received = models.ManyToManyField(User, blank=True, related_name='received_equb_managers')
    start_date = models.DateTimeField(null=True, blank=True)
    current_round_start_date = models.DateTimeField(null=True, blank=True)
    last_managed = models.DateTimeField(null=True, blank=True)
    finished_rounds = models.IntegerField(blank=True, default=0)
    wins = models.ManyToManyField(Win, blank=True, related_name='winning_equb_managers')

    def __str__(self):
        return str(self.equb.name) + ' balance manager'

    def activate(self):
        start_date = timezone.now()
        self.start_date = start_date
        self.save()

    def check_received(self, user):
        received = self.received.all()
        if user in received:
            return True
        else:
            return False

    def percent_completed(self):
        return round((self.finished_rounds / self.equb.max_members) * 100, 2) 
    
    def percent_joined(self):
        return round((self.equb.members.all().count() / self.equb.max_members) * 100, 2) 

    def current_spots(self):
        return self.equb.max_members - self.equb.members.all().count()

    def current_round(self):
        return min(self.finished_rounds + 1, self.equb.max_members)

    def time_left_till_next_round(self):  # time till next round
        if self.current_round_start_date is None:
            time_delta_dict = {
                "days": 0,
                "hours": 0,
                "minutes": 0,
                "seconds": 0
            }
        else: 
            next_round_time = self.current_round_start_date + self.equb.cycle
            delta = next_round_time - timezone.now()
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            seconds = delta.seconds

            time_delta_dict = {
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds
            }
        return time_delta_dict

    def rejected_payers(self):
        """
        returns all payment confirmation requests from the previous round that have been rejected
        """
        from .requests import PaymentConfirmationRequest

        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_rejected=True).select_related('sender')]

    def unconfirmed_payers(self):
        """
        returns all payment confirmation requests from the previous round that haven't yet been accepted
        by that round's winner and haven't been rejected
        """
        from .requests import PaymentConfirmationRequest

        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_accepted=False, is_rejected=False).select_related('sender')]

    def confirmed_payers(self):
        """
        inverse of self.unconfirmed_payers
        """
        from .requests import PaymentConfirmationRequest

        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_accepted=True).select_related('sender')]

    def unpaid_members(self):
        """
        returns all members who haven't yet sent a payment confirmation request to the current round's winner
        """
        from .requests import PaymentConfirmationRequest

        all_members = self.equb.members.all()
        payment_confirmation_requests = PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_rejected=False)
        payment_confirmation_requested_members = User.objects.filter(pk__in=payment_confirmation_requests.values_list('sender', flat=True))
        if self.latest_winner():
            return all_members.exclude(id=self.latest_winner().id).difference(payment_confirmation_requested_members)
        else:
            return all_members.difference(payment_confirmation_requested_members)

    def payment_collection_dates(self):
        """
        return the date of past wins and the date of the next win
        """
        win_dates = [win.date for win in self.wins.all()]
        if self.current_round_start_date and self.finished_rounds < self.equb.max_members:
            next_win_date = self.current_round_start_date + self.equb.cycle
            win_dates.append(next_win_date)
        return win_dates

    def latest_winner(self):
        return self.wins.first().user if self.wins.exists() else None
    
