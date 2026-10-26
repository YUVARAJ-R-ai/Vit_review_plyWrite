import time
import logging
from typing import Optional
from playwright.sync_api import Page

from vit_feedback.models import CourseItem, RatingPolicy, FeedbackResult
from vit_feedback.scraper import extract_dashboard_courses

logger = logging.getLogger(__name__)

def wait_for_ajax(page: Page, timeout: float = 10.0):
    """Wait for jQuery AJAX and blockUI loading indicator to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            is_busy = page.evaluate("""() => {
                const jqActive = (typeof $ !== 'undefined' && $.active > 0);
                const blockUi = document.querySelector('.blockUI') !== null;
                return jqActive || blockUi;
            }""")
            if not is_busy:
                break
        except Exception:
            pass
        time.sleep(0.3)
    time.sleep(0.5)

def dismiss_alerts(page: Page) -> Optional[str]:
    """Dismiss any SweetAlert modals that appear."""
    try:
        title = page.evaluate("""() => {
            const h2 = document.querySelector('.sweet-alert h2');
            if (h2 && h2.offsetParent !== null) {
                const text = h2.innerText;
                const okBtn = document.querySelector('.sweet-alert button.confirm');
                if (okBtn) okBtn.click();
                return text;
            }
            return null;
        }""")
        if title:
            time.sleep(0.5)
            return title
    except Exception:
        pass
    return None

def fill_class_wise_feedback(page: Page, item: CourseItem, policy: RatingPolicy, dry_run: bool = False) -> bool:
    """Open class feedback form, select star ratings, fill suggestions, and submit."""
    logger.info("Filling Class-Wise feedback for %s (%s) - %s", item.course_code, item.class_nbr, item.faculty_name)

    # 1. Trigger open form via JS AJAX
    open_script = f"""() => {{
        if (typeof processCourseFeedbackPerception === 'function') {{
            processCourseFeedbackPerception('{item.course_id}', '{item.param_type}');
            return true;
        }}
        return false;
    }}"""
    res = page.evaluate(open_script)
    if not res:
        logger.error("processCourseFeedbackPerception function not found on page.")
        return False
    wait_for_ajax(page)

    # 2. Determine rating & suggestions
    rating = policy.get_rating_for(item.course_code or item.class_nbr)
    suggestions = policy.get_suggestions_for(item.course_code or item.class_nbr)

    logger.info("Applying %d-star rating and suggestions to %s", rating, item.course_code)

    # 3. Fill radios and textarea
    fill_script = f"""() => {{
        const form = document.getElementById('CourseFeedbackPerception');
        if (!form) return false;

        // Select all question radios for target rating
        const fieldsets = Array.from(form.querySelectorAll('fieldset.rating'));
        for (const fs of fieldsets) {{
            const radio = fs.querySelector('input[type="radio"][value="{rating}"]');
            if (radio) {{
                radio.checked = true;
                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}

        // Fill suggestions textarea
        const ta = form.querySelector('textarea#FBS01') || form.querySelector('textarea');
        if (ta) {{
            ta.value = "{suggestions}";
            ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        return true;
    }}"""
    filled = page.evaluate(fill_script)
    if not filled:
        logger.warning("Could not locate CourseFeedbackPerception form.")
        return False

    if dry_run:
        logger.info("[DRY RUN] Feedback filled. Skipping submission, returning back to dashboard.")
        page.evaluate("if (typeof goBackCourseFeedback === 'function') goBackCourseFeedback();")
        wait_for_ajax(page)
        return True

    # 4. Submit form
    logger.info("Submitting CourseFeedbackPerception form...")
    page.evaluate("if (typeof saveCourseFeedbackPerception === 'function') saveCourseFeedbackPerception();")
    wait_for_ajax(page)
    dismiss_alerts(page)

    # 5. Return to dashboard if needed
    page.evaluate("if (typeof goBackCourseFeedback === 'function') goBackCourseFeedback();")
    wait_for_ajax(page)
    return True

def fill_course_outcome_feedback(page: Page, item: CourseItem, policy: RatingPolicy, dry_run: bool = False) -> bool:
    """Open course outcome form, select rating for CO questions, and submit."""
    logger.info("Filling Course Outcome feedback for %s", item.course_code)

    # 1. Trigger open CO form via JS AJAX
    open_script = f"""() => {{
        if (typeof processCourseOutcomeFeedbackPerception === 'function') {{
            processCourseOutcomeFeedbackPerception('{item.course_id}');
            return true;
        }}
        return false;
    }}"""
    res = page.evaluate(open_script)
    if not res:
        logger.error("processCourseOutcomeFeedbackPerception function not found on page.")
        return False
    wait_for_ajax(page)

    # 2. Determine rating
    co_rating = policy.get_co_rating(item.course_code)
    logger.info("Applying %d-star rating to Course Outcomes for %s", co_rating, item.course_code)

    # 3. Fill radios
    fill_script = f"""() => {{
        const form = document.getElementById('CourseOutcomeFeedbackPerception');
        if (!form) return false;

        const fieldsets = Array.from(form.querySelectorAll('fieldset.rating'));
        for (const fs of fieldsets) {{
            const radio = fs.querySelector('input[type="radio"][value="{co_rating}"]');
            if (radio) {{
                radio.checked = true;
                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}

        return true;
    }}"""
    filled = page.evaluate(fill_script)
    if not filled:
        logger.warning("Could not locate CourseOutcomeFeedbackPerception form.")
        return False

    if dry_run:
        logger.info("[DRY RUN] Course Outcome filled. Skipping submission, returning back to dashboard.")
        page.evaluate("if (typeof goBackCourseFeedback === 'function') goBackCourseFeedback();")
        wait_for_ajax(page)
        return True

    # 4. Submit form
    logger.info("Submitting CourseOutcomeFeedbackPerception form...")
    page.evaluate("if (typeof saveCourseOutcomeFeedbackPerception === 'function') saveCourseOutcomeFeedbackPerception();")
    wait_for_ajax(page)
    dismiss_alerts(page)

    # 5. Return to dashboard if needed
    page.evaluate("if (typeof goBackCourseFeedback === 'function') goBackCourseFeedback();")
    wait_for_ajax(page)
    return True

def process_all_feedback(page: Page, policy: RatingPolicy, dry_run: bool = False) -> FeedbackResult:
    """Process and submit feedback for all pending courses in both tables."""
    processed = []
    failed = []

    # 1. Process Class-Wise feedback
    class_items, _ = extract_dashboard_courses(page)
    pending_class = [it for it in class_items if it.is_pending]
    logger.info("Found %d pending Class-Wise feedback items.", len(pending_class))

    for item in pending_class:
        try:
            ok = fill_class_wise_feedback(page, item, policy, dry_run=dry_run)
            if ok:
                processed.append(f"{item.course_code} ({item.class_nbr})")
            else:
                failed.append(f"{item.course_code} ({item.class_nbr})")
        except Exception as e:
            logger.error("Error submitting Class-Wise feedback for %s: %s", item.course_code, e)
            failed.append(f"{item.course_code} ({item.class_nbr})")

    # 2. Re-extract dashboard for fresh state
    _, co_items = extract_dashboard_courses(page)
    pending_co = [it for it in co_items if it.is_pending]
    logger.info("Found %d pending Course Outcome feedback items.", len(pending_co))

    for item in pending_co:
        try:
            ok = fill_course_outcome_feedback(page, item, policy, dry_run=dry_run)
            if ok:
                processed.append(f"CO: {item.course_code}")
            else:
                failed.append(f"CO: {item.course_code}")
        except Exception as e:
            logger.error("Error submitting Course Outcome feedback for %s: %s", item.course_code, e)
            failed.append(f"CO: {item.course_code}")

    status = "success" if not failed else ("partial" if processed else "failed")
    msg = f"Completed processing {len(processed)} items ({len(failed)} failed)."
    return FeedbackResult(
        status=status,
        processed_courses=processed,
        failed_courses=failed,
        message=msg
    )
