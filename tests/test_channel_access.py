from unittest.mock import MagicMock, patch

import pytest

from backend.subscriptions.channel import ChannelManager


@pytest.fixture
def manager():
    return ChannelManager(
        bot_token="test_token",
        premium_channel_id="-1001234567890",
    )


@patch("backend.subscriptions.channel.httpx.post")
def test_create_invite_link(mock_post, manager):
    mock_post.return_value = MagicMock(
        json=lambda: {"ok": True, "result": {"invite_link": "https://t.me/+abc123"}}
    )

    link = manager.create_invite_link()
    assert link == "https://t.me/+abc123"
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["chat_id"] == "-1001234567890"
    assert call_json["member_limit"] == 1


@patch("backend.subscriptions.channel.httpx.post")
def test_send_invite_to_user(mock_post, manager):
    mock_post.return_value = MagicMock(
        json=lambda: {"ok": True, "result": {"invite_link": "https://t.me/+abc123"}}
    )

    manager.send_invite_to_user("12345")
    assert mock_post.call_count == 2  # createChatInviteLink + sendMessage


@patch("backend.subscriptions.channel.httpx.post")
def test_revoke_user_access(mock_post, manager):
    mock_post.return_value = MagicMock(json=lambda: {"ok": True})

    manager.revoke_user_access("12345")
    assert mock_post.call_count == 3  # banChatMember + unbanChatMember + sendMessage


@patch("backend.subscriptions.channel.httpx.post")
def test_send_admin_notification(mock_post, manager):
    manager.admin_chat_id = "-100admin"
    mock_post.return_value = MagicMock(json=lambda: {"ok": True})

    manager.send_admin_notification("Test message")
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["chat_id"] == "-100admin"
