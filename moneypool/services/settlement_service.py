import logging

from django.db import transaction
from django.utils import timezone

from ..adapters.django_notifier import default_notifier
from ..adapters.system_clock import default_clock
from ..domain import settlement
from ..models import HighestBid, Win
from ..ports.clock import Clock
from ..ports.notifier import Notifier


def select_winner(manager):
    """
    Selects highest bidder as winner.
    If there is no bid, winner is randomly selected from
    those who haven't received their equbs yet
    """
    with transaction.atomic():  # to ensure payment stage is not started without a winner
        manager.equb.is_in_payment_stage = True
        manager.equb.save()

        current_round = manager.finished_rounds + 1
        highest_bid = manager.equb.highest_bids.get(round=current_round)
        all_members = manager.equb.members.all()
        received = manager.received.all()
        not_received = all_members.difference(received)
        logging.info(f'{not_received.count()} member have not won yet')

        if not_received:
            highest_bidder = highest_bid.bid.user if highest_bid.bid else None
            winning_user = settlement.pick_winner(highest_bidder, list(not_received))
            win = Win.objects.create(user=winning_user, round=current_round)
            manager.wins.add(win)
            logging.info(f'{win.user.username} won round {current_round}')
            manager.received.add(win.user)
            return win.user


def setup_next_round(
    manager, notifier: Notifier = default_notifier, clock: Clock = default_clock
) -> None:
    manager.equb.is_in_payment_stage = False
    manager.equb.save()

    manager.finished_rounds += 1
    manager.last_managed = timezone.now()
    manager.save()

    if manager.equb.max_members == manager.finished_rounds:
        manager.equb.is_completed = True
        manager.equb.end_date = timezone.now()
        manager.equb.save()
    else:
        manager.current_round_start_date = clock.now()
        manager.save()
        HighestBid.objects.create(equb=manager.equb, round=manager.finished_rounds + 1)
        notifier.round_advanced(manager.equb)
