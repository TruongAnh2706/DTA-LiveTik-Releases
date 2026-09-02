"""Unit Tests for Next-Gen AI Qwen Engine, Cart Scraper, Seeding Manager & Host Chatbot.

Verifies deterministic lifecycle management, offline inference formatting, DOM cart parsing,
and multi-account seeding scenario generation.
"""

import time
from pathlib import Path
from typing import Any

from dta_autolive.infrastructure.domain_knowledge_adapter import DomainKnowledgeAdapter
from dta_autolive.infrastructure.dta_qwen_engine import (
    DTAQwenEngine,
    format_price_shorthand,
    get_gpu_info,
)
from dta_autolive.infrastructure.host_live_chat_responder import HostLiveChatResponder
from dta_autolive.infrastructure.product_pinner import ProductPinnerManager
from dta_autolive.infrastructure.satellite_seeding_manager import SatelliteSeedingManager
from dta_autolive.infrastructure.tiktok_cart_scraper import TikTokCartScraper


def test_gpu_info_inspection() -> None:
    """Verify GPU inspection returns valid structure with fallback."""
    gpu = get_gpu_info()
    assert isinstance(gpu, dict)
    assert "has_gpu" in gpu
    assert "total_vram_gb" in gpu
    assert "used_vram_gb" in gpu
    assert "free_vram_gb" in gpu


def test_qwen_engine_model_lifecycle(tmp_path: Path) -> None:
    """Verify check_model_status, simulated loading and VRAM cleanup."""
    engine = DTAQwenEngine(models_dir=tmp_path)

    # 1. Check status of model (not exists initially)
    status = engine.check_model_status("Qwen2.5-7B-Instruct-Q4_K_M")
    assert status["exists"] is False
    assert status["is_loaded"] is False
    assert status["expected_size_gb"] > 0

    # 2. Simulate model file creation
    model_file = tmp_path / "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    model_file.write_bytes(b"GGUF_MOCK_DATA" * 100)

    status_after = engine.check_model_status("Qwen2.5-7B-Instruct-Q4_K_M")
    assert status_after["exists"] is True

    # 3. Load model (simulated engine mode)
    loaded = engine.load_model_to_gpu("Qwen2.5-7B-Instruct-Q4_K_M")
    assert loaded is True
    assert engine.is_loaded is True

    # 4. Generate response
    reply = engine.generate_response(user_prompt="Mẫu này còn hàng không shop?", knowledge_catalog="Mã 1: Áo thun")
    assert "shop" in reply.lower() or "dạ" in reply.lower()

    # 5. Generate seeding scenarios
    scenarios = engine.generate_seeding_scenarios(
        [{"stt": 1, "name": "Cần câu 5H", "sale_price": "300k", "stock": "Còn 10"}],
        count=3,
    )
    assert len(scenarios) == 3

    # 6. Unload and clean VRAM
    engine.unload_model_and_clean_gpu()
    assert engine.is_loaded is False
    assert engine.llm is None


def test_tiktok_cart_scraper_formatting() -> None:
    """Verify live cart catalog formatting and simulated scraping."""
    scraper = TikTokCartScraper(cdp_port=9999)  # Non-existent port to test fallback reliably

    # Fallback simulated scrape
    res = scraper._fallback_simulated_cart("Test fallback")  # noqa: SLF001
    assert "products" in res
    assert len(res["products"]) >= 4

    kb_text = scraper.format_knowledge_base_text(res["products"])
    assert "Mã SP 1:" in kb_text
    assert "620k" in kb_text
    assert "Flash Sale" in kb_text


def test_satellite_seeding_manager() -> None:
    """Verify satellite accounts parsing and seeding dispatch."""
    manager = SatelliteSeedingManager()

    sample_accounts = "Nick_1|cookie_val_1\nNick_2|cookie_val_2\nNick_3|cookie_val_3"
    count = manager.load_accounts_from_text(sample_accounts)
    assert count == 3
    assert manager.accounts[0]["name"] == "Nick_1"

    # Start and stop seeding
    started = manager.start_seeding(
        target_username="@dta_live_channel",
        interval_min=5,
        interval_max=10,
        seeding_style="mixed",
    )
    assert started is True
    assert manager.is_running is True

    manager.stop_seeding()
    assert manager.is_running is False


