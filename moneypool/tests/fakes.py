import datetime

from moneypool.ports.clock import Clock
from moneypool.ports.live_updates import LiveUpdates
from moneypool.ports.scheduler import Scheduler


class RecordingLiveUpdates(LiveUpdates):
    """Records pushed equb ids."""

    def __init__(self):
        self.equb_ids = []

    def equb_updated(self, equb_id) -> None:
        self.equb_ids.append(equb_id)


class RecordingScheduler(Scheduler):
    """Records (equb_name, when) pairs."""

    def __init__(self):
        self.scheduled = []

    def schedule_winner_selection(self, equb_name: str, when: datetime.datetime) -> None:
        self.scheduled.append((equb_name, when))


class FixedClock(Clock):
    """
    Pair with RecordingScheduler to assert the exact next-round deadline
    """

    def __init__(self, fixed_now: datetime.datetime):
        self.fixed_now = fixed_now

    def now(self) -> datetime.datetime:
        return self.fixed_now
