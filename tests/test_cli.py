import pytest
from unittest.mock import MagicMock
from vit_feedback.cli import build_parser, run_cli
from vit_feedback.models import FeedbackResult

def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--username", "testuser", "--password", "testpass"])
    assert args.username == "testuser"
    assert args.password == "testpass"
    assert args.rating == 5
    assert args.dry_run is False
    assert args.headless is True

def test_build_parser_options():
    parser = build_parser()
    args = parser.parse_args([
        "--username", "u",
        "--password", "p",
        "--rating", "3",
        "--co-rating", "5",
        "--dry-run",
        "--no-headless",
        "--override", "BCSE301L=4"
    ])
    assert args.rating == 3
    assert args.co_rating == 5
    assert args.dry_run is True
    assert args.headless is False
    assert args.override == ["BCSE301L=4"]

def test_run_cli_dry_run(monkeypatch):
    mock_client = MagicMock()
    mock_client.login.return_value = True
    mock_page = MagicMock()
    mock_client.get_page.return_value = mock_page

    monkeypatch.setattr("vit_feedback.cli.VitFeedbackClient", lambda **kw: mock_client)
    monkeypatch.setattr(
        "vit_feedback.cli.process_all_feedback",
        lambda page, policy, dry_run: FeedbackResult(status="success", processed_courses=["BCSE204L"], message="Done")
    )
    monkeypatch.setattr(
        "vit_feedback.cli.extract_dashboard_courses",
        lambda page: ([], [])
    )

    code = run_cli(["--username", "u", "--password", "p", "--dry-run"])
    assert code == 0
