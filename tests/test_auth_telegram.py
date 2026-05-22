from unittest.mock import patch

from backend.notifications.auth_telegram import get_authorized_chats, is_authorized_chat


def test_authorized_chats_from_list():
    with patch.dict("os.environ", {"TELEGRAM_AUTHORIZED_CHATS": "111,222,333"}, clear=False):
        chats = get_authorized_chats()
        assert chats == {"111", "222", "333"}


def test_authorized_chats_fallback_single():
    env = {"TELEGRAM_CHAT_ID": "999"}
    with patch.dict("os.environ", env, clear=True):
        chats = get_authorized_chats()
        assert chats == {"999"}


def test_authorized_chats_empty():
    with patch.dict("os.environ", {}, clear=True):
        chats = get_authorized_chats()
        assert chats == set()


def test_is_authorized():
    with patch.dict("os.environ", {"TELEGRAM_AUTHORIZED_CHATS": "111,222"}, clear=False):
        assert is_authorized_chat("111") is True
        assert is_authorized_chat(222) is True
        assert is_authorized_chat("999") is False
