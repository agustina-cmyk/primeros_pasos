import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from models import AgentMemoryState, TicketStateSnapshot


class AgentMemory:
    def __init__(self, state_path: str) -> None:
        self.path = Path(state_path)

    def load(self) -> AgentMemoryState:
        if not self.path.exists():
            return AgentMemoryState.empty()

        with self.path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        tickets_raw = data.get("tickets", {})
        allowed_fields = {field.name for field in fields(TicketStateSnapshot)}
        tickets: Dict[str, TicketStateSnapshot] = {}
        for key, value in tickets_raw.items():
            payload = {k: v for k, v in value.items() if k in allowed_fields}
            tickets[key] = TicketStateSnapshot(**payload)

        return AgentMemoryState(
            tickets=tickets,
            last_run_at=data.get("last_run_at"),
        )

    def save(self, state: AgentMemoryState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state.last_run_at = datetime.now(timezone.utc).isoformat()
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh, ensure_ascii=True, indent=2)
