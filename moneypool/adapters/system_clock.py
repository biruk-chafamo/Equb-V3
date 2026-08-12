import datetime

from django.utils import timezone

from ..ports.clock import Clock


class SystemClock:
    def now(self) -> datetime.datetime:
        return timezone.now()


default_clock: Clock = SystemClock()
