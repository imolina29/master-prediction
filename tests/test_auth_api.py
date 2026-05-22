from unittest.mock import patch

from backend.api.auth import API_KEYS, verify_api_key


def test_verify_valid_key():
    with patch.dict(API_KEYS, {"secret123": "pipeline"}, clear=True):
        assert verify_api_key("secret123") == "pipeline"


def test_verify_invalid_key():
    with patch.dict(API_KEYS, {"secret123": "pipeline"}, clear=True):
        assert verify_api_key("wrong") is None


def test_verify_empty():
    with patch.dict(API_KEYS, {}, clear=True):
        assert verify_api_key("anything") is None
