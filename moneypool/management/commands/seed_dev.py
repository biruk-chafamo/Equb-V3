import datetime
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from ...models import (
    Bid,
    Equb,
    EqubInviteRequest,
    EqubJoinRequest,
    EqubJoinRequestVote,
    FriendRequest,
    PaymentConfirmationRequest,
    PaymentMethod,
    User,
    Win,
)
from ...services.equb_service import add_member, create_equb, place_bid
from ...services.settlement_service import (
    calculate_losers_deductions,
    select_winner,
    setup_next_round,
)

PASSWORD = "equbtest123"
CYCLE = datetime.timedelta(days=7)

SEED_USERS = {
    "alice": ("Alice", "Abebe"),
    "bob": ("Bob", "Bekele"),
    "carol": ("Carol", "Chala"),
    "dave": ("Dave", "Desta"),
    "erin": ("Erin", "Endale"),
    "frank": ("Frank", "Fikru"),
    "grace": ("Grace", "Girma"),
    "heidi": ("Heidi", "Haile"),
}
SEED_USERNAMES = list(SEED_USERS)

PENDING_PARTIAL = "Weekly Savers"
PENDING_JOINABLE = "Coffee Fund"
ACTIVE_MIDWAY = "Rent Circle"
ACTIVE_FINAL_ROUND = "Final Stretch"
ACTIVE_PAYMENT_STAGE = "Payment Due"
COMPLETED = "Holiday Pot"

SEED_EQUB_NAMES = [
    PENDING_PARTIAL,
    PENDING_JOINABLE,
    ACTIVE_MIDWAY,
    ACTIVE_FINAL_ROUND,
    ACTIVE_PAYMENT_STAGE,
    COMPLETED,
]

LOCAL_HOSTS = ("", "localhost", "127.0.0.1", "::1", "pgdb", "db")


