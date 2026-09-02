"""Unit tests for TikTokShopKnowledgeBase & Policy Handler.

Verifies accurate default platform policies and non-accidental pinning.
"""

from dta_autolive.infrastructure.host_live_chat_responder import HostLiveChatResponder
from dta_autolive.infrastructure.tiktok_shop_knowledge_base import TikTokShopKnowledgeBase


def test_detect_policy_intent():
    kb = TikTokShopKnowledgeBase()
    assert kb.detect_policy_intent("Có giống trên live không shop?") == "COLOR_REAL_ITEM"
    assert kb.detect_policy_intent("Mấy ngày nhận được hàng shop ơi?") == "SHIPPING"
    assert kb.detect_policy_intent("Có được xem hàng không?") == "CO_INSPECTION"
    assert kb.detect_policy_intent("Đổi trả thế nào shop?") == "RETURN_WARRANTY"
    assert kb.detect_policy_intent("Có mã freeship không?") == "VOUCHER_FREESHIP"
    assert kb.detect_policy_intent("Cần câu 5H giá bao nhiêu?") is None


def test_policy_responses():
    kb = TikTokShopKnowledgeBase()

    # 1. Độ chính xác live
    rep_live = kb.generate_policy_response("COLOR_REAL_ITEM", "KhachA", "north")
    assert "100%" in rep_live or "thật" in rep_live or "live" in rep_live

    # 2. Vận chuyển
    rep_ship = kb.generate_policy_response("SHIPPING", "KhachB", "south")
    assert "2-3" in rep_ship
    assert any(c in rep_ship for c in ["J&T", "GHN", "SPX"])

    # 3. Đồng kiểm
    rep_co = kb.generate_policy_response("CO_INSPECTION", "KhachC", "central")
    assert "đồng kiểm" in rep_co.lower() or "kiểm tra" in rep_co.lower()

    # 4. Đổi trả
    rep_ret = kb.generate_policy_response("RETURN_WARRANTY", "KhachD", "north")
    assert "6 ngày" in rep_ret

    # 5. Freeship & Voucher
    rep_vouch = kb.generate_policy_response("VOUCHER_FREESHIP", "KhachE", "south")
    assert "freeship" in rep_vouch.lower() or "voucher" in rep_vouch.lower()


def test_host_responder_no_accidental_pin_on_combo_color_question():
    """Đảm bảo khi khách hỏi chính sách / màu sắc thì KHÔNG BAO GIỜ bị ghim nhầm sản phẩm."""
    pinned_calls = []

    def mock_auto_pin(pid):
        pinned_calls.append(str(pid))

    responder = HostLiveChatResponder(auto_pin_callback=mock_auto_pin)
    sample_catalog = [
        {"stt": "1", "name": "Combo 2 Cần Câu Đài Hoàng Đan 5H", "sale_price": "299000"},
        {"stt": "2", "name": "Phao Nano Tàng Hình", "sale_price": "50000"}
    ]
    responder.update_catalog(sample_catalog)

    res = responder.generate_test_response(
        customer_name="Trần_Văn_A",
        question="Combo có đúng màu như trên live ko shop?",
        region_dialect="north"
    )

    assert res["pinned_id"] is None
    assert len(pinned_calls) == 0
