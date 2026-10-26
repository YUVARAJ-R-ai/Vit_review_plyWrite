import re
import logging
from typing import Tuple, List
from playwright.sync_api import Page

from vit_feedback.models import CourseItem

logger = logging.getLogger(__name__)

JS_SCRAPE_SCRIPT = """
(() => {
    const classWiseItems = [];
    const coItems = [];

    const tables = Array.from(document.querySelectorAll('table'));
    for (const table of tables) {
        const text = table.innerText || '';
        const headerText = table.querySelector('thead') ? table.querySelector('thead').innerText : '';
        
        if (headerText.includes('FEEDBACK - CLASS WISE') || text.includes('FEEDBACK - CLASS WISE')) {
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            for (const row of rows) {
                const cells = Array.from(row.querySelectorAll('td'));
                if (cells.length >= 6) {
                    const classNbr = cells[1].innerText.trim();
                    const courseCode = cells[2].innerText.trim();
                    const title = cells[3].innerText.trim();
                    const courseType = cells[4].innerText.trim();
                    const facultyName = cells.length >= 2 ? cells[cells.length - 2].innerText.trim() : '';
                    
                    const statusCell = cells[cells.length - 1];
                    const statusText = statusCell.innerText.trim();
                    const postBtn = statusCell.querySelector('button');
                    
                    let courseId = '';
                    let paramType = '';
                    if (postBtn) {
                        const onclick = postBtn.getAttribute('onclick') || '';
                        const match = onclick.match(/processCourseFeedbackPerception\\s*\\(\\s*['"]([^'"]+)['"]\\s*,\\s*['"]([^'"]+)['"]\\s*\\)/);
                        if (match) {
                            courseId = match[1];
                            paramType = match[2];
                        }
                    }

                    classWiseItems.push({
                        class_nbr: classNbr,
                        course_code: courseCode,
                        title: title,
                        course_type: courseType,
                        faculty_name: facultyName,
                        status: statusText || (postBtn ? 'Pending' : 'Posted'),
                        table_type: 'class_wise',
                        course_id: courseId,
                        param_type: paramType
                    });
                }
            }
        } else if (headerText.includes('FEEDBACK - COURSE OUTCOME') || text.includes('FEEDBACK - COURSE OUTCOME')) {
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            for (const row of rows) {
                const cells = Array.from(row.querySelectorAll('td'));
                if (cells.length >= 8) {
                    const courseCode = cells[1].innerText.trim();
                    const title = cells[2].innerText.trim();
                    const genericType = cells[3].innerText.trim();

                    const statusCell = cells[cells.length - 1];
                    const statusText = statusCell.innerText.trim();
                    const postBtn = statusCell.querySelector('button');

                    let courseId = '';
                    if (postBtn) {
                        const onclick = postBtn.getAttribute('onclick') || '';
                        const match = onclick.match(/processCourseOutcomeFeedbackPerception\\s*\\(\\s*['"]([^'"]+)['"]\\s*\\)/);
                        if (match) {
                            courseId = match[1];
                        }
                    }

                    coItems.push({
                        class_nbr: '',
                        course_code: courseCode,
                        title: title,
                        course_type: genericType,
                        faculty_name: '',
                        status: statusText || (postBtn ? 'Pending' : 'Posted'),
                        table_type: 'course_outcome',
                        course_id: courseId,
                        param_type: ''
                    });
                }
            }
        }
    }

    return { classWiseItems, coItems };
})()
"""

def extract_from_html(html: str) -> Tuple[List[CourseItem], List[CourseItem]]:
    """Fallback regex/string extraction from raw HTML if evaluate is mocked or not a browser page."""
    class_items = []
    co_items = []

    # Parse tables
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
    for tbl in tables:
        if "FEEDBACK - CLASS WISE" in tbl:
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', tbl, re.DOTALL | re.IGNORECASE)
            tbody = tbody_match.group(1) if tbody_match else tbl
            rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL | re.IGNORECASE)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if len(cells) >= 6:
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    class_nbr = clean_cells[1]
                    course_code = clean_cells[2]
                    title = clean_cells[3]
                    course_type = clean_cells[4]
                    faculty_name = clean_cells[-2] if len(clean_cells) >= 2 else ""
                    status_text = clean_cells[-1]

                    match = re.search(r"processCourseFeedbackPerception\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", cells[-1])
                    course_id = match.group(1) if match else ""
                    param_type = match.group(2) if match else ""

                    status = "Posted" if "posted" in status_text.lower() else "Pending"
                    class_items.append(CourseItem(
                        class_nbr=class_nbr,
                        course_code=course_code,
                        title=title,
                        course_type=course_type,
                        faculty_name=faculty_name,
                        status=status,
                        table_type="class_wise",
                        course_id=course_id,
                        param_type=param_type
                    ))
        elif "FEEDBACK - COURSE OUTCOME" in tbl:
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', tbl, re.DOTALL | re.IGNORECASE)
            tbody = tbody_match.group(1) if tbody_match else tbl
            rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL | re.IGNORECASE)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if len(cells) >= 8:
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    course_code = clean_cells[1]
                    title = clean_cells[2]
                    generic_type = clean_cells[3]
                    status_text = clean_cells[-1]

                    match = re.search(r"processCourseOutcomeFeedbackPerception\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", cells[-1])
                    course_id = match.group(1) if match else ""

                    status = "Posted" if "posted" in status_text.lower() else "Pending"
                    co_items.append(CourseItem(
                        class_nbr="",
                        course_code=course_code,
                        title=title,
                        course_type=generic_type,
                        faculty_name="",
                        status=status,
                        table_type="course_outcome",
                        course_id=course_id,
                        param_type=""
                    ))

    return class_items, co_items

def extract_dashboard_courses(page: Page) -> Tuple[List[CourseItem], List[CourseItem]]:
    """Extract all courses from Table 1 and Table 2 on the dashboard."""
    try:
        data = page.evaluate(JS_SCRAPE_SCRIPT)
        if data and isinstance(data, dict) and (data.get("classWiseItems") or data.get("coItems")):
            class_items = [CourseItem(**item) for item in data.get("classWiseItems", [])]
            co_items = [CourseItem(**item) for item in data.get("coItems", [])]
            return class_items, co_items
    except Exception as e:
        logger.debug("Page evaluation failed or mocked: %s", e)

    # Fallback to HTML parsing
    html = page.content() if hasattr(page, "content") else ""
    return extract_from_html(html)
