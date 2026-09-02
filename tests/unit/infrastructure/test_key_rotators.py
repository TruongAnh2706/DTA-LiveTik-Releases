"""Unit tests for Gemini and DeepSeek API Key Rotators."""

from __future__ import annotations

from dta_autolive.infrastructure.ai_responder import DeepSeekKeyRotator, GeminiKeyRotator


def test_gemini_key_rotator() -> None:
    """Test Gemini key rotator behavior on rate limit."""
    keys = ["key_1", "key_2", "key_3"]
    rotator = GeminiKeyRotator(keys)

    assert rotator.get_active_key() == "key_1"
    rotator.rotate_key("HTTP 429")
    assert rotator.get_active_key() == "key_2"
    rotator.rotate_key("HTTP 429")
    assert rotator.get_active_key() == "key_3"
    rotator.rotate_key("HTTP 429")
    assert rotator.get_active_key() == "key_1"


def test_deepseek_key_rotator() -> None:
    """Test DeepSeek key rotator behavior on rate limit."""
    keys = ["ds_key_a", "ds_key_b"]
    rotator = DeepSeekKeyRotator(keys)

    assert rotator.get_active_key() == "ds_key_a"
    rotator.rotate_key("HTTP 429 Rate Limit")
    assert rotator.get_active_key() == "ds_key_b"
    rotator.rotate_key("HTTP 429 Rate Limit")
    assert rotator.get_active_key() == "ds_key_a"
