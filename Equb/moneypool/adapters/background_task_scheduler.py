import datetime

from ..ports.scheduler import Scheduler
from ..tasks import select_winner_task


class BackgroundTaskScheduler:
    def schedule_winner_selection(self, equb_name: str, when: datetime.datetime) -> None:
        select_winner_task(equb_name, schedule=when)


default_scheduler: Scheduler = BackgroundTaskScheduler()
