import json
from unittest.mock import MagicMock, patch

import pytest

from models import NewIdeaData, RoadmapAction, RoadmapIdea, RoadmapMemoryState


def _make_idea(id="idea-1", title="Test idea", category="Core"):
    return RoadmapIdea(
        id=id, title=title, description="Desc", category=category,
        status="submitted", visibility="public", author_email="other@test.com",
        upvotes=1, downvotes=0, comment_count=0,
    )


def _mock_webhook_response(actions):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"response": json.dumps(actions)}
    return mock


def test_analyze_returns_vote_action():
    actions_json = [{"action": "vote", "idea_id": "idea-1", "vote_type": "like",
                     "comment_body": "Evidencia de PS-123", "comment_id": None, "new_idea": None}]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            finalized_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "vote"
    assert plan.actions[0].vote_type == "like"


def test_analyze_returns_create_idea_action():
    new_idea = {"title": "Nueva idea", "description": "Pain points...", "category": "Core"}
    actions_json = [{"action": "create_idea", "idea_id": None, "vote_type": None,
                     "comment_body": None, "comment_id": None, "new_idea": new_idea}]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            finalized_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert plan.actions[0].action == "create_idea"
    assert plan.actions[0].new_idea.title == "Nueva idea"


def test_analyze_caps_at_five_actions():
    actions_json = [
        {"action": "vote", "idea_id": f"idea-{i}", "vote_type": "like",
         "comment_body": None, "comment_id": None, "new_idea": None}
        for i in range(8)
    ]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            finalized_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea(id=f"idea-{i}") for i in range(8)],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert len(plan.actions) <= 5


def test_analyze_returns_skip_on_empty_response():
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response([])):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            finalized_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert plan.actions == []
    assert plan.skip_reason is not None


def test_analyze_raises_on_invalid_json():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"response": "esto no es json válido {{{"}
    with patch("roadmap_analyzer.requests.post", return_value=mock):
        from roadmap_analyzer import analyze_roadmap
        with pytest.raises(ValueError, match="JSON"):
            analyze_roadmap(
                active_tickets=[],
                finalized_tickets=[],
                recurring_patterns=[],
                ideas=[_make_idea()],
                roadmap_memory=RoadmapMemoryState(),
                webhook_url="https://n8n.test/webhook",
            )
