import pytest
from unittest.mock import MagicMock
from vit_feedback.models import CourseItem, RatingPolicy, FeedbackResult
from vit_feedback.filler import fill_class_wise_feedback, fill_course_outcome_feedback, process_all_feedback

def test_fill_class_wise_feedback_dry_run(monkeypatch):
    monkeypatch.setattr("vit_feedback.filler.wait_for_ajax", lambda p, t=0: None)
    mock_page = MagicMock()
    mock_page.evaluate.return_value = True

    item = CourseItem(
        class_nbr="CH2026270100928",
        course_code="BCSE204P",
        faculty_name="SAKTHIVEL R",
        title="Algorithms Lab",
        course_id="CH_BCSE204P_00100",
        param_type="LO",
        status="Pending"
    )
    # Policy with quotes and quotes in suggestion to test injection safety
    policy = RatingPolicy(
        default_rating=5,
        course_overrides={"SAKTHIVEL": 3},
        custom_suggestions={"SAKTHIVEL": 'Excellent class! "High quality" & great labs\n100% recommended.'}
    )
    success = fill_class_wise_feedback(mock_page, item, policy, dry_run=True)
    assert success is True
    
    # Check that evaluate received parameterized arguments
    calls = mock_page.evaluate.call_args_list
    assert len(calls) >= 2
    # First call opens form: args should be [item.course_id, item.param_type]
    assert calls[0][0][1] == ["CH_BCSE204P_00100", "LO"]
    # Second call fills form: args should be [3, custom_suggestion]
    assert calls[1][0][1] == [3, 'Excellent class! "High quality" & great labs\n100% recommended.']

def test_fill_course_outcome_feedback_dry_run(monkeypatch):
    monkeypatch.setattr("vit_feedback.filler.wait_for_ajax", lambda p, t=0: None)
    mock_page = MagicMock()
    mock_page.evaluate.return_value = True

    item = CourseItem(
        course_code="BCSE204L",
        title="Algorithms",
        course_id="CH_BCSE204L_00100",
        table_type="course_outcome",
        status="Pending"
    )
    policy = RatingPolicy(default_rating=4)
    success = fill_course_outcome_feedback(mock_page, item, policy, dry_run=True)
    assert success is True
    calls = mock_page.evaluate.call_args_list
    assert len(calls) >= 2
    assert calls[0][0][1] == "CH_BCSE204L_00100"
    assert calls[1][0][1] == 4

def test_process_all_feedback_all_posted(monkeypatch):
    mock_page = MagicMock()
    monkeypatch.setattr(
        "vit_feedback.filler.extract_dashboard_courses",
        lambda p: (
            [CourseItem(course_code="BCSE204L", status="Posted")],
            [CourseItem(course_code="BCSE204L", status="Posted", table_type="course_outcome")]
        )
    )
    res = process_all_feedback(mock_page, RatingPolicy(), dry_run=False)
    assert res.is_success is True
    assert len(res.processed_courses) == 0
