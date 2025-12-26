import datetime

from .ports.clock import Clock
from .ports.live_updates import LiveUpdates
from .ports.scheduler import Scheduler


class RecordingLiveUpdates(LiveUpdates):
    """Records pushed equb ids."""

    def __init__(self):
        self.equb_ids = []

    def equb_updated(self, equb_id) -> None:
        self.equb_ids.append(equb_id)