class Command(BaseCommand):
    help = "Reset and rebuild reproducible dev users, friendships and equbs."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--list", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        if options["list"]:
            self._describe()
            return

        self._guard(options["force"])

        with transaction.atomic():
            self.stdout.write(f"removed {self._reset()} seed objects")
            if options["reset"]:
                self.stdout.write(self.style.SUCCESS("seed data cleared"))
                return
            self._build()

        self._describe()
        self.stdout.write(self.style.SUCCESS("\nseed complete"))

    def _guard(self, force):
        if force:
            return
        host = (connection.settings_dict.get("HOST") or "").lower()
        if host not in LOCAL_HOSTS:
            raise CommandError(
                f"refusing to seed {connection.settings_dict.get('NAME')!r} on host "
                f"{host!r}; pass --force if you are sure"
            )
        debug = settings.DEBUG
        if isinstance(debug, str):
            debug = debug.strip().lower() not in ("false", "0", "no", "off", "")
        if not debug:
            raise CommandError("refusing to seed with DEBUG=False; pass --force to override")

    def _reset(self):
        count = 0
        users = User.objects.filter(username__in=SEED_USERNAMES)

        equbs = Equb.objects.filter(name__in=SEED_EQUB_NAMES)
        count += equbs.count()
        equbs.delete()

        for model in (FriendRequest, EqubJoinRequest, EqubInviteRequest, PaymentConfirmationRequest):
            qs = model.objects.filter(sender__in=users) | model.objects.filter(receiver__in=users)
            count += qs.count()
            qs.delete()

        for model in (Bid, Win, PaymentMethod):
            qs = model.objects.filter(user__in=users)
            count += qs.count()
            qs.delete()

        # models.deleted_user() passes every field as a lookup, so a 'deleted' row with
        # different names sends it down the create path and trips the unique constraint.
        User.objects.filter(username="deleted").exclude(
            first_name="deleted", last_name="deleted"
        ).update(first_name="deleted", last_name="deleted")

        count += users.count()
        users.delete()
        return count

    def _build(self):
        u = self._users()
        self._friendships(u)
        self._pending_partial(u)
        self._pending_joinable(u)
        self._active_midway(u)
        self._active_final_round(u)
        self._active_payment_stage(u)
        self._completed(u)

    def _users(self):
        return {
            username: User.objects.create_user(
                username=username,
                password=PASSWORD,
                email=f"{username}@example.com",
                first_name=first,
                last_name=last,
                bank_account=Decimal("500.00"),
            )
            for username, (first, last) in SEED_USERS.items()
        }

    def _friendships(self, u):
        for a, b in (("bob", "alice"), ("carol", "alice"), ("dave", "alice"), ("heidi", "bob"), ("erin", "bob")):
            self._accept(FriendRequest.objects.create(sender=u[a], receiver=u[b]))
        FriendRequest.objects.create(sender=u["erin"], receiver=u["alice"])
        FriendRequest.objects.create(sender=u["alice"], receiver=u["frank"])

    def _pending_partial(self, u):
        equb = create_equb(
            creator=u["alice"], name=PENDING_PARTIAL, amount=Decimal("400.00"),
            max_members=4, cycle=CYCLE, is_private=False,
        )
        add_member(equb, u["bob"])
        EqubInviteRequest.objects.create(sender=u["alice"], receiver=u["carol"], equb=equb)
        EqubInviteRequest.objects.create(sender=u["alice"], receiver=u["grace"], equb=equb)
        # erin is trusted by bob but not yet approved; frank is trusted by nobody
        erin_request = EqubJoinRequest.objects.create(sender=u["erin"], receiver=u["alice"], equb=equb)
        EqubJoinRequestVote.objects.create(request=erin_request, voter=u["bob"], approve=True)
        EqubJoinRequest.objects.create(sender=u["frank"], receiver=u["alice"], equb=equb)

    def _pending_joinable(self, u):
        equb = create_equb(
            creator=u["grace"], name=PENDING_JOINABLE, amount=Decimal("250.00"),
            max_members=5, cycle=CYCLE, is_private=False,
        )
        add_member(equb, u["heidi"])
        EqubInviteRequest.objects.create(sender=u["grace"], receiver=u["alice"], equb=equb)

    def _active_midway(self, u):
        equb = self._full_equb(
            ACTIVE_MIDWAY, u["alice"], [u["bob"], u["carol"], u["dave"]], Decimal("800.00")
        )
        self._round(equb, u["bob"], Decimal("0.100"))
        self._round(equb, u["carol"], Decimal("0.080"))
        place_bid(u["dave"], equb, Decimal("0.050"))

    def _active_final_round(self, u):
        equb = self._full_equb(
            ACTIVE_FINAL_ROUND, u["alice"], [u["bob"], u["carol"]], Decimal("300.00")
        )
        self._round(equb, u["bob"], Decimal("0.120"))
        self._round(equb, u["carol"], Decimal("0.090"))

    def _active_payment_stage(self, u):
        equb = self._full_equb(
            ACTIVE_PAYMENT_STAGE, u["alice"], [u["bob"], u["carol"]], Decimal("600.00")
        )
        place_bid(u["bob"], equb, Decimal("0.150"))
        select_winner(equb.balance_manager)
        equb.refresh_from_db()

        manager = equb.balance_manager
        winner = manager.latest_winner()
        round_no = manager.finished_rounds + 1
        for member in equb.members.exclude(pk=winner.pk):
            PaymentConfirmationRequest.objects.create(
                sender=member,
                receiver=winner,
                equb=equb,
                round=round_no,
                payment_method=member.selected_payment_methods.first(),
                amount=calculate_losers_deductions(manager, member, round_no),
                message=f"payment for round {round_no}",
            )

    def _completed(self, u):
        equb = self._full_equb(COMPLETED, u["alice"], [u["bob"], u["carol"]], Decimal("900.00"))
        self._round(equb, u["bob"], Decimal("0.200"))
        self._round(equb, u["carol"], Decimal("0.100"))
        self._round(equb)

    def _full_equb(self, name, creator, others, amount):
        equb = create_equb(
            creator=creator, name=name, amount=amount,
            max_members=len(others) + 1, cycle=CYCLE, is_private=False,
        )
        for member in others:
            add_member(equb, member)
        equb.refresh_from_db()
        return equb

    def _round(self, equb, bidder=None, amount=None):
        if bidder is not None:
            place_bid(bidder, equb, amount)
        manager = equb.balance_manager
        select_winner(manager)
        setup_next_round(manager)
        equb.refresh_from_db()

    def _accept(self, request):
        request.is_accepted = True
        request.save()

    def _describe(self):
        w = self.stdout.write
        w(f"\nusers (password: {PASSWORD})")
        for username, (first, last) in SEED_USERS.items():
            w(f"  {username:8} {first} {last}")
        w("\nfriendships")
        w("  alice <-> bob, carol, dave        bob <-> heidi")
        w("  pending: erin -> alice, alice -> frank")
        w("  not friends: alice & grace")
        w("  bob <-> erin (the trust signal on erin's join request)")
        w("\nequbs")
        rows = [
            (PENDING_PARTIAL, "pending", "alice's, 2/4; invites to carol+grace, join reqs from erin+frank"),
            (PENDING_JOINABLE, "pending", "grace's, 2/5; alice has an invite to accept"),
            (ACTIVE_MIDWAY, "active", "4 members, round 3/4, open bid"),
            (ACTIVE_FINAL_ROUND, "active", "3 members, round 3/3, bidding disabled"),
            (ACTIVE_PAYMENT_STAGE, "payment", "3 members, winner picked, confirmations open"),
            (COMPLETED, "completed", "3 members, all rounds finished"),
        ]
        for name, state, note in rows:
            w(f"  {name:16} {state:10} {note}")
