from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TicketFacts:
    key: str
    vertical: str
    summary: str
    status: str
    status_category: str
    assignee: Optional[str]
    reporter: Optional[str]
    created: str
    updated: str
    last_status_change_at: str
    description: str
    section: str
    criticality: str
    environment: str
    ticket_type: str
    url: str
    labels: List[str]
    created_today: bool
    status_changed_today: bool
    finalized_today: bool
    is_stale: bool
    changed_since_last_run: bool
    status_changed: bool
    assignee_changed: bool


@dataclass(frozen=True)
class AgentAction:
    action_type: str
    vertical: str
    reason: str
    tickets: List[TicketFacts]


@dataclass(frozen=True)
class VerticalPlan:
    vertical: str
    actions: List[AgentAction]


@dataclass
class TicketStateSnapshot:
    key: str
    vertical: str
    status: str
    assignee: Optional[str]
    updated: str
    last_status_change_at: str = ""
    notified_reasons: List[str] = field(default_factory=list)


@dataclass
class AgentMemoryState:
    tickets: Dict[str, TicketStateSnapshot]
    last_run_at: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "last_run_at": self.last_run_at,
            "tickets": {key: asdict(snapshot) for key, snapshot in self.tickets.items()},
        }

    @classmethod
    def empty(cls) -> "AgentMemoryState":
        return cls(tickets={})
