import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock
import sys

# Mock the problematic packages before importing services.ai
sys.modules["google"] = Mock()
sys.modules["google.generativeai"] = Mock()
sys.modules["groq"] = Mock()

import services.ai

def _collect(gen):
    return "".join(gen)

def test_falls_back_to_groq_when_gemini_fails():
    with patch("services.ai._stream_gemini", side_effect=Exception("quota")):
        with patch("services.ai._stream_groq", return_value=iter(["groq response"])):
            result = _collect(services.ai.stream_response("test prompt"))
    assert "groq response" in result

def test_falls_back_to_static_when_both_fail():
    with patch("services.ai._stream_gemini", side_effect=Exception("quota")):
        with patch("services.ai._stream_groq", side_effect=Exception("rate limit")):
            result = _collect(services.ai.stream_response("test prompt"))
    assert "temporarily offline" in result.lower()

def test_gemini_used_first():
    with patch("services.ai._stream_gemini", return_value=iter(["gemini ok"])) as mock:
        result = _collect(services.ai.stream_response("test"))
    assert "gemini ok" in result
