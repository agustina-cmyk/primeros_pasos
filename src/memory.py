import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from models import AgentMemoryState, RoadmapMemoryState, TicketStateSnapshot, WeeklyTicketSnapshot


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

        roadmap_raw = data.get("roadmap", {})
        roadmap = RoadmapMemoryState(
            voted_idea_ids=roadmap_raw.get("voted_idea_ids", {}),
            commented_idea_ids=roadmap_raw.get("commented_idea_ids", []),
            replied_comment_ids=roadmap_raw.get("replied_comment_ids", []),
            created_idea_ids=roadmap_raw.get("created_idea_ids", []),
            last_run_at=roadmap_raw.get("last_run_at"),
        )

        weekly_buffer_raw = data.get("weekly_buffer", {})
        weekly_buffer: Dict[str, Dict[str, WeeklyTicketSnapshot]] = {}
        snap_fields = {f.name for f in fields(WeeklyTicketSnapshot)}
        for date_str, day_data in weekly_buffer_raw.items():
            weekly_buffer[date_str] = {
                key: WeeklyTicketSnapshot(**{k: v for k, v in snap.items() if k in snap_fields})
                for key, snap in day_data.items()
            }

        return AgentMemoryState(
            tickets=tickets,
            last_run_at=data.get("last_run_at"),
            last_message_sent_at=data.get("last_message_sent_at"),
            roadmap=roadmap,
            weekly_buffer=weekly_buffer,
            weekly_last_run_at=data.get("weekly_last_run_at"),
        )

    def save(self, state: AgentMemoryState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state.last_run_at = datetime.now(timezone.utc).isoformat()
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh, ensure_ascii=True, indent=2)
