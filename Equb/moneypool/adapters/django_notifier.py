from ..models import (
    NewEqubNotification,
    NewMemberNotification,
    NewPaymentConfirmationRequestNotification,
    NewRoundNotification,
    OutBidNotification,
)
from ..ports.clock import Clock
from ..ports.live_updates import LiveUpdates
from ..ports.notifier import Notifier
from ..ports.scheduler import Scheduler
from .background_task_scheduler import default_scheduler
from .channels_live_updates import default_live_updates
from .system_clock import default_clock


class DjangoNotifier:
    def __init__(
        self,
        clock: Clock = default_clock,
        live_updates: LiveUpdates = default_live_updates,
        scheduler: Scheduler = default_scheduler,
    ):
        self.clock = clock
        self.live_updates = live_updates
        self.scheduler = scheduler

    def equb_created(self, equb):
        NewEqubNotification.notify(equb=equb)

