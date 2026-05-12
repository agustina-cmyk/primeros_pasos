import pytest
from unittest.mock import MagicMock, patch

from models import TicketFacts


def _make_facts(**overrides) -> TicketFacts:
    """Helper para construir TicketFacts con defaults razonables."""
    defaults = dict(
        key="PS-1",
        vertical="payments",
        summary="Test",
        status="In Progress",
        status_category="In Progress",
        assignee=None,
        reporter=None,
        created="2026-04-15T10:00:00.000+0000",
        updated="2026-04-15T10:00:00.000+0000",
        last_status_change_at="2026-04-15T10:00:00.000+0000",
        description="",
        section="",
        criticality="High",
        environment="",
        ticket_type="Bug",
        url="https://example.atlassian.net/browse/PS-1",
        labels=[],
        created_today=False,
        finalized_today=False,
        created_since_last_message=False,
        finalized_since_last_message=False,
        is_stale=False,
        days_without_status_change=0,
        status_changed=False,
        assignee_changed=False,
    )
    defaults.update(overrides)
    return TicketFacts(**defaults)


@pytest.fixture
def mock_sync_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"synced": 2, "errors": []}
    mock.raise_for_status = MagicMock()
    return mock


def test_sync_with_tickets_returns_synced_count(mock_sync_response):
    facts = [_make_facts(key="PS-1"), _make_facts(key="PS-2", vertical="core")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        result = roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    assert result.synced == 2
    assert result.errors == []
    args, kwargs = mock_post.call_args
    assert args[0] == "https://app.vercel.app/api/support-tickets/sync"
    assert kwargs["headers"]["Authorization"] == "Bearer test-jwt"
    payload = kwargs["json"]
    assert len(payload["tickets"]) == 2
    assert payload["tickets"][0]["key"] == "PS-1"
    assert payload["tickets"][0]["vertical"] == "payments"


def test_resolved_ticket_includes_resolvedAt(mock_sync_response):
    facts = [_make_facts(
        key="PS-CLOSED",
        status="Done",
        status_category="Done",
        last_status_change_at="2026-04-20T15:00:00.000+0000",
    )]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["resolvedAt"] == "2026-04-20T15:00:00.000+0000"


def test_open_ticket_has_null_resolvedAt(mock_sync_response):
    facts = [_make_facts(status_category="In Progress")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["resolvedAt"] is None


def test_empty_criticality_serializes_as_null(mock_sync_response):
    facts = [_make_facts(criticality="")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["criticality"] is None


def test_url_normalized_trailing_slash(mock_sync_response):
    facts = [_make_facts()]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app/",
            token="test-jwt",
            facts=facts,
        )
    assert mock_post.call_args.args[0] == "https://app.vercel.app/api/support-tickets/sync"


def test_partial_errors_returned_in_result():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"synced": 1, "errors": [{"key": "PS-2", "message": "DB busy"}]}
    mock.raise_for_status = MagicMock()
    facts = [_make_facts(key="PS-1"), _make_facts(key="PS-2")]
    with patch("roadmap_support_client.requests.post", return_value=mock):
        import roadmap_support_client
        result = roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    assert result.synced == 1
    assert len(result.errors) == 1
    assert result.errors[0]["key"] == "PS-2"


def test_raise_for_status_propagates_http_errors():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("401 Unauthorized")
    with patch("roadmap_support_client.requests.post", return_value=mock):
        import roadmap_support_client
        with pytest.raises(Exception, match="401"):
            roadmap_support_client.sync_support_tickets(
                app_url="https://app.vercel.app",
                token="bad",
                facts=[_make_facts()],
            )
