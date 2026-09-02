"""DTA Studio - Dynamic Domain Knowledge & Niche Prompt Adapter.

Automatically analyzes TikTok Shop Live Cart / Catalog products to detect the active business niche
(e.g., Fishing Gear, Fashion/Apparel, Cosmetics/Beauty, Tech/Electronics, Food/Snacks, Home Appliances),
and provides comprehensive domain knowledge, specialized vocabulary, and tailored AI host personas.
"""

import re
from typing import Any

from dta_autolive.infrastructure.dta_qwen_engine import format_price_shorthand
from dta_autolive.infrastructure.tiktok_shop_knowledge_base import TikTokShopKnowledgeBase

# ==============================================================================
# 1. BÁCH KHOA TOÀN THƯ KIẾN THỨC NGHỀ CÂU CÁ CHUYÊN SÂU (FISHING EXPERT KB)
# ==============================================================================
FISHING_DOMAIN_ENCYCLOPEDIA: str = """
=== CẨM NANG CHUYÊN GIA NGHỀ CÂU CÁ LIVESTREAM (FISHING EXPERT GUIDE) ===
1. ĐỘ CỨNG CẦN & PHÂN BỔ LỰC (ACTION & POWER):
- Cần 3H - 4H: Đọt dẻo dịu (phân bổ lực 37i - 28i), chuyên câu cá diếc, rô phi nhỏ, cá chép hồ tự nhiên, câu cảm giác rùa, giữ cá êm, chống đứt thẻo.
- Cần 5H - 6H: Cần đài tổng hợp (phân bổ lực 28i - 19i), tải cá từ 1.5kg đến 5kg, thích hợp cho cả hồ dịch vụ và thiên nhiên, bo cá nhanh vừa phải.
- Cần 7H - 8H - 10H: Cần bạo lực săn hàng (phân bổ lực 19i - đọt đặc), chuyên bo cá khủng 5kg - 15kg (trắm đen, trắm cỏ to, cá tra, cá chim hồ dịch vụ), đánh giải, tốc độ dòng cá cực nhanh.

2. PHÔI CARBON & CÔNG NGHỆ CHẾ TẠO:
- Carbon 24T / 30T / 40T / 46T Toray Nhật Bản: Số T càng cao thì mật độ sợi carbon càng đặc, cần càng nhẹ, độ nảy và độ nén chịu tải càng khỏe.
- Đọt đặc Carbon: Chống xoắn gãy 360 độ khi giật mạnh, ngọn phụ tặng kèm giúp cần thủ an tâm đổi khi gặp sự cố.
- Khoen cần Lure: Khoen Fuji Alconite / Sic chống tưa dây dù PE, tản nhiệt nhanh khi quăng mồi xa.

3. MỒI CÂU & KỸ THUẬT CÂU TỪNG LOẠI CÁ:
- Câu Cá Chép: Mồi nền ngũ cốc (ngô non, cám tanh thơm, khoai lang ủ), hương hoa quả/khóm hoặc tinh sữa chép, câu đáy ôm mồi.
- Câu Rô Phi: Cám hạt mịn pha vị tôm/gan vịt/tanh nồng, mồi tơi xốp bung tỏa tầng lửng đến đáy.
- Câu Trắm Đen: Ốc vặn sống rửa sạch đập dập nhẹ ủ thính ốc hoặc hương ngô ngọt, câu cước trục to chịu cọ xát.
- Câu Trắm Cỏ: Lá chuối, ngô ngọt luộc, rau muống non, cám vị cỏ chua thơm.
- Câu Lure (Cá lóc, cá chẽm, cá măng): Mồi nhái hơi (frog), nhái nhảy, mồi cá sắt (vibe), mồi thìa (spoon), mồi mềm kèm lưỡi jighead.

4. THỜI TIẾT, CON NƯỚC & ĐIỂM CÂU (FISHING WEATHER & SPOTS):
- Trời nắng gắt: Cá chìm sâu đáy, tìm các ổ nước sâu, bóng râm gốc cây, cọc ngầm, chân cầu.
- Trời râm mát / Mưa phùn: Cá nổi kiếm ăn nhiều, câu nước cạn, ven bờ, cửa cống nước chảy nhẹ.
- Nước chảy xiết: Chọn phao chì neo hoặc phao đài bầu ngắn chịu sóng, câu mồi dẻo bám đáy.
- Nước đứng / Nước trong: Dùng dây thẻo mảnh tàng hình (cước Fluorocarbon), phao hạt nano tàng hình tránh cá nhát.

5. PHỤ KIỆN & BẢO QUẢN:
- Dây câu: Dây cước Mono/Nylon tàng hình câu đài, dây dù PE 4x/8x số #1.0-#4.0 câu lure chịu lực kéo cao.
- Đóng gói vận chuyển: Đóng ống nhựa PVC cứng cáp bọc xốp bóng khí 2 đầu, bao không gãy vỡ, kiểm tra hàng thoải mái trước khi thanh toán.
- Chính sách bảo hành: Bảo hành chính hãng 1 năm 1 lóng miễn phí, lỗi 1 đổi 1 trong 7 ngày đầu.
"""

