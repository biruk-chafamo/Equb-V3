from django.utils import timezone
from guardian.shortcuts import assign_perm

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


