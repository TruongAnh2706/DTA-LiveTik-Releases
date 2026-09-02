"""Unit tests for Dynamic Host Prompt Template & 3 Variable Injection System.

Tests {{Thong tin nen tang}}, {{List san pham}}, {{Quy tac}} replacement and AI generation.
"""

from unittest.mock import MagicMock

from dta_autolive.infrastructure.host_live_chat_responder import (
    DEFAULT_DYNAMIC_HOST_PROMPT,
    HostLiveChatResponder,
)


def test_dynamic_prompt_variable_replacement() -> None:
    """Test replacing {{Thong tin nen tang}}, {{List san pham}}, {{Quy tac}}."""
    responder = HostLiveChatResponder()

    custom_cart = [
        {"stt": 1, "name": "Cần Câu Handing 5H", "sale_price": "350.000đ", "stock": "50 cái"},
        {"stt": 2, "name": "Phao Đài Nano", "sale_price": "45.000đ", "stock": "100 cái"},
    ]
    responder.products_catalog = custom_cart

    custom_plat = "Freeship toàn quốc từ 200k. Đổi trả 7 ngày."
    custom_rules = "Tuyệt đối không nói tục. Xưng em gọi anh/chị."

    built_prompt = responder.build_system_prompt_from_template(
        template=DEFAULT_DYNAMIC_HOST_PROMPT,
        platform_info=custom_plat,
        products=custom_cart,
        rules=custom_rules,
    )

    # Verify variables are substituted
    assert "{{Thong tin nen tang}}" not in built_prompt
    assert "{{List san pham}}" not in built_prompt
    assert "{{Quy tac}}" not in built_prompt

    assert "Freeship toàn quốc từ 200k" in built_prompt
    assert "Cần Câu Handing 5H" in built_prompt
    assert "Phao Đài Nano" in built_prompt
    assert "Tuyệt đối không nói tục" in built_prompt


def test_dynamic_prompt_case_insensitive_placeholders() -> None:
    """Test placeholder matching regardless of casing and accents."""
    responder = HostLiveChatResponder()
    template = "INFO: {{thong_tin_nen_tang}} | PRODS: {{LIST_SAN_PHAM}} | RULES: {{quy_tac}}"

    custom_plat = "Chính sách bảo hành 12 tháng"
    custom_rules = "Quy tắc cấm nhắc sàn khác"
    custom_cart = [{"stt": 5, "name": "Máy Câu Kim Loại", "sale_price": "220.000đ"}]

    out = responder.build_system_prompt_from_template(
        template=template,
        platform_info=custom_plat,
        products=custom_cart,
        rules=custom_rules,
    )

    assert "Chính sách bảo hành 12 tháng" in out
    assert "Máy Câu Kim Loại" in out
    assert "Quy tắc cấm nhắc sàn khác" in out


def test_host_responder_set_prompt_configuration() -> None:
    """Test set_prompt_configuration updates state and system prompt."""
    responder = HostLiveChatResponder()
    responder.set_prompt_configuration(
        prompt_template="Xin chào! {{Thong tin nen tang}} - {{List san pham}} - {{Quy tac}}",
        platform_info="Shop Hà Nội",
        rules="Luôn mỉm cười",
    )

    assert responder.platform_info == "Shop Hà Nội"
    assert responder.rules == "Luôn mỉm cười"
    assert "Shop Hà Nội" in responder.system_prompt
    assert "Luôn mỉm cười" in responder.system_prompt


def test_ai_engine_invocation_receives_dynamic_prompt() -> None:
    """Test that DeepSeek or Qwen receives the dynamic system prompt."""
    mock_deepseek = MagicMock()
    mock_deepseek.is_configured = True
    mock_deepseek.generate_response.return_value = "Dạ mã 1 giá 350k freeship bác nha!"

    responder = HostLiveChatResponder(
        deepseek_engine=mock_deepseek,
        ai_provider="deepseek",
    )
    responder.products_catalog = [{"stt": 1, "name": "Cần 5H", "sale_price": "350.000đ"}]
    responder.set_prompt_configuration(
        platform_info="Giao hàng 2 ngày",
        rules="Luôn dạ thưa",
    )

    res = responder._call_active_ai_engine("Khách hỏi: Mã 1 giá bao nhiêu?")  # noqa: SLF001
    assert res == "Dạ mã 1 giá 350k freeship bác nha!"

    # Verify the system prompt sent to deepseek contains the formatted dynamic variables
    call_args = mock_deepseek.generate_response.call_args
    assert call_args is not None
    system_sent = call_args.kwargs.get("system_prompt", "")
    assert "Giao hàng 2 ngày" in system_sent
    assert "Luôn dạ thưa" in system_sent
    assert "Cần 5H" in system_sent


def test_anti_duplicate_replies_loop_prevention() -> None:
    """Verify that a customer comment is only queued and answered ONCE, blocking duplicates 2-3-4 times."""
    responder = HostLiveChatResponder()
    responder.is_running = True

    # 1. First time comment is received
    responder.enqueue_comment("Nguyen_Van_A", "Cần 5H bao nhiêu tiền?")
    assert responder._reply_queue.qsize() == 1  # noqa: SLF001

    # 2. Same comment received 2nd, 3rd, 4th time (from network retry or DOM rescan)
    responder.enqueue_comment("Nguyen_Van_A", "Cần 5H bao nhiêu tiền?")
    responder.enqueue_comment("Nguyen_Van_A", "Cần 5H bao nhiêu tiền?")
    responder.enqueue_comment("Nguyen_Van_A", "cần 5h bao nhiêu tiền?")
    assert responder._reply_queue.qsize() == 1  # Still exactly 1, completely blocked! # noqa: SLF001

    # 3. Simulate reply completed and recorded in fingerprint
    fp = "nguyen_van_a::cần 5h bao nhiêu tiền?"
    responder._replied_comment_fingerprints.add(fp)  # noqa: SLF001
    responder._in_progress_comments.discard(fp)  # noqa: SLF001

    # 4. Try sending the same comment again after reply is done
    responder.enqueue_comment("Nguyen_Van_A", "Cần 5H bao nhiêu tiền?")
    assert responder._reply_queue.qsize() == 1  # Blocked forever! # noqa: SLF001

    # 5. Customer asks a genuinely NEW question -> Allowed!
    responder.enqueue_comment("Nguyen_Van_A", "Shop có tặng kèm ngọn phụ không?")
    assert responder._reply_queue.qsize() == 2  # New question accepted! # noqa: SLF001


def test_customer_registry_tracking() -> None:
    """Verify customer state tracking: PENDING -> PROCESSING -> REPLIED."""
    responder = HostLiveChatResponder()
    responder.is_running = True

    responder.enqueue_comment("Can_Thu_SG", "Phao đài mã 2 bao nhiêu?")
    reg = responder._customer_registry.get("can_thu_sg")  # noqa: SLF001
    assert reg is not None
    assert reg["nickname"] == "Can_Thu_SG"
    assert reg["status"] == "PENDING"
    assert reg["total_comments"] == 1

    summary = responder.get_customer_tracking_summary()
    assert len(summary) == 1
    assert summary[0]["status"] == "PENDING"