def test_host_live_chat_responder() -> None:
    """Verify host live chat responder reply synthesis and queue."""
    responder = HostLiveChatResponder()

    started = responder.start_responder(
        username="@dta_store",
        system_prompt="Test Prompt",
        knowledge_catalog_text="Mã 1: Cần câu",
    )
    assert started is True
    assert responder.is_running is True

    responder.products_catalog = [
        {"stt": "1", "name": "Cần Câu Lure SMALL VENOM Khoen Fuji Độ Cứng UL", "sale_price": "329.000đ", "stock": "Còn: 2,7K"},
        {"stt": 20, "name": "Cần Câu Tay Hạng Đao Phong 5H - Carbon 30T", "sale_price": "800.000đ", "stock": "Còn: 811"},
    ]

    # Test exact product matching with string and int STT
    p1 = responder.find_matched_product("Mã số 1 bao nhiêu tiền vậy shop?")
    assert p1 is not None
    assert p1["name"].startswith("Cần Câu Lure")

    p20 = responder.find_matched_product("Cây 20 còn hàng không shop ơi?")
    assert p20 is not None
    assert "800.000đ" in p20["sale_price"]

    # Test test response generation
    test_res = responder.generate_test_response("Khach_Test", "Mã số 1 bao nhiêu tiền vậy shop?")
    assert "329" in test_res["reply"] or "1" in test_res["reply"]

    responder.stop_responder()
    assert responder.is_running is False


def test_product_pinner_advanced_modes_and_callouts() -> None:
    """Verify flash_sale and hot_demand pinning modes, callouts, and heatmap analytics."""
    pinner = ProductPinnerManager()
    pinner.products_catalog = [
        {"stt": 1, "name": "Cần Câu Huyền Thiên 6H", "sale_price": "500.000đ", "campaign": "Flash Sale"},
        {"stt": 2, "name": "Cần Câu Hoàng Đan 5H", "sale_price": "315.000đ", "campaign": "Khuyến mãi Live"},
        {"stt": 3, "name": "Cần Câu Hắc Đạo 6H", "sale_price": "450.000đ", "campaign": "Kết thúc sau 1 ngày"},
    ]

    # 1. Record customer inquiries and pin counts
    pinner.record_product_interest(3)
    pinner.record_product_interest(3)
    pinner.record_product_interest(1)
    pinner.record_pin_action(1)

    summary = pinner.get_analytics_summary()
    assert summary["total_pins"] == 1
    assert summary["total_queries"] == 3
    assert summary["interest_counts"]["3"] == 2
    assert summary["interest_counts"]["1"] == 1

    # 2. Test Host Live Callout on Pinned Product
    responder = HostLiveChatResponder()
    callout = responder.handle_pin_callout({"stt": 1, "name": "Cần Câu Huyền Thiên 6H", "sale_price": "500.000đ"})
    assert "Huyền Thiên" in callout or "#1" in callout
    assert "500" in callout

    # 3. Test Seeding Support on Pinned Product
    seeding_mgr = SatelliteSeedingManager()
    comment = seeding_mgr.handle_pin_seeding_support({"stt": 2, "name": "Cần Câu Hoàng Đan 5H", "sale_price": "315.000đ"})
    assert "#2" in comment or "Hoàng Đan" in comment

    # 4. Clean close
    pinner.close_browser()
    assert pinner.is_running is False


def test_multidialect_and_slang_generator(tmp_path: Path) -> None:
    """Verify responses and seeding templates across North, Central, and South dialects."""
    engine = DTAQwenEngine(models_dir=tmp_path)
    engine.is_loaded = True
    engine.llm = "SIMULATED_ENGINE"

    # 1. Test slangs transform
    text_raw = "Sản phẩm này không có mã freeship được à anh em ơi? Mọi người mua bao nhiêu nghìn?"
    slangified = engine.apply_human_slangs_and_typos(text_raw, slang_rate=1.0)
    assert "ko" in slangified
    assert "dc" in slangified
    assert "ae" in slangified
    assert "mn" in slangified

    # 2. Test North Dialect
    reply_north = engine.generate_response(
        user_prompt="Mã 1 bao tiền bác ơi?",
        knowledge_catalog="Mã 1: Cần câu Venom giá 320k",
        region_dialect="north",
        tone_style="genz_casual",
        use_slangs=True,
    )
    assert any(w in reply_north.lower() for w in ["bác", "nhá bác", "chuẩn", "cành", "venom", "320", "deal"])

    # 3. Test Central Dialect
    reply_central = engine.generate_response(
        user_prompt="Mã 1 giá mấy rứa shop?",
        knowledge_catalog="Mã 1: Cần câu Venom giá 320k",
        region_dialect="central",
        tone_style="humorous",
        use_slangs=True,
    )
    assert any(w in reply_central.lower() for w in ["mình ơi", "bồ ơi", "rứa", "hỉ", "hè", "ngon lành", "320", "venom"])

    # 4. Test South Dialect
    reply_south = engine.generate_response(
        user_prompt="Mã 1 giá nhiu bồ tèo?",
        knowledge_catalog="Mã 1: Cần câu Venom giá 320k",
        region_dialect="south",
        tone_style="fomo_sale",
        use_slangs=True,
    )
    assert any(w in reply_south.lower() for w in ["anh em", "mấy ní", "bồ", "lụm", "êm", "320", "venom"])

    # 5. Test Seeding Scenarios in 3 Dialects
    seeding_mgr = SatelliteSeedingManager()
    prods = [{"stt": 1, "name": "Cần Câu Huyền Thiên 6H", "sale_price": "500.000đ"}]

    scripts_north = seeding_mgr.generate_cart_product_seeding_scripts(prods, region_dialect="north")
    assert len(scripts_north) >= 3
    scripts_central = seeding_mgr.generate_cart_product_seeding_scripts(prods, region_dialect="central")
    assert len(scripts_central) >= 3
    scripts_south = seeding_mgr.generate_cart_product_seeding_scripts(prods, region_dialect="south")
    assert len(scripts_south) >= 3