# ==============================================================================
# 2. CÁC NGÀNH HÀNG KHÁC (FASHION, COSMETICS, TECH, FOOD, GENERAL RETAIL)
# ==============================================================================
DOMAIN_KNOWLEDGE_PRESETS: dict[str, dict[str, Any]] = {
    "fishing": {
        "name": "Đồ Câu Cá & Dã Ngoại (Fishing & Outdoor)",
        "keywords": [
            "cần câu", "can cau", "máy câu", "may cau", "lure", "câu đài", "cau dai", "phôi", "carbon",
            "5h", "6h", "4h", "8h", "3h", "19i", "28i", "37i", "gác cần", "phao câu", "mồi câu", "moi cau",
            "dây pe", "cước", "cuoc", "khoen fuji", "nhái hơi", "đọt", "lóng", "tải cá", "chống móm", "cần tay"
        ],
        "encyclopedia": FISHING_DOMAIN_ENCYCLOPEDIA,
        "persona_prompt": (
            "Bạn là Host Livestream Bán Đồ Câu Cá và là một cần thủ chuyên nghiệp, am hiểu sâu sắc về mọi loại cần (câu đài, lure, lục), "
            "phôi carbon 24T-40T, độ cứng 3H-10H, cách pha mồi cá chép/trắm/rô phi, kỹ thuật chọn dây cước/dù PE và mẹo câu cá theo thời tiết. "
            "Luôn tư vấn tận tình, chuẩn kỹ thuật, nói chuyện thân thiện như bạn đồng câu."
        ),
    },
    "fashion_apparel": {
        "name": "Thời Trang & Quần Áo (Fashion & Apparel)",
        "keywords": [
            "áo", "ao", "quần", "quan", "váy", "vay", "đầm", "dam", "set", "sơ mi", "so mi", "polo",
            "thun", "cotton", "oversize", "form rộng", "size", "freesize", "vải", "co giãn", "jeans",
            "khoác", "hoodie", "cardigan", "chân váy", "yếm"
        ],
        "encyclopedia": """
=== CẨM NANG TƯ VẤN THỜI TRANG LIVESTREAM ===
1. Chất liệu: Cotton 100% 2 chiều/4 chiều thấm hút mồ hôi, vải đũi mát mịn không nhăn, vải lụa tuyết mềm rủ, denim bền màu.
2. Bảng size chuẩn: Size S (40-47kg), Size M (48-55kg), Size L (56-62kg), Size XL (63-70kg), Form oversize từ 45-75kg mặc vừa.
3. Phối đồ (Mix & Match): Phối áo thun + quần ống rộng cá tính, áo polo + quần âu lịch sự, set váy tiểu thư nhẹ nhàng.
4. Đổi trả: Hỗ trợ đổi size trong vòng 7 ngày nguyên tem mác.
""",
        "persona_prompt": (
            "Bạn là Stylist & Host Livestream Thời Trang năng động, sành điệu. Bạn am hiểu sâu sắc về chất liệu vải, bảng size cân nặng/chiều cao, "
            "và cách phối đồ tôn dáng. Luôn tư vấn chuẩn size, nhiệt tình gợi ý phong cách cho khách hàng."
        ),
    },
    "cosmetics_beauty": {
        "name": "Mỹ Phẩm & Chăm Sóc Sắc Đẹp (Cosmetics & Skincare)",
        "keywords": [
            "kem", "son", "serum", "toner", "nước hoa hồng", "chống nắng", "sữa rửa mặt", "tẩy trang",
            "dưỡng ẩm", "trắng da", "mụn", "nám", "tàn nhang", "da dầu", "da khô", "da nhạy cảm", "cushion",
            "phấn", "mascara", "bảng mắt", "retinol", "bha", "aha", "niacinamide"
        ],
        "encyclopedia": """
=== CẨM NANG TƯ VẤN MỸ PHẨM & SKINCARE LIVESTREAM ===
1. Phân loại da: Da dầu mụn (dùng gel kiềm dầu, BHA, Niacinamide), Da khô (cấp ẩm Hyaluronic Acid, Ceramide), Da nhạy cảm (chiết xuất rau má, cúc la mã, không cồn).
2. Chu trình Skincare: Tẩy trang -> Sữa rửa mặt -> Toner cân bằng -> Serum đặc trị -> Kem dưỡng khóa ẩm -> Kem chống nắng ban ngày.
3. Cam kết: 100% chính hãng có tem phụ tiếng Việt, đầy đủ hóa đơn, hạn sử dụng mới nhất.
""",
        "persona_prompt": (
            "Bạn là Chuyên viên Skincare & Host Livestream Mỹ Phẩm tận tâm, am hiểu cặn kẽ về các loại da (da dầu, khô, nhạy cảm), "
            "hoạt chất dưỡng da (AHA/BHA, Niacinamide, Retinol) và cách makeup tự nhiên. Tư vấn an toàn, chu đáo, chuẩn khoa học."
        ),
    },
    "electronics_tech": {
        "name": "Công Nghệ & Điện Tử (Electronics & Smart Devices)",
        "keywords": [
            "tai nghe", "bluetooth", "sạc", "cáp", "pin", "dự phòng", "loa", "loa bluetooth", "smartwatch",
            "đồng hồ thông minh", "ốp lưng", "cường lực", "chuột", "bàn phím", "type-c", "máy cạo râu",
            "quạt tích điện", "camera", "mic thu âm", "tripod"
        ],
        "encyclopedia": """
=== CẨM NANG TƯ VẤN THIẾT BỊ CÔNG NGHỆ LIVESTREAM ===
1. Thông số kỹ thuật: Chip Bluetooth 5.3 kết nối siêu nhanh không độ trễ, pin lithium trâu dùng 6-12 tiếng liên tục, sạc nhanh PD 20W-65W.
2. Tương thích: Hỗ trợ 100% hệ điều hành iOS (iPhone/iPad), Android (Samsung, Xiaomi, Oppo), PC/Laptop Windows & MacOS.
3. Bảo hành: Bảo hành lỗi 1 đổi 1 trong 12 tháng, đổi mới tận nhà nếu lỗi từ nhà sản xuất.
""",
        "persona_prompt": (
            "Bạn là Chuyên gia Review Công Nghệ & Host Livestream Điện Tử am hiểu thông số kỹ thuật, dung lượng pin, chuẩn sạc nhanh PD, "
            "chip âm thanh, độ trễ gaming và tính tương thích trên mọi dòng điện thoại/máy tính. Tư vấn rành mạch, bảo hành uy tín."
        ),
    },
    "food_beverage": {
        "name": "Thực Phẩm & Đồ Ăn Vặt (Food & Snacks)",
        "keywords": [
            "ăn vặt", "khô bò", "khô gà", "cơm cháy", "bánh", "kẹo", "trà", "cà phê", "mì", "miến",
            "gia vị", "hạt điều", "hạt dẻ", "mắc ca", "ô mai", "chân vịt", "chân gà", "rong biển"
        ],
        "encyclopedia": """
=== CẨM NANG TƯ VẤN ĐỒ ĂN VẶT & THỰC PHẨM LIVESTREAM ===
1. Vệ sinh ATTP: Đầy đủ chứng nhận VSATTP, sản xuất quy trình khép kín, hút chân không sạch sẽ.
2. Hạn sử dụng: Hàng mới ra lò date mới tinh (6-12 tháng), không chất bảo quản độc hại.
3. Hương vị: Cay tê chuẩn vị, thơm giòn đậm đà, đóng gói lon pet hoặc túi zip tiện lợi ăn liền.
""",
        "persona_prompt": (
            "Bạn là Host Livestream Ẩm Thực hài hước, duyên dáng, miêu tả hương vị giòn ngon, đậm đà, kích thích vị giác của khách hàng. "
            "Luôn nhấn mạnh hạn sử dụng mới tinh, chứng nhận vệ sinh an toàn thực phẩm và ưu đãi combo ăn thả ga."
        ),
    },
    "general_retail": {
        "name": "Bán Lẻ Tổng Hợp & Đồ Gia Dụng (Home & General Goods)",
        "keywords": [
            "gia dụng", "tiện ích", "nhà bếp", "lau nhà", "hộp đựng", "kệ", "móc treo", "bình giữ nhiệt",
            "dao", "thớt", "đèn", "gối", "chăn", "khăn", "dụng cụ", "mini", "thông minh"
        ],
        "encyclopedia": """
=== CẨM NANG TƯ VẤN ĐỒ GIA DỤNG TIỆN ÍCH LIVESTREAM ===
1. Công năng: Thiết kế thông minh tối ưu không gian sống, chất liệu nhựa ABS cao cấp / Inox 304 không gỉ.
2. Tính tiện lợi: Dễ dàng tháo lắp, lau rửa vệ sinh, độ bền cao qua nhiều năm sử dụng.
3. Đóng gói: Bọc xốp chống sốc, giao hàng tận nơi kiểm tra hàng trước khi nhận.
""",
        "persona_prompt": (
            "Bạn là Host Livestream Gia Dụng Thông Minh khéo léo, chỉ rõ các tiện ích giải phóng sức lao động trong gia đình. "
            "Tư vấn chất liệu bền bỉ Inox 304, nhựa ABS an toàn và cam kết đổi trả uy tín."
        ),
    },
}


