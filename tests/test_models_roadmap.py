from models import (
    RoadmapIdea,
    RoadmapComment,
    NewIdeaData,
    RoadmapAction,
    RoadmapPlan,
    RoadmapMemoryState,
    AgentMemoryState,
)


def test_roadmap_idea_fields():
    idea = RoadmapIdea(
        id="abc",
        title="Idea de test",
        description="Descripción",
        category="Core",
        status="submitted",
        visibility="internal",
        author_email="agent@test.com",
        upvotes=2,
        downvotes=0,
        comment_count=1,
    )
    assert idea.id == "abc"
    assert idea.visibility == "internal"


def test_roadmap_action_vote():
    action = RoadmapAction(
        action="vote",
        idea_id="abc",
        comment_id=None,
        vote_type="like",
        comment_body=None,
        new_idea=None,
    )
    assert action.action == "vote"
    assert action.vote_type == "like"


def test_roadmap_plan_empty():
    plan = RoadmapPlan(actions=[], skip_reason="Sin cambios")
    assert plan.actions == []
    assert plan.skip_reason == "Sin cambios"


def test_roadmap_memory_state_defaults():
    state = RoadmapMemoryState()
    assert state.voted_idea_ids == {}
    assert state.commented_idea_ids == []
    assert state.replied_comment_ids == []
    assert state.created_idea_ids == []
    assert state.last_run_at is None


def test_agent_memory_state_includes_roadmap():
    mem = AgentMemoryState.empty()
    assert mem.roadmap is not None
    assert isinstance(mem.roadmap, RoadmapMemoryState)


def test_agent_memory_state_to_dict_includes_roadmap():
    mem = AgentMemoryState.empty()
    mem.roadmap.created_idea_ids.append("idea-1")
    d = mem.to_dict()
    assert "roadmap" in d
    assert d["roadmap"]["created_idea_ids"] == ["idea-1"]
