import sys
import os
import getpass
import argparse
import logging
from typing import Optional, List

from vit_feedback.client import VitFeedbackClient
from vit_feedback.models import RatingPolicy, CourseItem
from vit_feedback.scraper import extract_dashboard_courses
from vit_feedback.filler import process_all_feedback

logger = logging.getLogger("vit_feedback")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vit-feedback",
        description="Automated End-Semester Feedback tool for VIT VTOP Portal"
    )
    parser.add_argument("-u", "--username", help="Student Username or Registration Number")
    parser.add_argument("-p", "--password", help="Student VTOP Password")
    parser.add_argument("-r", "--rating", type=int, default=5, choices=[1, 2, 3, 4, 5],
                        help="Default star rating across all courses (default: 5)")
    parser.add_argument("--co-rating", type=int, choices=[1, 2, 3, 4, 5],
                        help="Course Outcome star rating (default: matches default rating)")
    parser.add_argument("--override", action="append", default=[],
                        help="Per-course rating override, format: COURSE_CODE=RATING (e.g. BCSE301L=4)")
    parser.add_argument("--suggestions", default="The course structure and teaching methodologies were well executed.",
                        help="Default comment text for suggestions box")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fill ratings and suggestions without submitting")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Log in, display pending/posted courses, and exit without filling")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless",
                        help="Run browser with visible UI")
    parser.add_argument("--browser-path", help="Path to custom Chromium/Brave executable")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    return parser

def print_table(title: str, items: List[CourseItem]):
    print(f"\n=== {title} ===")
    print(f"{'No.':<4} {'Class/Code':<18} {'Title':<35} {'Faculty / Type':<25} {'Status':<10}")
    print("-" * 95)
    for i, it in enumerate(items, 1):
        ident = it.class_nbr if it.class_nbr else it.course_code
        fac = it.faculty_name if it.faculty_name else it.course_type
        print(f"{i:<4} {ident:<18} {it.title[:33]:<35} {fac[:23]:<25} {it.status:<10}")

def run_cli(args_list: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(args_list)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    username = args.username or os.environ.get("VIT_USERNAME")
    if not username:
        username = input("Enter VIT Username: ").strip()

    password = args.password or os.environ.get("VIT_PASSWORD")
    if not password:
        password = getpass.getpass("Enter VIT Password: ").strip()

    if not username or not password:
        print("Error: Username and password are required.", file=sys.stderr)
        return 1

    # Parse overrides
    overrides = {}
    for ov in args.override:
        if "=" in ov:
            k, v = ov.split("=", 1)
            try:
                overrides[k.strip()] = int(v.strip())
            except ValueError:
                print(f"Warning: Invalid override format: {ov}", file=sys.stderr)

    policy = RatingPolicy(
        default_rating=args.rating,
        course_outcome_rating=args.co_rating,
        course_overrides=overrides,
        default_suggestion=args.suggestions
    )

    client = VitFeedbackClient(browser_path=args.browser_path, headless=args.headless)
    try:
        print(f"Connecting to VIT Feedback portal for user {username}...")
        client.login(username, password)
        page = client.get_page()

        class_items, co_items = extract_dashboard_courses(page)
        print_table("FEEDBACK - CLASS WISE", class_items)
        print_table("FEEDBACK - COURSE OUTCOME", co_items)

        if args.analyze_only:
            print("\n[Analyze Only] Done inspecting portal status.")
            return 0

        pending_total = len([it for it in class_items if it.is_pending]) + len([it for it in co_items if it.is_pending])
        if pending_total == 0:
            print("\nAll courses have already been submitted (Posted)! Nothing to do.")
            return 0

        action_desc = "Simulating (DRY RUN)" if args.dry_run else "Submitting"
        print(f"\n{action_desc} feedback for {pending_total} pending items with default rating {policy.default_rating} stars...")
        
        result = process_all_feedback(page, policy, dry_run=args.dry_run)
        print(f"\nExecution Result: {result.status.upper()}")
        print(f"Message: {result.message}")
        if result.processed_courses:
            print(f"Processed items ({len(result.processed_courses)}):")
            for c in result.processed_courses:
                print(f"  ✓ {c}")
        if result.failed_courses:
            print(f"Failed items ({len(result.failed_courses)}):")
            for c in result.failed_courses:
                print(f"  ✗ {c}")

        return 0 if result.is_success else 1

    except Exception as e:
        logger.error("Automation error: %s", e)
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    finally:
        client.close()

def main():
    sys.exit(run_cli())

if __name__ == "__main__":
    main()
