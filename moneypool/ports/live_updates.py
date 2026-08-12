from typing import Any, Protocol


class LiveUpdates(Protocol):
    def equb_updated(self, equb_id: Any) -> None: ...
