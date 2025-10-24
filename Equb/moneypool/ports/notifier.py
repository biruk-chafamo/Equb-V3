from typing import Any, Optional, Protocol


class Notifier(Protocol):
    def equb_created(self, equb: Any) -> None: ...

    def member_joined(self, equb: Any, new_member: Any) -> None: ...

    def equb_activated(self, equb: Any) -> None: ...

