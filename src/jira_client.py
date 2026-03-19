from dataclasses import dataclass
from typing import List, Optional

import requests
from requests.auth import HTTPBasicAuth


@dataclass(frozen=True)
class JiraTicket:
    key: str
    summary: str
    labels: List[str]
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


@dataclass(frozen=True)
class JiraBoardContext:
    board_id: str
    board_name: str
    project_key: Optional[str]
    project_name: Optional[str]


class JiraClient:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        cloud_id: str = "",
        section_field: str = "",
        criticality_field: str = "",
        environment_field: str = "environment",
        type_field: str = "issuetype",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cloud_id = cloud_id.strip()
        self.section_field = section_field.strip()
        self.criticality_field = criticality_field.strip()
        self.environment_field = environment_field.strip() or "environment"
        self.type_field = type_field.strip() or "issuetype"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(email, api_token)
        self.session.headers.update({"Accept": "application/json"})

    def search_tickets(self, jql: str, max_results: int = 100) -> List[JiraTicket]:
        endpoint = self._build_url("/rest/api/3/search/jql")
        tickets: List[JiraTicket] = []
        page_size = min(max_results, 100)
        request_fields = [
            "summary",
            "labels",
            "status",
            "assignee",
            "reporter",
            "created",
            "updated",
            "description",
            "priority",
            "environment",
            "issuetype",
        ]
        for field_name in [self.section_field, self.criticality_field, self.environment_field, self.type_field]:
            if field_name and field_name not in request_fields:
                request_fields.append(field_name)

        next_page_token: Optional[str] = None
        while len(tickets) < max_results:
            payload: dict = {
                "jql": jql,
                "maxResults": page_size,
                "fields": request_fields,
                "expand": "changelog",
            }
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            resp = self.session.post(endpoint, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            issues = data.get("issues", [])
            if not issues:
                break

            for issue in issues:
                issue_fields = issue.get("fields", {})
                key = issue.get("key", "")
                assignee = issue_fields.get("assignee") or {}
                reporter = issue_fields.get("reporter") or {}
                tickets.append(
                    JiraTicket(
                        key=key,
                        summary=issue_fields.get("summary", ""),
                        labels=[label.lower() for label in issue_fields.get("labels", [])],
                        status=(issue_fields.get("status") or {}).get("name", ""),
                        status_category=((issue_fields.get("status") or {}).get("statusCategory") or {}).get("name", ""),
                        assignee=assignee.get("displayName"),
                        reporter=reporter.get("displayName"),
                        created=issue_fields.get("created", ""),
                        updated=issue_fields.get("updated", ""),
                        last_status_change_at=self._last_status_change_at(issue) or issue_fields.get("updated", ""),
                        description=self._adf_to_text(issue_fields.get("description")),
                        section=self._field_to_text(issue_fields.get(self.section_field)) if self.section_field else "",
                        criticality=self._field_to_text(issue_fields.get(self.criticality_field)) if self.criticality_field else self._field_to_text(issue_fields.get("priority")),
                        environment=self._field_to_text(issue_fields.get(self.environment_field)),
                        ticket_type=self._field_to_text(issue_fields.get(self.type_field)),
                        url=f"{self.base_url}/browse/{key}",
                    )
                )
                if len(tickets) >= max_results:
                    break

            if data.get("isLast", True):
                break
            next_page_token = data.get("nextPageToken")

        return tickets

    def search_finalized_tickets(self, base_jql: str, lookback_days: int = 90, max_results: int = 200) -> List[JiraTicket]:
        """Trae tickets finalizados en los últimos N días, útil para análisis de recurrencia."""
        jql = (
            f"({base_jql}) AND statusCategory = Done "
            f"AND updated >= -{lookback_days}d ORDER BY updated DESC"
        )
        return self.search_tickets(jql=jql, max_results=max_results)

    def get_board_context(self, board_id: str) -> JiraBoardContext:
        endpoint = self._build_url(f"/rest/agile/1.0/board/{board_id}")
        resp = self.session.get(endpoint, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        location = data.get("location") or {}
        return JiraBoardContext(
            board_id=str(data.get("id") or board_id),
            board_name=str(data.get("name") or f"Board {board_id}"),
            project_key=location.get("projectKey"),
            project_name=location.get("projectName"),
        )

    def _adf_to_text(self, adf_node: Optional[dict]) -> str:
        if not adf_node:
            return ""

        out: List[str] = []

        def visit(node: object) -> None:
            if isinstance(node, dict):
                if node.get("type") == "text":
                    text = node.get("text")
                    if isinstance(text, str):
                        out.append(text)
                for child in node.get("content", []) or []:
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(adf_node)
        collapsed = " ".join(" ".join(out).split())
        return collapsed.strip()

    def _build_url(self, path: str) -> str:
        if self.cloud_id:
            return f"https://api.atlassian.com/ex/jira/{self.cloud_id}{path}"
        return f"{self.base_url}{path}"

    def _last_status_change_at(self, issue: dict) -> str:
        changelog = issue.get("changelog") or {}
        histories = changelog.get("histories") or []
        latest = ""
        for history in histories:
            for item in history.get("items") or []:
                if item.get("field") == "status":
                    created = history.get("created", "")
                    if created and created > latest:
                        latest = created
        return latest

    def _field_to_text(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            for key in ("value", "name", "displayName"):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    return item.strip()
            return ""
        if isinstance(value, list):
            parts = [self._field_to_text(item) for item in value]
            return ", ".join(part for part in parts if part)
        return str(value).strip()
