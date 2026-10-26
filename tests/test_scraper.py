import pytest
from unittest.mock import MagicMock
from vit_feedback.scraper import extract_dashboard_courses

SAMPLE_HTML = """
<div id="page-wrapper">
    <table class="w3-table-all">
        <thead>
            <tr><th colspan="15">FEEDBACK - CLASS WISE</th></tr>
            <tr>
                <th>Sl. No.</th><th>Class Nbr</th><th>Course Code</th><th>Course Title</th>
                <th>Course Type</th><th>L</th><th>T</th><th>P</th><th>J</th><th>C</th>
                <th>Course Option</th><th>Slot</th><th>Venue</th><th>Faculty Name</th><th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1.</td><td>CH2026270100925</td><td>BCSE204L</td><td>Design and Analysis of Algorithms</td>
                <td>Theory Only</td><td>3</td><td>0</td><td>0</td><td>0</td><td>3</td>
                <td>Regular</td><td>A1+TA1</td><td>AB3-406</td><td>SAKTHIVEL R</td>
                <td><span style="color:red;">Posted</span></td>
            </tr>
            <tr>
                <td>2.</td><td>CH2026270100928</td><td>BCSE204P</td><td>Design and Analysis of Algorithms Lab</td>
                <td>Lab Only</td><td>0</td><td>0</td><td>2</td><td>0</td><td>1</td>
                <td>Regular</td><td>L11+L12</td><td>AB3 - 412</td><td>SAKTHIVEL R</td>
                <td>
                    <button class="btn-warning" type="button" onclick="javascript:processCourseFeedbackPerception('CH_BCSE204P_00100','LO');">Post</button>
                </td>
            </tr>
        </tbody>
    </table>

    <table class="w3-table-all">
        <thead>
            <tr><th colspan="10">FEEDBACK - COURSE OUTCOME</th></tr>
            <tr>
                <th>Sl. No.</th><th>Course Code</th><th>Course Title</th><th>Generic Type</th>
                <th>L</th><th>T</th><th>P</th><th>J</th><th>C</th><th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1.</td><td>BCSE204L</td><td>Design and Analysis of Algorithms</td><td>TH</td>
                <td>3</td><td>0</td><td>0</td><td>0</td><td>3</td>
                <td>
                    <button class="btn-warning" type="button" onclick="javascript:processCourseOutcomeFeedbackPerception('CH_BCSE204L_00100');">Post</button>
                </td>
            </tr>
        </tbody>
    </table>
</div>
"""

def test_extract_dashboard_courses():
    mock_page = MagicMock()
    mock_page.content.return_value = SAMPLE_HTML
    mock_page.evaluate.return_value = None

    class_items, co_items = extract_dashboard_courses(mock_page)

    assert len(class_items) == 2
    assert class_items[0].course_code == "BCSE204L"
    assert class_items[0].is_posted is True
    assert class_items[1].course_code == "BCSE204P"
    assert class_items[1].is_pending is True
    assert class_items[1].course_id == "CH_BCSE204P_00100"
    assert class_items[1].param_type == "LO"

    assert len(co_items) == 1
    assert co_items[0].course_code == "BCSE204L"
    assert co_items[0].is_pending is True
    assert co_items[0].course_id == "CH_BCSE204L_00100"
