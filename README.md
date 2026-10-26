# VIT End-Semester Feedback Automation & MCP Server

Automated Python Playwright engine and FastMCP server designed specifically for the VIT End-Semester Course Feedback portal (`https://vtopregcc.vit.ac.in/endfeedback/`).

It autonomously solves the portal's distorted text captcha, navigates both **Class-Wise Feedback** (theory and lab) and **Course Outcome Feedback** tables, applies configurable star ratings (defaulting to 5 stars for all questions, facilities, and outcomes), writes constructive suggestions, and submits every pending course while gracefully skipping already posted ones.

---

## Features

- **Full End-to-End Playwright Automation**: Interacts with the real portal UI, accurately selecting radio stars and filling textareas.
- **Autonomous Captcha Solving**: Built-in `ddddocr` recognition tested on live portal captchas with automatic retry and refresh on failure.
- **Agent-Ready FastMCP Server**: Standard tools (`vit_analyze_feedback`, `vit_submit_all_feedback`, `vit_submit_single_course`, `vit_logout`) over stdio for coupling with Claude, Cursor, Antigravity, or any AI agent.
- **Configurable Rating Policy**:
  - Default: 5 stars across the board for all questions and course outcomes.
  - Uniform rating: e.g. 3 stars or 4 stars for everything.
  - Granular overrides: per-course or per-class ratings (`--override BCSE301L=4`).
  - Independent Course Outcome ratings (`--co-rating 5`).
  - Constructive suggestions text.
- **Robust Edge Case Handling**:
  - **Multi-Tab Prevention**: Clears stale session cookies and storage to avoid the *"Multiple Tabs Access prevented !!!"* lock.
  - **Session Expired Navigation**: Handles initial GET redirections to the actual POST login page.
  - **Single-Page AJAX Navigation**: Synchronizes with jQuery `$.ajax` and waits for `$.blockUI` loading overlays before DOM actions.
  - **SweetAlert Dismissal**: Automatically handles and dismisses SweetAlert popups.
  - **NixOS & Linux Compatible**: Auto-detects system Chromium/Brave (`/run/current-system/sw/bin/brave`) without ELF patch errors.
- **Dry-Run & Inspection Modes**: Inspect courses and test ratings without submitting data.

---

## Installation

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `pip`
- Chromium or Brave browser

### Quick Setup

```bash
# Clone and enter directory
cd Vit_review_plyWrite

# Create virtualenv and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

On NixOS, simply run:
```bash
nix-shell
```

---

## CLI Usage

### 1. Dry Run / Status Inspection
Inspect enrolled courses, faculty names, and submission status without submitting anything:

```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>' --analyze-only
```

Or simulate filling ratings and comments in dry-run mode:
```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>' --dry-run
```

### 2. Submit 5-Star Reviews for Everything (Default)
Submits 5 stars for all questions, facility evaluations, and Course Outcomes across all pending courses:

```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>'
```

### 3. Give 3 Stars Everywhere
```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>' --rating 3
```

### 4. Custom Course Overrides
Give 4 stars by default, but give 5 stars to `BCSE204L` and 3 stars to `BCSE301L`:
```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>' --rating 4 --override BCSE204L=5 --override BCSE301L=3
```

### 5. Visible Browser Mode (Headed)
Watch the automation execute in real-time on your screen:
```bash
python -m vit_feedback -u <VTOP_USERNAME> -p '<VTOP_PASSWORD>' --no-headless
```

---

## MCP Server Integration (for AI Agents)

To couple this automation with any AI agent, configure the FastMCP server in your agent's MCP settings:

```json
{
  "mcpServers": {
    "vit-feedback": {
      "command": "/mnt/drive1/projects/Vit_review_plyWrite/.venv/bin/python",
      "args": ["-m", "vit_feedback.mcp_server"],
      "env": {
        "PYTHONPATH": "/mnt/drive1/projects/Vit_review_plyWrite/src"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `vit_analyze_feedback(username, password)` | Inspects all enrolled courses and returns pending vs posted summary. |
| `vit_submit_all_feedback(...)` | Submits feedback for all pending courses with customizable ratings and dry-run flag. |
| `vit_submit_single_course(...)` | Submits feedback for one specific course, class number, or faculty member. |
| `vit_logout()` | Safely terminates the browser session. |

---

## Testing

Run the full automated test suite:

```bash
pytest
```