class DomainKnowledgeAdapter:
    """Auto-detects business domain from Live cart products and dynamically generates customized AI persona & knowledge."""

    def __init__(self, default_domain: str = "fishing") -> None:
        self.current_domain: str = default_domain

    def detect_domain_from_catalog(self, products: list[dict[str, Any]]) -> str:
        """Analyze product names in cart to detect the dominant business domain."""
        if not products:
            return self.current_domain

        # Combine all product titles and text
        all_text_tokens = " ".join([
            str(p.get("name", "")).lower() + " " + str(p.get("campaign", "")).lower()
            for p in products
        ])

        domain_scores: dict[str, int] = {}
        for dom_key, dom_data in DOMAIN_KNOWLEDGE_PRESETS.items():
            score = 0
            for kw in dom_data["keywords"]:
                matches = re.findall(rf"\b{re.escape(kw)}\b", all_text_tokens)
                score += len(matches)
            domain_scores[dom_key] = score

        # Find domain with highest score
        best_domain = max(domain_scores, key=domain_scores.get)  # type: ignore[arg-type]
        if domain_scores[best_domain] > 0:
            self.current_domain = best_domain
        else:
            self.current_domain = "general_retail"

        return self.current_domain

    def get_domain_info(self, domain_key: str | None = None) -> dict[str, Any]:
        """Get full details of specified or current active domain."""
        key = domain_key or self.current_domain
        return DOMAIN_KNOWLEDGE_PRESETS.get(key, DOMAIN_KNOWLEDGE_PRESETS["general_retail"])

    def build_system_prompt(
        self,
        domain_key: str | None = None,
        region_dialect: str = "south",
        tone_style: str = "genz_casual",
    ) -> str:
        """Construct full system prompt tailored to detected domain, regional dialect, and tone."""
        dom_info = self.get_domain_info(domain_key)
        persona_base = dom_info["persona_prompt"]

        dialect_note = ""
        if region_dialect == "north":
            dialect_note = "Xưng hô 'bác/em', dùng từ ngữ miền Bắc thân thiện ('nhá', 'nhé', 'bác chốt lẹ', 'cành')."
        elif region_dialect == "central":
            dialect_note = "Xưng hô 'mình/bồ/em', dùng từ ngữ miền Trung chân chất ('hỉ', 'hè', 'nè', 'mềm xèo')."
        else:
            dialect_note = "Xưng hô 'anh em/mấy ní/bồ/em', dùng từ ngữ miền Nam hào sảng ('nha', 'lụm liền', 'ngon lành cành đào')."

        tiktok_kb_summary = TikTokShopKnowledgeBase.get_knowledge_summary_for_ai_prompt()
        return (
            f"{persona_base}\n\n"
            f"{tiktok_kb_summary}\n"
            f"- Giọng điệu vùng miền: {dialect_note}\n"
            f"- Phong cách chat: Ngắn gọn, tự nhiên, dưới 90 ký tự, hỗ trợ khách mua hàng và trả lời chuyên sâu câu hỏi ngoài lề."
        )

    def build_full_knowledge_base(
        self,
        products: list[dict[str, Any]],
        domain_key: str | None = None,
    ) -> str:
        """Combine live cart catalog with domain encyclopedia and TikTok Shop policies for 360-degree consultation."""
        dom_info = self.get_domain_info(domain_key)
        encyclopedia = dom_info["encyclopedia"]
        tiktok_rules = TikTokShopKnowledgeBase.get_knowledge_summary_for_ai_prompt()

        cart_lines = ["=== DANH MỤC SẢN PHẨM ĐANG BÁN TRÊN LIVE (GIỎ HÀNG) ==="]
        if not products:
            cart_lines.append("(Chưa có sản phẩm nào trong giỏ hàng)")
        else:
            for p in products:
                stt = p.get("stt", "?")
                name = p.get("name", "Sản phẩm")
                sale_price = format_price_shorthand(p.get("sale_price", ""))
                orig_price = f" (Giá gốc: {format_price_shorthand(p.get('original_price'))})" if p.get("original_price") else ""
                stock = f" - Còn: {p.get('stock')}" if p.get("stock") else ""
                cart_lines.append(f"• Mã #{stt}: {name} - Giá: {sale_price}{orig_price}{stock}")

        cart_text = "\n".join(cart_lines)
        return f"{cart_text}\n\n{tiktok_rules}\n\n{encyclopedia}"
