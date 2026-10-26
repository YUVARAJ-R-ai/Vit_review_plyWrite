import logging
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP

from vit_feedback.client import VitFeedbackClient
from vit_feedback.models import RatingPolicy, CourseItem
from vit_feedback.scraper import extract_dashboard_courses
from vit_feedback.filler import (
    process_all_feedback,
    fill_class_wise_feedback,
    fill_course_outcome_feedback
)

logger = logging.getLogger("vit_feedback.mcp")

mcp = FastMCP("vit-feedback")

_global_client: Optional[VitFeedbackClient] = None
_global_user: Optional[str] = None

def get_client(username: str, password: str) -> VitFeedbackClient:
    """Retrieve an active authenticated client or create a new session."""
    global _global_client, _global_user
    if _global_client and _global_user == username and _global_client.is_logged_in():
        return _global_client

    if _global_client:
        try:
            _global_client.close()
        except Exception:
            pass

    client = VitFeedbackClient(headless=True)
    client.login(username, password)
    _global_client = client
    _global_user = username
    return client

@mcp.tool()
def vit_analyze_feedback(username: str, password: str) -> Dict[str, Any]:
    """Inspect and analyze the current VIT end-semester feedback portal status.

    Returns the list of all enrolled courses, faculty names, class numbers,
    and whether each has been Posted or is still Pending, without submitting any data.
    """
    try:
        client = get_client(username, password)
        page = client.get_page()

        if client.all_already_posted:
            return {
                "status": "success",
                "username": username,
                "message": "All feedback for this semester has already been submitted and posted to VTOP.",
                "pending_count": 0,
                "all_already_posted": True,
                "class_wise_courses": [],
                "course_outcome_courses": []
            }

        class_items, co_items = extract_dashboard_courses(page)

        pending_class = [it for it in class_items if it.is_pending]
        pending_co = [it for it in co_items if it.is_pending]

        return {
            "status": "success",
            "username": username,
            "total_courses": len(class_items) + len(co_items),
            "pending_count": len(pending_class) + len(pending_co),
            "posted_count": (len(class_items) - len(pending_class)) + (len(co_items) - len(pending_co)),
            "all_already_posted": False,
            "class_wise_courses": [it.model_dump() for it in class_items],
            "course_outcome_courses": [it.model_dump() for it in co_items],
        }
    except Exception as e:
        logger.error("Error analyzing feedback: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
def vit_submit_all_feedback(
    username: str,
    password: str,
    default_rating: int = 5,
    course_outcome_rating: Optional[int] = None,
    dry_run: bool = False,
    per_course_ratings: Optional[Dict[str, int]] = None,
    default_suggestions: str = "The course structure and teaching methodologies were well executed."
) -> Dict[str, Any]:
    """Automate end-semester feedback submission for all pending courses in VIT VTOP.

    Args:
        username: Student username or registration number.
        password: VTOP password.
        default_rating: Star rating (1 to 5) for all questions (default: 5).
        course_outcome_rating: Optional star rating (1 to 5) for Course Outcomes.
        dry_run: If True, fills the forms and reviews them without submitting.
        per_course_ratings: Optional mapping of COURSE_CODE or CLASS_NBR to custom ratings.
        default_suggestions: Feedback remarks text for suggestions box.
    """
    try:
        client = get_client(username, password)
        page = client.get_page()

        if client.all_already_posted:
            return {
                "status": "success",
                "message": "All feedback for this semester has already been submitted and posted to VTOP.",
                "processed_courses": [],
                "failed_courses": [],
                "dry_run": dry_run
            }

        policy = RatingPolicy(
            default_rating=default_rating,
            course_outcome_rating=course_outcome_rating,
            course_overrides=per_course_ratings or {},
            default_suggestion=default_suggestions
        )

        result = process_all_feedback(page, policy, dry_run=dry_run)
        return {
            "status": result.status,
            "message": result.message,
            "processed_courses": result.processed_courses,
            "failed_courses": result.failed_courses,
            "dry_run": dry_run
        }
    except Exception as e:
        logger.error("Error submitting all feedback: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
def vit_submit_single_course(
    username: str,
    password: str,
    target_id: str,
    rating: int = 5,
    target_type: str = "both",
    suggestions: str = "The course was well organized and concepts were clearly taught.",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Submit feedback for a specific single course or class in VIT VTOP.

    Args:
        username: Student username or registration number.
        password: VTOP password.
        target_id: Course Code (e.g. BCSE204L), Class Number (e.g. CH2026270100925), or Faculty Name.
        rating: Star rating (1 to 5) to submit (default: 5).
        target_type: "class_wise", "course_outcome", or "both".
        suggestions: Custom remark for this course.
        dry_run: If True, previews without submitting.
    """
    try:
        client = get_client(username, password)
        page = client.get_page()

        if client.all_already_posted:
            return {
                "status": "success",
                "message": "All feedback for this semester has already been submitted and posted to VTOP.",
                "processed": [],
                "dry_run": dry_run
            }

        class_items, co_items = extract_dashboard_courses(page)
        policy = RatingPolicy(
            default_rating=rating,
            course_overrides={target_id: rating},
            custom_suggestions={target_id: suggestions}
        )

        processed = []
        clean_target = target_id.strip().upper()

        if target_type in ("class_wise", "both"):
            for it in class_items:
                if it.is_pending and (
                    clean_target in it.course_code.upper() or
                    clean_target in it.class_nbr.upper() or
                    clean_target in it.faculty_name.upper()
                ):
                    ok = fill_class_wise_feedback(page, it, policy, dry_run=dry_run)
                    if ok:
                        processed.append(f"{it.course_code} ({it.class_nbr})")

        if target_type in ("course_outcome", "both"):
            for it in co_items:
                if it.is_pending and (clean_target in it.course_code.upper()):
                    ok = fill_course_outcome_feedback(page, it, policy, dry_run=dry_run)
                    if ok:
                        processed.append(f"CO: {it.course_code}")

        if not processed:
            return {
                "status": "not_found",
                "message": f"No pending feedback found matching target '{target_id}' for type '{target_type}'."
            }

        return {
            "status": "success",
            "message": f"Processed {len(processed)} matching item(s).",
            "processed": processed,
            "dry_run": dry_run
        }
    except Exception as e:
        logger.error("Error submitting single course feedback: %s", e)
        return {"status": "error", "message": str(e)}

@mcp.tool()
def vit_logout() -> Dict[str, Any]:
    """Safely log out and release the active browser session."""
    global _global_client, _global_user
    if _global_client:
        try:
            _global_client.close()
        except Exception as e:
            logger.warning("Error during logout: %s", e)
        finally:
            _global_client = None
            _global_user = None
    return {"status": "success", "message": "Logged out and browser session terminated."}

def main():
    mcp.run()

if __name__ == "__main__":
    main()