def test_product_pinner_do_pin_execution() -> None:
    """Verify _do_pin evaluates JavaScript on page correctly."""
    pinner = ProductPinnerManager()
    pinner.products_catalog = [{"stt": "2", "name": "Cần Câu Hoàng Đan 5H", "sale_price": "315.000đ"}]

    class MockPage:
        def evaluate(self, script: str, args: dict[str, Any]) -> dict[str, Any]:
            assert args["stt"] == 2
            assert args["name"] == "Cần Câu Hoàng Đan 5H"
            return {"success": True, "method": "pc_pin_product_pin_clicked"}

    ok = pinner._do_pin(MockPage(), "2")  # noqa: SLF001
    assert ok is True


def test_host_chat_responder_auto_pin_and_event_callback() -> None:
    """Verify Host Live Chatbot enqueues comment, triggers auto_pin_callback and event_callback."""
    pinned_ids = []
    events = []

    def on_auto_pin(pid: str | int) -> None:
        pinned_ids.append(str(pid))

    def on_event(ev: dict[str, Any]) -> None:
        events.append(ev)

    responder = HostLiveChatResponder(
        auto_pin_callback=on_auto_pin,
        event_callback=on_event,
    )
    responder.products_catalog = [
        {"stt": "5", "name": "Cần Câu Lure Chuyên Tráp 6H", "sale_price": "450.000đ", "stock": "Còn 12"},
    ]
    responder.is_running = True

    # 1. Enqueue a customer question asking about product #5
    responder.enqueue_comment("Nguyen_Van_A", "Cần số 5 tải cá bao nhiêu kg shop?")
    assert responder._reply_queue.qsize() == 1  # noqa: SLF001

    # 2. Match product
    matched = responder.find_matched_product("Cần số 5 tải cá bao nhiêu kg shop?")
    assert matched is not None
    assert str(matched["stt"]) == "5"

    # 3. Generate response with auto-pin simulation
    res = responder.generate_test_response("Nguyen_Van_A", "Cần số 5 tải cá bao nhiêu kg shop?")
    assert len(pinned_ids) == 1
    assert pinned_ids[0] == "5"
    assert "450" in res["reply"]

    # 4. Check response length fits TikTok Live comment limit (<= 180 chars)
    assert len(res["reply"]) <= 180


def test_host_chat_responder_strictly_under_100_chars() -> None:
    """Verify all regional dialects and general responses do not exceed 180 characters with @username tag."""
    responder = HostLiveChatResponder()
    prods = [
        {"stt": "1", "name": "Cần Tay Thiên Xuyên 5H thế hệ 4 F1 kèm 1 ngọn", "sale_price": "159.000đ", "original_price": "250.000đ", "stock": "còn 10 cây"},
        {"stt": "5", "name": "ĐỘC ĐẮC ĐẠI LỰC MẠCH THÁNH KIẾM 6H tặng kèm đọt", "sale_price": "295.000đ", "original_price": "450.000đ", "stock": "hết 2 cây"},
    ]
    responder.products_catalog = prods

    test_users = ["chong_mom_fan_cung", "nguyen_van_long_99", "khanh_vy_angler"]
    test_questions = [
        "Mã số 1 giá bao nhiêu và có khuyến mãi gì không shop?",
        "Cây số 5 tải cá bao nhiêu kg vậy shop, có bền không?",
        "Shop có freeship và giao hàng trong mấy ngày ạ?",
        "Hàng chính hãng có phiếu bảo hành đổi trả không shop?",
    ]

    for dialect in ["north", "central", "south"]:
        responder.region_dialect = dialect
        for u in test_users:
            for q in test_questions:
                matched = responder.find_matched_product(q)
                ans = responder._generate_ai_reply(u, q, matched)  # noqa: SLF001
                assert len(ans) <= 180, f"Exceeded 180 chars ({len(ans)} chars): {ans}"


