# VIT End-Semester Feedback Playwright Automation & MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust Python Playwright automation system and FastMCP server for the VIT End-Semester Feedback portal (`https://vtopregcc.vit.ac.in/endfeedback/`), supporting autonomous captcha solving, configurable 5-star / custom ratings, positive suggestions, edge case handling, CLI, and agent tools.

**Architecture:** A modular Python package with `client.py` managing stateful Playwright sessions and cookie isolation on NixOS; `captcha.py` using `ddddocr` for autonomous 6-character captcha recognition; `scraper.py` extracting Class-Wise and Course-Outcome tables; `filler.py` applying rating policies to radio fieldsets and suggestion textareas via jQuery AJAX; `cli.py` providing rich terminal interaction; and `mcp_server.py` exposing FastMCP tools over stdio.

**Tech Stack:** Python 3.12, Playwright, FastMCP, ddddocr, Pillow, Pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-10-26-vit-feedback-automation-design.md`

## Global Constraints

- Must run on NixOS using system browser binary (`/run/current-system/sw/bin/brave`) or standard Chromium.
- Default rating is 5 stars across all questions, facility perceptions, and course outcomes unless explicitly overridden.
- Passwords and credentials must not be hardcoded in committed code.
- Must cleanly handle portal states: "Session Expired", "Multi-Tab Access prevented", and SweetAlert popups.

## Review Focus

1. **Stale Session / Multi-Tab Collisions**: Portal displays "Multiple Tabs Access prevented !!!" if old cookies persist. Tested in Task 3 by clearing cookies before navigating to `/endfeedback/`.
2. **Captcha Recognition Misses**: OCR may occasionally misclassify 1 of 6 distorted characters. Tested in Task 2 & 3 with retry mechanism via `doRefreshCaptcha()`.
3. **AJAX Single-Page Replacement Timing**: Portal replaces `#page-wrapper` asynchronously with `$.blockUI`. Tested in Task 4 & 5 by awaiting the unblock overlay before parsing DOM.
4. **Already Submitted Courses ("Posted")**: Courses marked "Posted" have no "Post" button. Tested in Task 4 & 5 to ensure they are skipped safely without errors.
5. **Soft Skills / Non-Standard Course Rows**: Rows with generic type "SS" or soft skills have differing credit columns. Tested in Task 4 with flexible row parsing.

---

### Task 1: Project Environment & Core Data Models

**Files:**
- Create: `pyproject.toml`
- Create: `shell.nix`
- Create: `src/vit_feedback/__init__.py`
- Create: `src/vit_feedback/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `CourseItem(class_nbr: str, course_code: str, title: str, course_type: str, faculty_name: str, status: str, table_type: str, course_id: str = "")`
  - `RatingPolicy(default_rating: int = 5, course_outcome_rating: int | None = None, course_overrides: dict[str, int] = {}, custom_suggestions: dict[str, str] = {}, default_suggestion: str = "The course structure and teaching methodologies were well executed.")`
  - `FeedbackResult(status: str, processed_courses: list[str], failed_courses: list[str], message: str)`

- [ ] **Step 1: Write tests for data models in `tests/test_models.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_models.py`)**
- [ ] **Step 3: Create `pyproject.toml`, `shell.nix`, `src/vit_feedback/__init__.py`, and implement `models.py`**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_models.py`)**
- [ ] **Step 5: Commit (`git add pyproject.toml shell.nix src/ tests/ && git commit -m "feat: setup project models and environment"`)**

---

### Task 2: Captcha Engine (`captcha.py`)

**Files:**
- Create: `src/vit_feedback/captcha.py`
- Test: `tests/test_captcha.py`

**Interfaces:**
- Consumes: `ddddocr`, `Pillow`, `base64`
- Produces:
  - `solve_captcha_bytes(image_bytes: bytes) -> str`
  - `solve_captcha_base64(data_uri: str) -> str`

- [ ] **Step 1: Write test for captcha decoding and recognition in `tests/test_captcha.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_captcha.py`)**
- [ ] **Step 3: Implement `solve_captcha_bytes` and `solve_captcha_base64` in `src/vit_feedback/captcha.py` with alphanumeric cleaning**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_captcha.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/captcha.py tests/test_captcha.py && git commit -m "feat: add captcha recognition engine"`)**

---

### Task 3: Browser Client & Authentication (`client.py`)

**Files:**
- Create: `src/vit_feedback/client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: `Playwright`, `src/vit_feedback/captcha.py`
- Produces:
  - `VitFeedbackClient(browser_path: str | None = None, headless: bool = True)`
  - `VitFeedbackClient.login(username: str, password: str, max_retries: int = 3) -> bool`
  - `VitFeedbackClient.get_page() -> Page`
  - `VitFeedbackClient.logout()`
  - `VitFeedbackClient.close()`

