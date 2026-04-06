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
    finalized_today: bool
    created_since_last_message: bool
    finalized_since_last_message: bool
    is_stale: bool
    days_without_status_change: int
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



@dataclass(frozen=True)
class RoadmapIdea:
    id: str
    title: str
    description: str
    category: str
    status: str
    visibility: str
    author_email: str
    upvotes: int
    downvotes: int
    comment_count: int


@dataclass(frozen=True)
class RoadmapComment:
    id: str
    body: str
    author_email: str
    idea_id: str
    parent_comment_id: Optional[str]
    created_at: str


@dataclass(frozen=True)
class NewIdeaData:
    title: str
    description: str
    category: str


@dataclass(frozen=True)
class RoadmapAction:
    action: str           # "vote" | "comment" | "create_idea" | "reply_comment"
    idea_id: Optional[str]
    comment_id: Optional[str]
    vote_type: Optional[str]      # "like" | "dislike"
    comment_body: Optional[str]
    new_idea: Optional[NewIdeaData]


@dataclass(frozen=True)
class RoadmapPlan:
    actions: List[RoadmapAction]
    skip_reason: Optional[str]


@dataclass
class RoadmapMemoryState:
    voted_idea_ids: Dict[str, str] = field(default_factory=dict)  # id → "like"|"dislike"
    commented_idea_ids: List[str] = field(default_factory=list)
    replied_comment_ids: List[str] = field(default_factory=list)
    created_idea_ids: List[str] = field(default_factory=list)
    last_run_at: Optional[str] = None


@dataclass
class AgentMemoryState:
    tickets: Dict[str, TicketStateSnapshot]
    last_run_at: Optional[str] = None
    last_message_sent_at: Optional[str] = None
    roadmap: "RoadmapMemoryState" = field(default_factory=lambda: RoadmapMemoryState())
    last_sent_tickets: Dict[str, "TicketStateSnapshot"] = field(default_factory=dict)
    weekly_last_run_at: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "last_run_at": self.last_run_at,
            "last_message_sent_at": self.last_message_sent_at,
            "tickets": {key: asdict(snapshot) for key, snapshot in self.tickets.items()},
            "last_sent_tickets": {key: asdict(snapshot) for key, snapshot in self.last_sent_tickets.items()},
            "roadmap": {
                "last_run_at": self.roadmap.last_run_at,
                "voted_idea_ids": self.roadmap.voted_idea_ids,
                "commented_idea_ids": self.roadmap.commented_idea_ids,
                "replied_comment_ids": self.roadmap.replied_comment_ids,
                "created_idea_ids": self.roadmap.created_idea_ids,
            },
            "weekly_last_run_at": self.weekly_last_run_at,
        }

    @classmethod
    def empty(cls) -> "AgentMemoryState":
        return cls(tickets={}, roadmap=RoadmapMemoryState())
