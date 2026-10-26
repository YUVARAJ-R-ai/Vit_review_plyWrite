# VIT End-Semester Feedback Playwright Automation & MCP Server — Design Document

- **Date**: 2026-10-26
- **Status**: Complete & Ready for Review
- **Author**: Antigravity Pair Programmer
- **Project**: `Vit_review_plyWrite`

---

## 1. Intent and Why

VIT students are required each semester to fill out an End-Semester Course Feedback form (`https://vtopregcc.vit.ac.in/endfeedback/`) for every registered theory, lab, and soft-skill course, as well as separate Course Outcome (CO) feedback questionnaires. With 8–10 registered courses and up to 15 questions per course, this involves clicking hundreds of radio star ratings and filling textboxes manually under strict multi-tab and session restrictions.

The goal of this project is to build a robust, Python-based Playwright automation engine and FastMCP server. It can be run directly via CLI or coupled with any AI agent (via MCP) to inspect feedback status, apply configurable ratings (defaulting to 5-star positive ratings across all questions, with support for custom ratings like 3-star or granular per-course overrides), generate positive suggestions, solve login captchas autonomously via local OCR, and handle all portal edge cases.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Full End-to-End Automation**: Automate login, parsing both "FEEDBACK - CLASS WISE" and "FEEDBACK - COURSE OUTCOME" tables, filling star ratings and text feedback, and submitting each pending course.
- **Agent Coupling via MCP**: Expose a FastMCP server over stdio so AI agents can query status, inspect pending reviews, and trigger submissions with fine-grained control.
- **Configurable Review Strategy**:
  - Default: 5-star rating for all faculty, facility, general questions, and course outcomes.
  - Uniform rating override: e.g., 3-star, 4-star, or random high rating (4–5 stars).
  - Per-course / per-faculty overrides: custom rating and custom comments for specific course codes or class numbers.
  - Positive remarks for suggestion textboxes (`Any other feedback / suggestions:`).
- **Autonomous Captcha Solving**: Built-in OCR solver (`ddddocr`) for the portal's 6-character distorted text captcha with automatic retry and manual fallback.
- **Robust Edge Case Handling**:
  - Skip already "Posted" courses without redundant clicks.
  - Handle "Session Expired" / "Multi-Tab Access prevented" banners by clearing stale session cookies before navigation.
  - Dismiss SweetAlert (`swal`) confirmation dialogs automatically.
  - Single-Page AJAX navigation: Portal uses jQuery `$.ajax` updating `#page-wrapper` rather than full page reloads; wait for AJAX responses and loader overlays (`$.blockUI`).
  - NixOS compatibility: Support local system Chromium/Brave (`/run/current-system/sw/bin/brave`) and standard Playwright browser binaries.
- **Dry-Run Mode**: Inspect and analyze all courses, faculties, and questions without executing the final submission.

### Non-Goals
- Bypassing portal authentication without valid credentials.
- Hardcoding passwords into source code (read from CLI flags, `.env`, or MCP parameters).

### Anti-Goals
- Brittle selector-based scripting that breaks on minor whitespace changes.
- Incomplete runs that crash without reporting which courses succeeded and which failed.
- Locking user accounts due to uncontrolled retry loops on incorrect passwords.

---

## 3. Portal Mechanics & Architecture Analysis

Based on live portal inspection of `https://vtopregcc.vit.ac.in/endfeedback/`:
1. **Entry & Multi-Tab Protection**:
   - Accessing `/endfeedback/processStudentLogin` directly via GET returns a "Session Expired" page that submits to `/endfeedback/`.
   - Stale cookies trigger a "Multi-Tab Access prevented !!!" screen.
   - *Solution*: Start with a clean browser context, clear existing cookies for `/` and `/endfeedback/`, and navigate directly to `/endfeedback/`.
2. **Login Form**:
   - Fields: `#userName` (maxlength 15), `#password`, `#captchaString` (maxlength 6).
   - Captcha element: `#captcha_id` (`<img>` with base64 data URI). Refresh via `doRefreshCaptcha()`.
   - Submit button: triggers `validateLogin()` checking lengths, followed by form submission.
3. **Feedback Dashboard**:
   - Contains two distinct tables:
     - Table 1: **FEEDBACK - CLASS WISE** (Sl. No., Class Nbr, Course Code, Course Title, Course Type, L, T, P, J, C, Slot, Venue, Faculty Name, Status).
     - Table 2: **FEEDBACK - COURSE OUTCOME** (Sl. No., Course Code, Course Title, Generic Type, L, T, P, J, C, Status).
   - Status column contains either:
     - Text `Posted` (in red): already completed, cannot be edited.
     - Button `Post`: triggers `processCourseFeedbackPerception(courseId, courseType)` or `processCourseOutcomeFeedbackPerception(courseId)`.
