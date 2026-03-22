from typing import Dict, List, Optional

import requests

from models import NewIdeaData, RoadmapComment, RoadmapIdea


def login(supabase_url: str, anon_key: str, email: str, password: str) -> str:
    response = requests.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_ideas(app_url: str, token: str) -> List[RoadmapIdea]:
    response = requests.get(
        f"{app_url}/api/ideas",
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return [
        RoadmapIdea(
            id=item["id"],
            title=item["title"],
            description=item.get("description", ""),
            category=item.get("category", ""),
            status=item.get("status", ""),
            visibility=item.get("visibility", ""),
            author_email=item.get("author_email", ""),
            upvotes=item.get("upvotes", 0),
            downvotes=item.get("downvotes", 0),
            comment_count=item.get("comment_count", 0),
        )
        for item in response.json()
    ]


def get_comments(app_url: str, token: str, idea_id: str) -> List[RoadmapComment]:
    response = requests.get(
        f"{app_url}/api/ideas/{idea_id}/comments",
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return [
        RoadmapComment(
            id=item["id"],
            body=item["body"],
            author_email=item.get("author_email", ""),
            idea_id=idea_id,
            parent_comment_id=item.get("parent_comment_id"),
            created_at=item.get("created_at", ""),
        )
        for item in response.json()
    ]


def vote(app_url: str, token: str, idea_id: str, vote_type: str) -> None:
    response = requests.post(
        f"{app_url}/api/ideas/{idea_id}/vote",
        json={"type": vote_type},
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()


def add_comment(
    app_url: str,
    token: str,
    idea_id: str,
    body: str,
    parent_comment_id: Optional[str] = None,
) -> None:
    payload: Dict = {"body": body}
    if parent_comment_id:
        payload["parent_comment_id"] = parent_comment_id
    response = requests.post(
        f"{app_url}/api/ideas/{idea_id}/comments",
        json=payload,
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()


def create_idea(app_url: str, token: str, data: NewIdeaData) -> Dict:
    response = requests.post(
        f"{app_url}/api/ideas",
        json={"title": data.title, "description": data.description, "category": data.category},
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