- [ ] **Step 1: Write unit tests with mock Page/Browser in `tests/test_client.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_client.py`)**
- [ ] **Step 3: Implement `VitFeedbackClient` in `src/vit_feedback/client.py` handling cookie clearing, portal URL navigation, captcha extraction, and login retries**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_client.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/client.py tests/test_client.py && git commit -m "feat: add Playwright client and auth manager"`)**

---

### Task 4: Scraper & Dashboard Parser (`scraper.py`)

**Files:**
- Create: `src/vit_feedback/scraper.py`
- Test: `tests/test_scraper.py`

**Interfaces:**
- Consumes: `models.CourseItem`, `Playwright Page`
- Produces:
  - `extract_dashboard_courses(page: Page) -> tuple[list[CourseItem], list[CourseItem]]`
  - Returns `(class_wise_items, course_outcome_items)`

- [ ] **Step 1: Write tests with sample portal HTML in `tests/test_scraper.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_scraper.py`)**
- [ ] **Step 3: Implement `extract_dashboard_courses` in `src/vit_feedback/scraper.py` extracting `class_nbr`, `course_code`, `title`, `faculty_name`, `status`, and button onclick IDs**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_scraper.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/scraper.py tests/test_scraper.py && git commit -m "feat: add dashboard table scraper"`)**

---

### Task 5: Review Filler Engine (`filler.py`)

**Files:**
- Create: `src/vit_feedback/filler.py`
- Test: `tests/test_filler.py`

**Interfaces:**
- Consumes: `models.CourseItem`, `models.RatingPolicy`, `models.FeedbackResult`, `Playwright Page`
- Produces:
  - `fill_class_wise_feedback(page: Page, item: CourseItem, policy: RatingPolicy, dry_run: bool = False) -> bool`
  - `fill_course_outcome_feedback(page: Page, item: CourseItem, policy: RatingPolicy, dry_run: bool = False) -> bool`
  - `process_all_feedback(page: Page, policy: RatingPolicy, dry_run: bool = False) -> FeedbackResult`

- [ ] **Step 1: Write tests with mock feedback forms in `tests/test_filler.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_filler.py`)**
- [ ] **Step 3: Implement `fill_class_wise_feedback`, `fill_course_outcome_feedback`, and `process_all_feedback` handling star radio selection, suggestion filling, AJAX submissions, and returning back to dashboard**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_filler.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/filler.py tests/test_filler.py && git commit -m "feat: add feedback filler engine"`)**

---

### Task 6: Command-Line Interface (`cli.py`)

**Files:**
- Create: `src/vit_feedback/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `client.VitFeedbackClient`, `filler.process_all_feedback`, `models.RatingPolicy`
- Produces:
  - CLI executable entrypoint `main()`: supports `--username`, `--password`, `--rating`, `--co-rating`, `--dry-run`, `--headless`

- [ ] **Step 1: Write CLI argument parsing and runner tests in `tests/test_cli.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_cli.py`)**
- [ ] **Step 3: Implement `cli.py` with `argparse`, masked password input fallback (`getpass`), and execution summary table**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_cli.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/cli.py tests/test_cli.py && git commit -m "feat: add CLI interface"`)**

---

### Task 7: FastMCP Server (`mcp_server.py`)

**Files:**
- Create: `src/vit_feedback/mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `FastMCP`, `client.VitFeedbackClient`, `scraper`, `filler`
- Produces:
  - `vit_analyze_feedback(username, password) -> dict`
  - `vit_submit_all_feedback(username, password, default_rating=5, course_outcome_rating=None, dry_run=False, per_course_ratings=None) -> dict`
  - `vit_submit_single_course(username, password, target_id, rating=5, target_type="both", suggestions="", dry_run=False) -> dict`
  - `vit_logout() -> dict`

- [ ] **Step 1: Write MCP server tool calling tests in `tests/test_mcp_server.py`**
- [ ] **Step 2: Run test to verify it fails (`pytest tests/test_mcp_server.py`)**
- [ ] **Step 3: Implement FastMCP server with tool definitions and session pool in `src/vit_feedback/mcp_server.py`**
- [ ] **Step 4: Run test to verify it passes (`pytest tests/test_mcp_server.py`)**
- [ ] **Step 5: Commit (`git add src/vit_feedback/mcp_server.py tests/test_mcp_server.py && git commit -m "feat: add FastMCP server for agent integration"`)**

---

### Task 8: End-to-End Live Verification & Documentation

**Files:**
- Create: `README.md`
- Verify: Live run on `https://vtopregcc.vit.ac.in/endfeedback/` with user credentials (`<VTOP_USERNAME>` / `<VTOP_PASSWORD>`)

- [ ] **Step 1: Create comprehensive `README.md` explaining installation, CLI usage, MCP setup for Claude Desktop / Cursor / Antigravity, and rating policies**
- [ ] **Step 2: Execute live analysis run (`python -m vit_feedback --username <VTOP_USERNAME> --password <VTOP_PASSWORD> --dry-run`) to verify portal communication**
- [ ] **Step 3: Execute live submission run with 5-star default ratings on all pending courses**
- [ ] **Step 4: Confirm 100% of courses transition to "Posted" status**
- [ ] **Step 5: Final commit and summary report**
