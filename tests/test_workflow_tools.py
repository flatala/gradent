import importlib
import json

import pytest


@pytest.mark.asyncio
async def test_run_planning_workflow(monkeypatch):
    """Planning tool should serialize plan data from the graph."""

    class FakePlan:
        goal = "Plan a study session"
        steps = ["Review notes", "Practice problems"]
        considerations = ["Stay focused"]

    async def fake_ainvoke(state, config):
        return {"plan": FakePlan()}

    from workflows.planning import graph as planning_graph_module

    monkeypatch.setattr(planning_graph_module.planning_graph, "ainvoke", fake_ainvoke)

    from main_agent import workflow_tools

    importlib.reload(workflow_tools)

    result = await workflow_tools.run_planning_workflow.ainvoke(
        {"query": "Help me plan a study session"},
        config={"configurable": {"openai_api_key": "test-key"}},
    )
    parsed = json.loads(result)
    assert parsed["goal"] == "Plan a study session"
    assert parsed["steps"] == ["Review notes", "Practice problems"]
    assert parsed["considerations"] == ["Stay focused"]


@pytest.mark.asyncio
async def test_assess_assignment_tool(monkeypatch):
    """Assignment assessment tool should surface structured output."""

    class FakeAssessment:
        effort_hours_low = 2.0
        effort_hours_most = 4.0
        effort_hours_high = 6.0
        difficulty_1to5 = 3.0
        risk_score_0to100 = 40.0
        confidence_0to1 = 0.8
        milestones = [{"label": "Draft", "hours": 2.0, "days_before_due": 3}]
        prereq_topics = ["Topic A"]
        deliverables = ["Report"]
        blocking_dependencies = []
        summary = "Sample summary"

    async def fake_assessment_invoke(state, config):
        return {"assessment": FakeAssessment(), "assessment_record_id": 10}

    from workflows.assignment_assessment import graph as assessment_graph_module

    monkeypatch.setattr(assessment_graph_module.assessment_graph, "ainvoke", fake_assessment_invoke)

    from main_agent import workflow_tools

    importlib.reload(workflow_tools)

    result = await workflow_tools.assess_assignment.ainvoke(
        {
            "title": "Sample Assignment",
            "description": "Write a short paper.",
            "course_name": "Course 101",
        },
        config={"configurable": {"openai_api_key": "test-key"}},
    )
    parsed = json.loads(result)
    assert parsed["title"] == "Sample Assignment"
    assert parsed["difficulty_1to5"] == 3.0
    assert parsed["effort_estimates"]["most_likely_hours"] == 4.0
    assert parsed["summary"] == "Sample summary"