4. **Question Form (Class Wise)**:
   - Form `#CourseFeedbackPerception`.
   - Hidden fields: `courseId`, `courseType`, `qno`, `ansType`.
   - Questions (Faculty, Facility, General): Each row contains a `<fieldset class="rating">` with radio buttons:
     `<input type="radio" value="5" name="[qno]" id="star5_[i]"><label for="star5_[i]"></label>`
   - Suggestions: `<textarea name="FBS01" id="FBS01" maxlength="250"></textarea>`.
   - Submit button: calls `saveCourseFeedbackPerception()`, validates all ratings are selected, posts via AJAX with FormData, and updates `#page-wrapper`.
5. **Question Form (Course Outcome)**:
   - Form `#CourseOutcomeFeedbackPerception`.
   - Rows for CO statements (e.g. CO1–CO6), each with `<fieldset class="rating">` radio inputs `value="1"` to `value="5"`.
   - Submit button: calls `saveCourseOutcomeFeedbackPerception()`.

---

## 4. Software Architecture & Builder Specifications

```
Vit_review_plyWrite/
├── src/
│   └── vit_feedback/
│       ├── __init__.py
│       ├── client.py           # Playwright browser manager, session pool, auth & navigation
│       ├── captcha.py          # Captcha OCR recognition (ddddocr) & retry logic
│       ├── scraper.py          # Dashboard table parsing & question inspection
│       ├── filler.py           # Rating policy engine (5-star, custom, overrides, text)
│       ├── models.py           # Pydantic schemas (CourseItem, RatingPolicy, RunResult)
│       ├── mcp_server.py       # FastMCP server exposing tools to AI agents
│       └── cli.py              # Rich CLI interface for human/terminal use
├── tests/
│   ├── test_models.py
│   └── test_filler.py
├── pyproject.toml              # Dependencies & CLI entry point
├── shell.nix                   # NixOS shell environment definition
└── README.md                   # Documentation & MCP configuration guide
```

### Component Details & Builder Calls:

1. **Session Management (Stateful vs. Stateless)**:
   - `client.py` implements a `SessionManager` that holds an active Playwright browser instance and page per user session with concurrency locks.
   - If an agent calls `vit_analyze_feedback` followed by `vit_submit_all_feedback` or `vit_submit_single_course`, the existing authenticated session is reused without re-triggering login or captcha solving.
   - Auto-login occurs seamlessly on the first call or when the session has expired. An explicit `vit_logout` tool is provided for clean teardown.

2. **Entity Identification**:
   - In `models.py`:
     - `CourseItem` carries `class_nbr`, `course_code` (e.g. `BCSE204L` vs `BCSE204P`), `title`, `faculty_name`, `status`, and `table_type` (`class_wise` | `course_outcome`).
   - In `vit_submit_single_course` and `course_overrides`:
     - Keys can match `class_nbr` (e.g., `CH2026270100925`), full `course_code` (e.g. `BCSE204L`), or a faculty name substring.
     - `target_type` parameter accepts `"class_wise"`, `"course_outcome"`, or `"both"` (default).

3. **Rating Policy Coupling**:
   - `RatingPolicy` model:
     - `default_rating: int = 5` (applies across all questions by default)
     - `course_outcome_rating: int | None = None` (if set, applies specifically to Course Outcome statements; otherwise follows `default_rating`)
     - `course_overrides: dict[str, int] = {}` (per-course / per-class overrides)
     - `custom_suggestions: dict[str, str] = {}` (per-course / per-class custom remarks)
     - `default_suggestion: str = "The course structure and teaching methodologies were well executed."`

4. **Captcha Engine (`captcha.py`)**:
   - Extracts base64 image bytes from `#captcha_id`.
   - Passes to `ddddocr` engine to predict the 6-character alphanumeric string.
   - If login fails with "Invalid Captcha", triggers `doRefreshCaptcha()` up to 3 times before raising an error or requesting manual input.

5. **FastMCP Server Tools**:
   - `vit_analyze_feedback(username, password)`: Logs in, inspects both tables, returns structured list of pending and posted courses.
   - `vit_submit_all_feedback(username, password, default_rating=5, course_outcome_rating=None, dry_run=False, per_course_ratings=None)`: Submits all pending courses.
   - `vit_submit_single_course(username, password, target_id, rating=5, target_type="both", suggestions="", dry_run=False)`: Submits feedback for a specific class/course.
   - `vit_logout()`: Safely closes the session and clears browser context.

---

## 5. Builder Calls Summary
- **Session**: Stateful session pool with auto-relogin on expiry to prevent multi-tab collisions and lockouts.
- **Course Resolution**: Multi-field matcher supporting `class_nbr`, `course_code`, and `faculty_name`.
- **Policy**: Decoupled default ratings for Class-Wise and Course Outcomes with granular overrides.