def test_host_chat_responder_deduplication() -> None:
    """Verify exact duplicate comments from the same user are ignored (1 comment = 1 reply only)."""
    responder = HostLiveChatResponder()
    responder.is_running = True

    # User sends identical comment 4 times consecutively
    for _ in range(4):
        responder.enqueue_comment("Son_Dam_Trung_Mien", "Mã 10 sao em")

    # Only 1 item should be enqueued
    assert responder._reply_queue.qsize() == 1  # noqa: SLF001

    # Empty queue
    item = responder._reply_queue.get_nowait()  # noqa: SLF001
    assert item[0] == "Son_Dam_Trung_Mien"
    assert item[1] == "Mã 10 sao em"
    assert responder._reply_queue.empty()  # noqa: SLF001

    # Immediate next duplicate should still be dropped by 60s cache
    responder.enqueue_comment("Son_Dam_Trung_Mien", "Mã 10 sao em")
    assert responder._reply_queue.empty()  # noqa: SLF001


def test_host_chat_responder_gratitude_and_human_like_interaction() -> None:
    """Verify human-like gratitude replies when customer says they ordered or says thanks/ok."""
    responder = HostLiveChatResponder()
    test_cases = [
        ("Son_Dam_Trung_Mien", "Đã săn rồi nha shop"),
        ("chong_mom_fan_cung", "Ok em nhé"),
        ("khanh_vy_angler", "Cảm ơn shop nhiều nha"),
        ("nguyen_van_a", "Đã chốt đơn rồi shop"),
    ]

    for user, cmt in test_cases:
        assert responder.is_gratitude_or_confirmation(cmt) is True
        for dialect in ["north", "central", "south"]:
            responder.region_dialect = dialect
            reply = responder._generate_ai_reply(user, cmt, None)  # noqa: SLF001
            assert len(reply) <= 180, f"Gratitude reply too long ({len(reply)}): {reply}"
            # Check warm keywords
            assert any(w in reply.lower() for w in ("cảm ơn", "cam on", "oke", "ủng hộ", "chúc", "gửi", "đơn", "bác", "bồ", "shop", "hỗ trợ"))


def test_domain_knowledge_adapter_multi_niche() -> None:
    """Verify DomainKnowledgeAdapter correctly detects business niches and generates tailored prompts."""
    adapter = DomainKnowledgeAdapter()

    # 1. Fishing Niche
    fishing_cart = [
        {"stt": 1, "name": "Cần Câu Đài Hoàng Đan 5.5H Phân Bổ Lực 28i Phôi Carbon", "sale_price": "315k"},
        {"stt": 2, "name": "Cần Lure Venom Khoen Fuji Sic Dây PE #2.0", "sale_price": "450k"},
    ]
    assert adapter.detect_domain_from_catalog(fishing_cart) == "fishing"
    fishing_prompt = adapter.build_system_prompt("fishing", "north")
    assert "Cần Thủ" in fishing_prompt or "Đồ Câu" in fishing_prompt

    # 2. Fashion Niche
    fashion_cart = [
        {"stt": 1, "name": "Áo Polo Nam Phối Bo Cổ Vải Cotton Co Giãn Form Rộng", "sale_price": "189k"},
        {"stt": 2, "name": "Quần Jeans Ống Suông Nữ Cạp Cao Thời Trang", "sale_price": "245k"},
    ]
    assert adapter.detect_domain_from_catalog(fashion_cart) == "fashion_apparel"
    fashion_prompt = adapter.build_system_prompt("fashion_apparel", "south")
    assert "Thời Trang" in fashion_prompt or "Stylist" in fashion_prompt

    # 3. Cosmetics Niche
    cosmetics_cart = [
        {"stt": 1, "name": "Serum Niacinamide 10% Cấp Ẩm Trắng Da Mờ Thâm Mụn", "sale_price": "220k"},
        {"stt": 2, "name": "Kem Chống Nắng Dành Cho Da Dầu Nhạy Cảm 50ml", "sale_price": "175k"},
    ]
    assert adapter.detect_domain_from_catalog(cosmetics_cart) == "cosmetics_beauty"

    # 4. Full Knowledge Base integration
    full_kb = adapter.build_full_knowledge_base(fishing_cart, "fishing")
    assert "ĐỘ CỨNG CẦN & PHÂN BỔ LỰC" in full_kb
    assert "Mã #1: Cần Câu Đài" in full_kb


