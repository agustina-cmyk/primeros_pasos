import pytest
from unittest.mock import MagicMock, patch
from models import NewIdeaData


@pytest.fixture
def mock_login_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"access_token": "test-jwt-token"}
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_ideas_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = [
        {
            "id": "idea-1",
            "title": "Idea de prueba",
            "description": "Descripción",
            "category": "Core",
            "status": "submitted",
            "visibility": "public",
            "author_email": "user@test.com",
            "upvotes": 3,
            "downvotes": 1,
            "comment_count": 2,
        }
    ]
    mock.raise_for_status = MagicMock()
    return mock


def test_login_returns_token(mock_login_response):
    with patch("roadmap_client.requests.post", return_value=mock_login_response):
        import roadmap_client
        token = roadmap_client.login(
            supabase_url="https://test.supabase.co",
            anon_key="anon-key",
            email="agent@test.com",
            password="pass",
        )
    assert token == "test-jwt-token"


def test_get_ideas_returns_list(mock_ideas_response):
    with patch("roadmap_client.requests.get", return_value=mock_ideas_response):
        import roadmap_client
        ideas = roadmap_client.get_ideas(
            app_url="https://app.vercel.app",
            token="test-jwt",
        )
    assert len(ideas) == 1
    assert ideas[0].id == "idea-1"
    assert ideas[0].upvotes == 3


def test_vote_calls_correct_endpoint():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("roadmap_client.requests.post", return_value=mock_resp) as mock_post:
        import roadmap_client
        roadmap_client.vote(
            app_url="https://app.vercel.app",
            token="test-jwt",
            idea_id="idea-1",
            vote_type="like",
        )
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "idea-1/vote" in call_args[0][0]
    assert call_args[1]["json"]["type"] == "like"


def test_add_comment_calls_correct_endpoint():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("roadmap_client.requests.post", return_value=mock_resp) as mock_post:
        import roadmap_client
        roadmap_client.add_comment(
            app_url="https://app.vercel.app",
            token="test-jwt",
            idea_id="idea-1",
            body="Comentario de prueba",
        )
    call_args = mock_post.call_args
    assert "idea-1/comments" in call_args[0][0]
    assert call_args[1]["json"]["body"] == "Comentario de prueba"
    assert "parent_comment_id" not in call_args[1]["json"] or call_args[1]["json"]["parent_comment_id"] is None


def test_create_idea_returns_roadmap_idea():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "id": "new-idea-1",
        "title": "Nueva idea",
        "visibility": "internal",
        "status": "submitted",
    }
    with patch("roadmap_client.requests.post", return_value=mock_resp):
        import roadmap_client
        idea = roadmap_client.create_idea(
            app_url="https://app.vercel.app",
            token="test-jwt",
            data=NewIdeaData(title="Nueva idea", description="Desc", category="Core"),
        )
    assert idea["id"] == "new-idea-1"
    assert idea["visibility"] == "internal"
