import logging

from django.db import transaction
from django.db.models import F
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
        received_ids = set(manager.received.values_list('id', flat=True))
        not_received = [m for m in manager.equb.members.all() if m.id not in received_ids]
        logging.info(f'{len(not_received)} member have not won yet')

        if not_received:
            highest_bidder = highest_bid.bid.user if highest_bid.bid else None
            winning_user = settlement.pick_winner(highest_bidder, not_received)
            win = Win.objects.create(user=winning_user, round=current_round)
            manager.wins.add(win)
            logging.info(f'{win.user.username} won round {current_round}')
            manager.received.add(win.user)
            return win.user


def calculate_winners_award(manager, round):
    equb = manager.equb
    # scanned, not .get(): uses the prefetch cache
    highest_bid = next((h for h in equb.highest_bids.all() if h.round == round), None)
    bid_amount = highest_bid.bid.amount if highest_bid is not None and highest_bid.bid else 0
    # values_list would bypass the prefetch cache
    received_ids = {member.id for member in manager.received.all()}
    not_received_count = sum(1 for m in equb.members.all() if m.id not in received_ids)
    return settlement.compute_award(equb.amount, equb.max_members, bid_amount, not_received_count)


def calculate_losers_deductions(manager, member, round):
    """
    calculates the amount each member must pay in the next round;
    amount of deduction depends on whether the member has received equb in previous rounds.
    """
    equb = manager.equb
    highest_bid = equb.highest_bids.get(round=round)
    bid_amount = highest_bid.bid.amount if highest_bid.bid else 0

    return settlement.compute_deduction(
        equb.amount, equb.max_members, bid_amount,
        in_not_received=not manager.received.filter(pk=member.pk).exists(),
    )


def setup_next_round(
    manager, notifier: Notifier = default_notifier, clock: Clock = default_clock
) -> None:
    # two callers can advance the same round concurrently
    with transaction.atomic():
        locked = manager.__class__.objects.select_for_update().get(pk=manager.pk)

        manager.equb.is_in_payment_stage = False
        manager.equb.save()

        finished_rounds = locked.finished_rounds + 1
        manager.__class__.objects.filter(pk=manager.pk).update(
            finished_rounds=F('finished_rounds') + 1,
            last_managed=timezone.now(),
        )
        manager.finished_rounds = finished_rounds
        manager.refresh_from_db(fields=['last_managed'])

        if manager.equb.max_members == finished_rounds:
            manager.equb.is_completed = True
            manager.equb.end_date = timezone.now()
            manager.equb.save()
        else:
            manager.current_round_start_date = clock.now()
            manager.save()
            HighestBid.objects.create(equb=manager.equb, round=finished_rounds + 1)
            notifier.round_advanced(manager.equb)