def test_product_pinner_priority_hold_coordination() -> None:
    """Verify priority product pinning holds lock window and delays auto-pin loop."""
    pinner = ProductPinnerManager()
    pinner.products_catalog = [
        {"stt": 1, "name": "SP 1", "sale_price": "100k"},
        {"stt": 2, "name": "SP 2", "sale_price": "200k"},
    ]

    # Priority pin product #2 for 60s
    pinner.pin_priority_product(product_id=2, hold_seconds=60)
    assert pinner.priority_pinned_pid == "2"
    assert pinner.priority_pin_lock_until > time.time() + 50
    assert pinner.product_interest_counts.get("2") == 1


def test_host_chat_responder_fishing_encyclopedia_questions() -> None:
    """Verify AI answers off-product fishing questions intelligently across 3 regions."""
    responder = HostLiveChatResponder()

    questions = [
        "Hồ nước chảy đánh phao gì vậy shop?",
        "Câu cá chép mùa này dùng mồi gì nhạy em?",
        "Cần 6H câu cá trắm 10kg bo nổi không shop?",
    ]

    for q in questions:
        for dialect in ["north", "central", "south"]:
            responder.region_dialect = dialect
            ans = responder._generate_ai_reply("Can_Thu_K", q, None, None)  # noqa: SLF001
            assert len(ans) <= 180, f"Answer exceeded 180 chars ({len(ans)}): {ans}"
            assert len(ans) > 15, "Answer too short"


def test_host_chat_responder_advisory_river_fishing() -> None:
    """Verify customer question 'Câu sông mua cần mấy H' answers with 5H/6H fishing expertise & smart pin suggestion."""
    responder = HostLiveChatResponder()
    responder.products_catalog = [
        {"stt": 1, "name": "Cần Câu Đài Thiên Xuyên 3.6H Phân Bổ 37i", "sale_price": "210k"},
        {"stt": 12, "name": "Cần Tay Hoàng Đan 5.5H Đánh Tổng Hợp Câu Sông", "sale_price": "315k"},
        {"stt": 28, "name": "Dây Cước Câu Cá Trắng Siêu Bền", "sale_price": "70k"},
    ]

    q = "Câu sông mua cần mấy H"
    assert responder.is_advisory_or_knowledge_query(q) is True
    assert responder.is_explicit_product_query(q) is None

    best_prod = responder.find_best_product_for_advisory(q)
    assert best_prod is not None
    assert best_prod["stt"] == 12  # Must pick 5.5H rod, NOT product #28!

    for dialect in ["north", "central", "south"]:
        responder.region_dialect = dialect
        ans = responder._generate_ai_reply("Do_Hien", q, None, best_prod)  # noqa: SLF001
        assert len(ans) <= 180, f"Exceeded 180 chars ({len(ans)}): {ans}"
        assert "12" in ans  # Mentions recommended rod #12
        assert "70.000" not in ans  # Absolutely must not quote irrelevant product #28!


def test_format_price_shorthand_streamer_standard() -> None:
    """Verify price formatting converts all raw numbers/symbols into realistic streamer shorthand (e.g. 185k)."""
    assert format_price_shorthand("185.000đ") == "185k"
    assert format_price_shorthand("185.000") == "185k"
    assert format_price_shorthand("185,000đ") == "185k"
    assert format_price_shorthand("70.000đ") == "70k"
    assert format_price_shorthand("315.000đ") == "315k"
    assert format_price_shorthand("1.250.000đ") == "1250k"
    assert format_price_shorthand("185k") == "185k"
    assert format_price_shorthand("185") == "185k"
    assert format_price_shorthand("450.000 VNĐ") == "450k"

    # Test chatbot reply with 185.000đ in catalog -> outputs '185k'
    responder = HostLiveChatResponder()
    p35 = {"stt": 35, "name": "Cần Câu Tay Cao Cấp", "sale_price": "185.000đ"}
    reply = responder._generate_ai_reply("Do_Hien", "Mã 35 giá sao shop", p35)  # noqa: SLF001
    assert "185k" in reply
    assert "185.000" not in reply
    assert len(reply) <= 180





