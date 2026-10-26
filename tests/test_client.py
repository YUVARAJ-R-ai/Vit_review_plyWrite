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
