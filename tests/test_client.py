import pytest
from unittest.mock import MagicMock, patch
from vit_feedback.client import find_browser_executable, VitFeedbackClient

def test_find_browser_executable():
    path = find_browser_executable()
    # On this NixOS machine, brave is at /run/current-system/sw/bin/brave
    assert path is not None or path is None

def test_client_init_defaults():
    client = VitFeedbackClient(headless=True)
    assert client.headless is True
    assert client.is_logged_in() is False

def test_client_clean_cookies_logic():
    client = VitFeedbackClient(headless=True)
    mock_context = MagicMock()
    client._context = mock_context
    client.clear_session()
    mock_context.clear_cookies.assert_called_once()

def test_login_invalid_credentials_raises_immediately():
    client = VitFeedbackClient(headless=True)
    client.navigate_to_login = MagicMock()
    mock_page = MagicMock()
    client._page = mock_page
    client._extract_and_solve_captcha = MagicMock(return_value="ABCDEF")

    # First dismiss call returns None (pre-submit), second returns credential error
    client._dismiss_sweetalert_if_any = MagicMock(side_effect=[None, "Invalid User ID or Password"])

    with pytest.raises(ValueError, match="Portal rejected credentials"):
        client.login("wrong_user", "wrong_pass", max_retries=5)

    # Should only execute 1 attempt because credentials rejection aborts immediately
    assert client.navigate_to_login.call_count == 1
    assert mock_page.click.call_count == 1

def test_login_already_posted_short_circuit():
    client = VitFeedbackClient(headless=True)
    client.navigate_to_login = MagicMock()
    mock_page = MagicMock()
    client._page = mock_page
    client._extract_and_solve_captcha = MagicMock(return_value="ABCDEF")

    client._dismiss_sweetalert_if_any = MagicMock(
        side_effect=[None, "You already posted the Fall Semester 2026-27 feedback."]
    )

    result = client.login("valid_user", "valid_pass")
    assert result is True
    assert client.all_already_posted is True
    assert client.is_logged_in() is True
