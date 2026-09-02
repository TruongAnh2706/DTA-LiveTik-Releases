"""Unit Tests for Smart Product Matching & Flexible AI Live Consultations.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import pytest

from dta_autolive.infrastructure.host_live_chat_responder import HostLiveChatResponder


@pytest.fixture
def mock_responder():
    responder = HostLiveChatResponder()
    catalog = [
        {
            "stt": 1,
            "name": "Áo Thun Cotton 100% Form Rộng Unisex",
            "sale_price": "129.000",
            "original_price": "199.000",
            "description": "Vải cotton thoáng mát thấm hút mồ hôi, đủ size S M L XL",
        },
        {
            "stt": 2,
            "name": "Áo Phao Trần Bông Siêu Nhẹ Chống Nước Nam Nữ",
            "sale_price": "299.000",
            "original_price": "450.000",
            "description": "Áo phao dày dặn ấm áp chống gió rét mùa đông",
        },
        {
            "stt": 3,
            "name": "Son Kem Lì Mịn Môi Màu Đỏ Gạch",
            "sale_price": "89.000",
            "original_price": "150.000",
            "description": "Son lâu trôi 8 tiếng không khô môi",
        },
        {
            "stt": 4,
            "name": "Tai Nghe Bluetooth Không Dây Pin Trâu",
            "sale_price": "179.000",
            "original_price": "250.000",
            "description": "Âm bass cực căng chống ồn tốt",
        },
    ]
    responder.update_catalog(catalog)
    return responder


def test_smart_matching_ao_phao_keyword(mock_responder):
    matched = mock_responder.find_matched_product("lên mã phao đi shop")
    assert matched is not None
    assert matched["stt"] == 2
    assert "Phao" in matched["name"]

    matched2 = mock_responder.find_matched_product("cho em xem áo phao với")
    assert matched2 is not None
    assert matched2["stt"] == 2


def test_smart_matching_son_keyword(mock_responder):
    matched = mock_responder.find_matched_product("có son môi không shop")
    assert matched is not None
    assert matched["stt"] == 3
    assert "Son" in matched["name"]


def test_smart_matching_tai_nghe_keyword(mock_responder):
    matched = mock_responder.find_matched_product("cho xem tai nghe bluetooth")
    assert matched is not None
    assert matched["stt"] == 4
    assert "Tai Nghe" in matched["name"]


def test_smart_matching_explicit_stt(mock_responder):
    matched = mock_responder.find_matched_product("mã 1 bao nhiêu tiền")
    assert matched is not None
    assert matched["stt"] == 1


def test_generate_test_response_auto_pins_and_consults(mock_responder):
    pinned = []
    mock_responder.auto_pin_callback = pinned.append

    res = mock_responder.generate_test_response(
        customer_name="ThuTrang",
        question="lên mã phao đi shop ơi"
    )
    assert res["pinned_product_id"] == "2"
    assert "2" in pinned
    assert "phao" in res["reply"].lower() or "mã #2" in res["reply"]
    assert len(res["reply"]) > 30


def test_natural_request_phao_cau_and_shorthand_m7():
    responder = HostLiveChatResponder()
    fishing_catalog = [
        {
            "stt": 1,
            "name": "Cần Câu Tay Hoàng Đan 5H Carbon Cao Cấp",
            "sale_price": "350.000",
            "description": "Cần câu đài tải tĩnh 2.5kg",
        },
        {
            "stt": 3,
            "name": "Máy Câu Đứng Shimano FX Siêu Mượt",
            "sale_price": "280.000",
            "description": "Máy câu lure và câu sông",
        },
        {
            "stt": 7,
            "name": "Phao Đài Nano Đổi Màu Phát Sáng Tàng Hình",
            "sale_price": "45.000",
            "description": "Phao nano tự đổi màu khi cá cắn câu, báo tín hiệu cực nhạy",
        },
    ]
    responder.update_catalog(fishing_catalog)

    matched = responder.find_matched_product("lên phao câu đi")
    assert matched is not None
    assert matched["stt"] == 7
    assert "Phao" in matched["name"]

    matched_phao = responder.find_matched_product("cho xem phao")
    assert matched_phao is not None
    assert matched_phao["stt"] == 7

    assert responder.find_matched_product("m7")["stt"] == 7
    assert responder.find_matched_product("m 7")["stt"] == 7

    res = responder.generate_test_response(customer_name="AnhNam", question="lên phao câu đi")
    assert res["pinned_product_id"] == "7"
    assert any(w in res["reply"].lower() for w in ("phao", "mã #7", "ghim"))


def test_freeship_never_pins_other_products():
    """Kiểm tra: Khách hỏi chính sách / freeship tuyệt đối KHÔNG ĐƯỢC TỰ TIỆN GHIM SẢN PHẨM KHÁC."""
    responder = HostLiveChatResponder()
    fishing_catalog = [
        {
            "stt": 1,
            "name": "Cần Câu Tay Hoàng Đan 5H",
            "sale_price": "350.000",
        },
        {
            "stt": 7,
            "name": "Phao Đài Nano Đổi Màu",
            "sale_price": "45.000",
        },
    ]
    responder.update_catalog(fishing_catalog)

    pinned = []
    responder.auto_pin_callback = pinned.append

    res = responder.generate_test_response(customer_name="BaoAnh", question="có freeship không")

    # Tuyệt đối không ghim sản phẩm nào
    assert res["pinned_product_id"] is None
    assert res["pinned_id"] is None
    assert len(pinned) == 0

    reply_low = res["reply"].lower()
    assert "mã #1" not in reply_low  # Không được đi báo giá mã 1 lung tung
    assert "mã #7" not in reply_low


def test_clamp_message_strict_95_char_limit():
    responder = HostLiveChatResponder()

    long_reply = (
        "Dạ em ghim ngay mã #7 (Phao Đài Nano Đổi Màu Phát Sáng Tàng Hình Đêm Ngày Siêu Nhạy) "
        "lên góc trái màn hình cho bác rồi nhá! Mẫu này đang sale sốc chỉ 45k, bác bấm vào giỏ hàng chốt liền tay kẻo hết lượt nha!"
    )
    nickname = "Nguyen_Van_A_Chuyen_Gia"

    clamped = responder._clamp_message(long_reply, nickname=nickname, max_total_chars=95)  # noqa: SLF001
    total_len = len(f"@{nickname} {clamped}")

    assert total_len <= 95
    assert not clamped.endswith(" ")
    assert clamped[-1] in (".", "!", "?") or clamped[-1].isalnum()

    responder.update_catalog([
        {"stt": 7, "name": "Phao Đài Nano Đổi Màu Siêu Nhạy", "sale_price": "45.000"}
    ])
    res = responder.generate_test_response(customer_name="Trang_Live_Shop", question="lên phao câu đi")
    full_msg = f"@{res['customer']} {res['reply']}"
    assert len(full_msg) <= 95


def test_combo_gia_re_matching():
    responder = HostLiveChatResponder()
    catalog = [
        {
            "stt": 1,
            "name": "Cần Câu Tay 5H Cao Cấp 4m5",
            "sale_price": "180.000",
        },
        {
            "stt": 2,
            "name": "Combo Cần Câu Tay 5H Kèm Phao Cước Trọn Bộ",
            "sale_price": "149.000",
        },
        {
            "stt": 3,
            "name": "Combo Cần Câu Đài Săn Hàng 8H Full Set",
            "sale_price": "299.000",
        },
        {
            "stt": 5,
            "name": "(Tặng Gạt Cá + Gỡ Lưới) Rọng Cá FANGSI Khung Inox Bền Đẹp",
            "sale_price": "123.000",
        },
        {
            "stt": 6,
            "name": "Túi đựng Rọng Cá, Dụng Cụ Đồ Câu Tiện Lợi",
            "sale_price": "69.000",
        },
    ]
    responder.update_catalog(catalog)

    matched = responder.find_matched_product("Combo giá rẻ đi")
    assert matched is not None
    assert matched["stt"] == 2
    assert "Combo" in matched["name"]

    res = responder.generate_test_response(customer_name="Sam Đầm Trung Niên", question="Combo giá rẻ đi")
    assert res["pinned_product_id"] == "2"
    assert "Combo mã #2" in res["reply"] or "mã #2" in res["reply"]
    assert "Rọng Cá" not in res["reply"]
    assert "Cây mã #5" not in res["reply"]


def test_typo_resilience_phao_va_technical_advisory():
    responder = HostLiveChatResponder()
    catalog = [
        {
            "stt": 1,
            "name": "Cần Câu Tay 5H Hoàng Đan 4m5",
            "sale_price": "180.000",
        },
        {
            "stt": 2,
            "name": "Cần Câu Đài Sông Hồ 6H Bạch Kinh 5m4",
            "sale_price": "260.000",
        },
        {
            "stt": 7,
            "name": "Phao Đài Nano Đổi Màu Siêu Nhạy Báo Cá",
            "sale_price": "45.000",
        },
        {
            "stt": 8,
            "name": "Cần Săn Hàng 8H Đại Lực Carbon Toray",
            "sale_price": "490.000",
        },
    ]
    responder.update_catalog(catalog)

    matched_phao = responder.find_matched_product("Pháo bảo nhiêu")
    assert matched_phao is not None
    assert matched_phao["stt"] == 7
    assert "Phao" in matched_phao["name"]

    res_phao = responder.generate_test_response(customer_name="KhachHangA", question="Pháo bảo nhiêu")
    assert res_phao["pinned_product_id"] == "7"
    assert "45" in res_phao["reply"] or "mã #7" in res_phao["reply"]


def test_smart_matching_retail_vs_combo():
    responder = HostLiveChatResponder()
    catalog = [
        {
            "stt": 10,
            "name": "Hộp Phao Đài Đa Năng 2 Mặt Chống Nước",
            "sale_price": "75.000",
            "description": "Hộp đựng phao câu đài cao cấp",
        },
        {
            "stt": 23,
            "name": "FULL combo đầy đủ CHIẾN THẦN 8H Tặng hộp phao, trục, thẻo",
            "sale_price": "520.000",
            "description": "Combo trọn bộ cần câu và phụ kiện",
        },
    ]
    responder.update_catalog(catalog)

    matched = responder.find_matched_product("Hộp phao lẻ có không?")
    assert matched is not None
    assert matched["stt"] == 10
    assert "Hộp Phao" in matched["name"]
    assert "FULL combo" not in matched["name"]

    matched_combo = responder.find_matched_product("cho xem combo full")
    assert matched_combo is not None
    assert matched_combo["stt"] == 23
