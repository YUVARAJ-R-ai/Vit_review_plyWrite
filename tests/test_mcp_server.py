import pytest
import asyncio
from unittest.mock import MagicMock
from vit_feedback.mcp_server import (
    vit_analyze_feedback,
    vit_submit_all_feedback,
    vit_submit_single_course,
    vit_logout,
    mcp
)
from vit_feedback.models import CourseItem, FeedbackResult

def test_mcp_instance_registered():
    assert mcp.name == "vit-feedback"
    tools = asyncio.run(mcp.list_tools())
    tool_names = [t.name for t in tools]
    assert "vit_analyze_feedback" in tool_names
    assert "vit_submit_all_feedback" in tool_names
    assert "vit_submit_single_course" in tool_names
    assert "vit_logout" in tool_names

def test_vit_analyze_feedback_mock(monkeypatch):
    mock_client = MagicMock()
    mock_client.all_already_posted = False
    mock_client.login.return_value = True
    mock_client.get_page.return_value = MagicMock()

    monkeypatch.setattr("vit_feedback.mcp_server.get_client", lambda u, p: mock_client)
    monkeypatch.setattr(
        "vit_feedback.mcp_server.extract_dashboard_courses",
        lambda page: (
            [CourseItem(course_code="BCSE204L", status="Posted")],
            [CourseItem(course_code="BCSE204P", status="Pending", course_id="CH_1")]
        )
    )

    res = vit_analyze_feedback("u", "p")
    assert res["status"] == "success"
    assert len(res["class_wise_courses"]) == 1
    assert len(res["course_outcome_courses"]) == 1
    assert res["pending_count"] == 1

def test_vit_submit_all_feedback_mock(monkeypatch):
    mock_client = MagicMock()
    mock_client.all_already_posted = False
    mock_client.login.return_value = True
    mock_client.get_page.return_value = MagicMock()

    monkeypatch.setattr("vit_feedback.mcp_server.get_client", lambda u, p: mock_client)
    monkeypatch.setattr(
        "vit_feedback.mcp_server.process_all_feedback",
        lambda page, policy, dry_run: FeedbackResult(status="success", processed_courses=["BCSE204P"], message="Done")
    )

    res = vit_submit_all_feedback("u", "p", default_rating=5, dry_run=True)
    assert res["status"] == "success"
    assert "BCSE204P" in res["processed_courses"]

def test_vit_already_posted_short_circuit(monkeypatch):
    mock_client = MagicMock()
    mock_client.all_already_posted = True
    mock_client.login.return_value = True
    monkeypatch.setattr("vit_feedback.mcp_server.get_client", lambda u, p: mock_client)

    res = vit_analyze_feedback("u", "p")
    assert res["all_already_posted"] is True
    assert res["pending_count"] == 0
