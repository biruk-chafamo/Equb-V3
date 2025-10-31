import datetime
from typing import Protocol


class Scheduler(Protocol):
    def schedule_winner_selection(self, equb_name: str, when: datetime.datetime) -> None: ...
