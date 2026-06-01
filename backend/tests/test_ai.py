import pytest
from unittest.mock import patch, Mock
import sys

# Mock the problematic packages before importing services.ai
sys.modules["google"] = Mock()
sys.modules["google.generativeai"] = Mock()
sys.modules["groq"] = Mock()

import services.ai

def _collect(gen):
    return "".join(gen)

@pytest.fixture(autouse=True)
def reset_key_state():
    services.ai._key_state = {"gemini": 0, "groq": 0}

@pytest.fixture
def mock_settings():
    fake = Mock()
    fake.gemini_api_keys = ["gemini-key-1", "gemini-key-2"]
    fake.groq_api_keys   = ["groq-key-1",   "groq-key-2"]
    with patch("services.ai.settings", fake):
        yield fake


# --- existing fallback chain tests (updated for list-based settings) ---

def test_gemini_used_first(mock_settings):
    with patch("services.ai._stream_gemini", return_value=iter(["gemini ok"])):
        result = _collect(services.ai.stream_response("test"))
    assert "gemini ok" in result

def test_falls_back_to_groq_when_gemini_fails(mock_settings):
    with patch("services.ai._stream_gemini", side_effect=Exception("quota")):
        with patch("services.ai._stream_groq", return_value=iter(["groq response"])):
            result = _collect(services.ai.stream_response("test prompt"))
    assert "groq response" in result

def test_falls_back_to_static_when_both_fail(mock_settings):
    with patch("services.ai._stream_gemini", side_effect=Exception("quota")):
        with patch("services.ai._stream_groq", side_effect=Exception("rate limit")):
            result = _collect(services.ai.stream_response("test prompt"))
    assert "temporarily offline" in result.lower()


# --- key rotation tests ---

def test_rotates_to_second_gemini_key_on_failure(mock_settings):
    calls = []
    def fake_gemini(prompt, key):
        calls.append(key)
        if key == "gemini-key-1":
            raise Exception("rate limit")
        return iter(["gemini ok"])

    with patch("services.ai._stream_gemini", side_effect=fake_gemini):
        result = _collect(services.ai.stream_response("test"))

    assert "gemini ok" in result
    assert calls == ["gemini-key-1", "gemini-key-2"]

def test_rotates_to_second_groq_key_on_failure(mock_settings):
    calls = []
    def fake_groq(prompt, key):
        calls.append(key)
        if key == "groq-key-1":
            raise Exception("rate limit")
        return iter(["groq ok"])

    with patch("services.ai._stream_gemini", side_effect=Exception("all gemini fail")):
    	with patch("services.ai._stream_groq", side_effect=fake_groq):
            result = _collect(services.ai.stream_response("test"))

    assert "groq ok" in result
    assert calls == ["groq-key-1", "groq-key-2"]

def test_falls_back_to_groq_when_all_gemini_keys_fail(mock_settings):
    with patch("services.ai._stream_gemini", side_effect=Exception("exhausted")):
        with patch("services.ai._stream_groq", return_value=iter(["groq saved it"])):
            result = _collect(services.ai.stream_response("test"))
    assert "groq saved it" in result

def test_key_state_persists_across_requests(mock_settings):
    """Successful key remembered; next request starts from it."""
    calls = []
    def fake_gemini(prompt, key):
        calls.append(key)
        if key == "gemini-key-1" and len(calls) == 1:
            raise Exception("rate limit")
        return iter(["ok"])

    with patch("services.ai._stream_gemini", side_effect=fake_gemini):
        _collect(services.ai.stream_response("first"))
        _collect(services.ai.stream_response("second"))

    # first request: tried key-1 (failed), key-2 (succeeded)
    # second request: should start from key-2 directly
    assert calls == ["gemini-key-1", "gemini-key-2", "gemini-key-2"]

def test_empty_keys_falls_through_to_static(mock_settings):
    mock_settings.gemini_api_keys = []
    mock_settings.groq_api_keys   = []
    result = _collect(services.ai.stream_response("test"))
    assert "temporarily offline" in result.lower()
