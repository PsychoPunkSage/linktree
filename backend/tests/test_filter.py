import pytest
from unittest.mock import patch, MagicMock

def test_hard_filter_blocks_obscene():
    from services.filter import classify
    result = classify("send me nudes")
    assert result == "HARD"

def test_soft_filter_blocks_out_of_scope():
    from services.filter import classify
    with patch("services.filter._ai_classify", return_value="SOFT"):
        result = classify("what is the capital of France?")
    assert result == "SOFT"

def test_pass_for_relevant_question():
    from services.filter import classify
    with patch("services.filter._ai_classify", return_value="PASS"):
        result = classify("what kernel modules have you written?")
    assert result == "PASS"

def test_hard_filter_is_checked_before_ai_call():
    from services.filter import classify
    with patch("services.filter._ai_classify") as mock_ai:
        classify("fuck you")
        mock_ai.assert_not_called()
