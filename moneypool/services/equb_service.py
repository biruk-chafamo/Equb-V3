from django.utils import timezone
from guardian.shortcuts import assign_perm
from rest_framework import serializers

from ..adapters.django_notifier import default_notifier
from ..adapters.system_clock import default_clock
from ..models import BalanceManager, Bid, Equb, HighestBid
from ..ports.clock import Clock
from ..ports.notifier import Notifier


def create_equb(
    creator, name, amount, max_members, cycle, is_private=False, notifier: Notifier = default_notifier
) -> Equb:
    equb = Equb.objects.create(
        creator=creator,
        name=name,
        amount=amount,
        max_members=max_members,
        cycle=cycle,
        is_private=is_private,
    )
    equb.members.add(creator)
    assign_perm("moneypool.change_equb", creator)
    assign_perm("change_equb", creator, equb)

    BalanceManager.objects.create(equb=equb)
    HighestBid.objects.create(equb=equb, round=1)
    notifier.equb_created(equb)
    return equb


def add_member(equb, member, notifier: Notifier = default_notifier, clock: Clock = default_clock) -> None:
    if equb.members.count() >= equb.max_members:
        raise serializers.ValidationError({"equb": f"{equb.name} is already full"})

    equb.members.add(member)
    notifier.member_joined(equb, member)
    if equb.members.count() == equb.max_members:
        equb.activate()
        equb.balance_manager.activate()
        equb.balance_manager.current_round_start_date = clock.now()
        equb.balance_manager.save()
        notifier.equb_activated(equb)


def place_bid(user, equb, amount, notifier: Notifier = default_notifier) -> Bid:
    current_round = equb.balance_manager.finished_rounds + 1
    bid = Bid.objects.create(
        equb=equb, user=user, round=current_round, amount=amount, date=timezone.now()
    )
    if bid.is_highest_bid():
        previous_highest_bid = HighestBid.objects.get(equb=bid.equb, round=bid.round).bid
        notifier.bid_outbid(equb, previous_highest_bid, bid)
        bid.make_highest_bid()
    return bid
