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

def test_rating_policy_empty_string_safety():
    policy = RatingPolicy(
        default_rating=5,
        course_overrides={"BCSE204L": 4, "": 2},
        custom_suggestions={"BCSE204L": "Great", "": "Empty"}
    )
    # Empty string should never match an override or empty key
    assert policy.get_rating_for("") == 5
    assert policy.get_co_rating("") == 5
    assert policy.get_suggestions_for("") == policy.default_suggestion

def test_rating_policy_multiple_identifiers():
    policy = RatingPolicy(
        default_rating=5,
        course_overrides={"SAKTHIVEL": 4, "CH2026270100925": 3},
        custom_suggestions={"SAKTHIVEL": "Great teacher."}
    )
    # Match via faculty name
    assert policy.get_rating_for("UNKNOWN_COURSE", "", "SAKTHIVEL R") == 4
    assert policy.get_suggestions_for("UNKNOWN_COURSE", "", "SAKTHIVEL R") == "Great teacher."
    # Match via class number
    assert policy.get_rating_for("UNKNOWN_COURSE", "CH2026270100925", "OTHER FACULTY") == 3
    # No match falls back to default
    assert policy.get_rating_for("UNKNOWN_COURSE", "CH9999", "OTHER FACULTY") == 5

def test_feedback_result():
    res = FeedbackResult(
        status="success",
        processed_courses=["BCSE204P", "BCSE301L"],
        failed_courses=[],
        message="All feedback submitted successfully"
    )
    assert res.is_success is True
    assert len(res.processed_courses) == 2
