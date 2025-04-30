from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.dispatch import Signal

import datetime
import random
import logging
import decimal
import pytz

from rest_framework import serializers
from guardian.shortcuts import assign_perm

class User(AbstractUser):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bank_account = models.DecimalField(max_digits=13, decimal_places=2, default=0.00)
    friends = models.ManyToManyField("self", through='Friendship', blank=True)
    payment_methods = models.ManyToManyField('PaymentMethod', blank=True, related_name='users')
    stripe_account_id = models.CharField(max_length=150, blank=True)
    score = models.DecimalField(
        max_digits=3, decimal_places=2, default=4, 
        validators=[MinValueValidator(0.01), MaxValueValidator(5.00)]
    )

    def delete(self, *args, **kwargs):
        for equb in (self.joined_equbs.all() | self.created_equbs.all()):
            if equb.is_active and not equb.is_completed:
                raise NotImplementedError("Cannot delete user that is part of active equbs.") # Todo Change error type
        super().delete()

    def remove_friend(self, friend: 'User') -> None:
        self.friends.remove(friend)

    class Meta:
        indexes = [
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
            models.Index(fields=['username']),
        ]

class ServiceChoices(models.TextChoices):
        VENMO = 'Venmo', 'Venmo'
        PAYPAL = 'PayPal', 'PayPal'
        CASHAPP = 'CashApp', 'CashApp'
        CASH = 'Cash', 'Cash'
        ZELLE = 'Zelle', 'Zelle'
        BANK_TRANSFER = 'Bank Transfer', 'Bank Transfer'

class PaymentMethod(models.Model):
    service = models.CharField(max_length=150, choices=ServiceChoices.choices)
    detail = models.CharField(max_length=150, default='')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='selected_payment_methods')

    def __str__(self):
        return f"{self.get_service_display()}: {self.detail}"
    
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=['user', 'service', 'detail'], name='unique_user_service')
    #     ]

class Friendship(models.Model):
    friend = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='friendships')
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_joined']

    # TODO removing friend


def deleted_user():
    return User.objects.get_or_create(username='deleted', first_name='deleted', last_name='deleted')[0]


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

new_round_signal = Signal()

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
            next_round_time = self.current_round_start_date.replace(tzinfo=pytz.UTC) + self.equb.cycle
            delta = next_round_time - datetime.datetime.now(tz=pytz.UTC)
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
        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_rejected=True).select_related('sender')]

    def unconfirmed_payers(self):
        """
        returns all payment confirmation requests from the previous round that haven't yet been accepted 
        by that round's winner and haven't been rejected
        """
        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_accepted=False, is_rejected=False).select_related('sender')]
    
    def confirmed_payers(self):
        """
        inverse of self.unconfirmed_payers
        """
        return [conf_request.sender for conf_request in PaymentConfirmationRequest.objects.filter(equb=self.equb, round=self.current_round(), is_accepted=True).select_related('sender')]
    
    def unpaid_members(self):
        """
        returns all members who haven't yet sent a payment confirmation request to the current round's winner
        """
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
            next_win_date = self.current_round_start_date.replace(tzinfo=pytz.UTC) + self.equb.cycle
            win_dates.append(next_win_date)
        return win_dates

    def latest_winner(self):
        return self.wins.first().user if self.wins.exists() else None
    
    def select_winner(self):
        """
        Selects highest bidder as winner.
        If there is no bid, winner is randomly selected from
        those who haven't received their equbs yet
        """
        with transaction.atomic(): # to ensure payment stage is not started without a winner
            self.equb.is_in_payment_stage = True
            self.equb.save()

            current_round = self.finished_rounds + 1
            highest_bid = self.equb.highest_bids.get(round=current_round)
            all_members = self.equb.members.all()
            received = self.received.all()
            not_received = all_members.difference(received)
            logging.info(f'{not_received.count()} member have not won yet')
            
            if not_received:
                win = Win.objects.create(
                    user=highest_bid.bid.user if highest_bid.bid else random.choice(not_received), 
                    round=current_round
                )
                self.wins.add(win)
                logging.info(f'{win.user.username} won round {current_round}')
                self.received.add(win.user)
                return win.user
        
    def calculate_winners_award(self, round):
        equb = self.equb
        highest_bid = equb.highest_bids.get(round=round) 
        if highest_bid.bid:
            bid_amount = highest_bid.bid.amount
        else:
            bid_amount = 0
        
        deductible_portion = equb.amount * decimal.Decimal(1 - 1 / equb.max_members)
        deducted_award = deductible_portion * decimal.Decimal(1 - bid_amount)
        non_deductible_award = equb.amount / equb.max_members
        award = non_deductible_award + deducted_award
        
        return award
    
    def calculate_losers_deductions(self, member, round):
        """
        calculates the amount each member must pay in the next round; 
        amount of deduction depends on whether the member has received equb in previous rounds.
        """
        equb = self.equb
        all_members = equb.members.all()
        not_received = all_members.difference(self.received.all())
        max_members = equb.max_members
        highest_bid = equb.highest_bids.get(round=round) 

        if highest_bid.bid:
            bid_amount = highest_bid.bid.amount
        else:
            bid_amount = 0

        # winner's contribution = 0 if there is no bid
        winners_contribution = equb.amount * decimal.Decimal((1 - 1 / max_members)) * decimal.Decimal((bid_amount))

        if member in not_received: 
            return (equb.amount / max_members) - (winners_contribution / not_received.count())
        elif member in self.received.all():
            return equb.amount / max_members
        else: # winner
            return 0
        

    def update_winner_account(self):
        """
        adds the total value of equb to winners account minus the percentage
        of this amount equal to what was bid
        """
        winner = self.select_winner()
        award = self.calculate_winners_award(self.finished_rounds + 1)
        if winner:
            logging.info(f'award {award} bank account {winner.bank_account}')
            winner.bank_account += award  # amount = equb value if highest bid = 0
            winner.save()
            logging.info(f'{winner.username} award {award}')

    def collect_money(self):
        """
        deducts the correct amount from equb members.
        Distributes the highest bid to those who haven't
        received their equbs yet. Those who received their
        equb won't benefit from the bid.
        """

        current_round = self.finished_rounds + 1
        for member in self.equb.members.all(): 
            member.bank_account -= self.calculate_losers_deductions(member, current_round)
            member.save()
            

    def setup_next_round(self):
        self.equb.is_in_payment_stage = False
        self.equb.save()
        
        self.finished_rounds += 1
        self.last_managed = timezone.now()
        self.save()
        
        if self.equb.max_members == self.finished_rounds:
            self.equb.is_completed = True  
            self.equb.end_date = timezone.now()          
            self.equb.save()
        else:
            new_round_signal.send(sender=self.__class__, instance = self, equb=self.equb)


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
        if not highest_bid.bid or (highest_bid.bid and self.amount > highest_bid.bid.amount):
            return True
        else:
            return False

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
            addressed_before = self.__class__.objects.get(pk=self.pk).is_accepted or self.__class__.objects.get(pk=self.pk).is_rejected or self.__class__.objects.get(pk=self.pk).is_expired
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

    def accept(self):
        """
        If all loosers' payments have been confirmed by the winner,
        the next round is ready to be set up.
        """
        if len(self.equb.balance_manager.confirmed_payers()) == self.equb.members.count() - 1:
            self.equb.balance_manager.setup_next_round()

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

