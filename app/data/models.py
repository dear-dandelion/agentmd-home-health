from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UserProfile:
    user_id: int
    name: str
    birth_date: str | None
    gender: str | None
    created_at: str
    updated_at: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def age(self) -> int | None:
        if not self.birth_date:
            return None
        birth = datetime.strptime(self.birth_date, "%Y-%m-%d").date()
        today = datetime.now().date()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


@dataclass
class DialogState:
    state: str = "Idle"
    pending_tool: str | None = None
    pending_intent: str | None = None
    required_params: list[str] = field(default_factory=list)
    collected_params: dict[str, Any] = field(default_factory=dict)
    last_active_at: datetime | None = None


@dataclass
class MessageResult:
    reply_text: str
    card_html: str
    state: DialogState
    result: dict[str, Any] | None = None
