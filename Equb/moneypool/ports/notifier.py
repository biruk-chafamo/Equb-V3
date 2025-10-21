from typing import Any, Optional, Protocol


class Notifier(Protocol):
    def equb_created(self, equb: Any) -> None: ...

