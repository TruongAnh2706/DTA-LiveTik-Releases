"""Unit tests for DTADeepSeekEngine and Multi-Provider AI Routing.

Tests DeepSeek V3 API connectivity, fallback to Qwen Local, and intent handling.
"""

import json
from unittest.mock import MagicMock, patch

from dta_autolive.infrastructure.dta_deepseek_engine import DTADeepSeekEngine
from dta_autolive.infrastructure.host_live_chat_responder import HostLiveChatResponder


def test_deepseek_engine_initialization() -> None:
    """Test engine initialization and API key configuration."""
    engine = DTADeepSeekEngine()
    assert not engine.is_configured
    assert engine.api_key == ""

    engine.set_api_key("sk-test-deepseek-12345")
    assert engine.is_configured
    assert engine.api_key == "sk-test-deepseek-12345"


def test_deepseek_engine_test_connection_empty() -> None:
    """Test connection without API key."""
    engine = DTADeepSeekEngine()
    res = engine.test_connection("")
    assert not res["success"]
    assert "Vui lòng nhập" in res["message"]


@patch("urllib.request.urlopen")
def test_deepseek_engine_test_connection_success(mock_urlopen: MagicMock) -> None:
    """Test successful API connection test."""
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps({"choices": [{"message": {"content": "DeepSeek V3 sẵn sàng!"}}]}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    engine = DTADeepSeekEngine(api_key="sk-valid-key")
    res = engine.test_connection()

    assert res["success"]
    assert "thành công" in res["message"]
    assert res["reply"] == "DeepSeek V3 sẵn sàng!"


@patch("urllib.request.urlopen")
def test_deepseek_engine_generate_response(mock_urlopen: MagicMock) -> None:
    """Test response generation via DeepSeek API."""
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = b'{"choices": [{"message": {"content": "D\xe1\xba\xa1 c\xe1\xba\xa7n 5H t\xe1\xba\xa3i c\xc3\xa1 3-5kg \xc3\xaam ru nh\xc3\xa1 b\xc3\xa1c!"}}]}'
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    engine = DTADeepSeekEngine(api_key="sk-valid-key")
    out = engine.generate_response(
        user_prompt="Cần 5H tải cá mấy kg shop",
        knowledge_catalog="Mã 1: Cần 5H 4m5",
    )
    assert "5H tải cá" in out or "3-5kg" in out


def test_host_responder_multi_provider_routing() -> None:
    """Test HostLiveChatResponder correctly routes between DeepSeek and Qwen."""
    mock_qwen = MagicMock()
    mock_qwen.is_loaded = True
    mock_qwen.llm = "ACTIVE_QWEN"
    mock_qwen.generate_response.return_value = "Phản hồi từ Qwen Local"

    mock_deepseek = MagicMock()
    mock_deepseek.is_configured = True
    mock_deepseek.generate_response.return_value = "Phản hồi từ DeepSeek V3"

    # 1. Test DeepSeek Mode
    responder = HostLiveChatResponder(
        qwen_engine=mock_qwen,
        deepseek_engine=mock_deepseek,
        ai_provider="deepseek",
    )
    res = responder._call_active_ai_engine("Hỏi giá mã 1")  # noqa: SLF001
    assert res == "Phản hồi từ DeepSeek V3"

    # 2. Test Qwen Local Mode
    responder.ai_provider = "qwen"
    res_qwen = responder._call_active_ai_engine("Hỏi giá mã 1")  # noqa: SLF001
    assert res_qwen == "Phản hồi từ Qwen Local"

    # 3. Test Auto / Hybrid with Fallback
    responder.ai_provider = "auto"
    mock_deepseek.generate_response.side_effect = Exception("Network timeout")
    res_fallback = responder._call_active_ai_engine("Hỏi giá mã 1")  # noqa: SLF001
    assert res_fallback == "Phản hồi từ Qwen Local"
