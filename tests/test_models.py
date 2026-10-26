import pytest
from vit_feedback.models import CourseItem, RatingPolicy, FeedbackResult

def test_course_item_creation():
    item = CourseItem(
        class_nbr="CH2026270100925",
        course_code="BCSE204L",
        title="Design and Analysis of Algorithms",
        course_type="Theory Only",
        faculty_name="SAKTHIVEL R",
        status="Pending",
        table_type="class_wise",
        course_id="CH_BCSE204L_00100"
    )
    assert item.course_code == "BCSE204L"
    assert item.is_pending is True
    assert item.is_posted is False

def test_course_item_posted():
    item = CourseItem(
        class_nbr="",
        course_code="BCSE204L",
        title="Design and Analysis of Algorithms",
        course_type="TH",
        faculty_name="",
        status="Posted",
        table_type="course_outcome"
    )
    assert item.is_posted is True
    assert item.is_pending is False

def test_rating_policy_defaults():
    policy = RatingPolicy()
    assert policy.default_rating == 5
    assert policy.get_co_rating() == 5
    assert policy.get_rating_for("BCSE204L") == 5
    assert "structure" in policy.get_suggestions_for("BCSE204L")

def test_rating_policy_overrides():
    policy = RatingPolicy(
        default_rating=4,
        course_outcome_rating=5,
        course_overrides={"BCSE301L": 3},
        custom_suggestions={"BCSE301L": "Needs better lab coordination."}
    )
    assert policy.get_rating_for("BCSE301L") == 3
    assert policy.get_rating_for("BCSE204L") == 4
    assert policy.get_co_rating() == 5
    assert policy.get_suggestions_for("BCSE301L") == "Needs better lab coordination."

def test_feedback_result():
    res = FeedbackResult(
        status="success",
        processed_courses=["BCSE204P", "BCSE301L"],
        failed_courses=[],
        message="All feedback submitted successfully"
    )
    assert res.is_success is True
    assert len(res.processed_courses) == 2
