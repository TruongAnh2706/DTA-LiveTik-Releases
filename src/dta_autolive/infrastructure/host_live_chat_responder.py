"""DTA Studio - Host Live Chat Responder Engine.

Listens to real-time viewer comments & seeding interactions, generates high-accuracy
sales responses using Qwen Local AI with Live Cart Knowledge Base, and types the reply
directly into the TikTok Shop Streamer Dashboard chatbox via CDP.
"""

import queue
import random
import threading
import time
from collections.abc import Callable
from typing import Any

import structlog

from dta_autolive.infrastructure.domain_knowledge_adapter import DomainKnowledgeAdapter
from dta_autolive.infrastructure.dta_qwen_engine import format_price_shorthand
from dta_autolive.infrastructure.tiktok_shop_knowledge_base import TikTokShopKnowledgeBase

logger = structlog.get_logger()


DEFAULT_DYNAMIC_HOST_PROMPT = """Bạn là một nhân viên tư vấn bán hàng online cực kỳ nhiệt tình, khéo léo và tự nhiên (xưng "em" hoặc xưng tên Shop - gọi khách là "bác/anh/chị" tùy ngữ cảnh).
---
THÔNG TIN NỀN TẢNG CỬA HÀNG:
{{Thong tin nen tang}}
DANH SÁCH SẢN PHẨM HIỆN CÓ:
{{List san pham}}
QUY TẮC:
{{Quy tac}}

NGUYÊN TẮC XỬ LÝ BÌNH LUẬN:

1. ĐOÁN Ý VÀ GIẢI MÃ CHÍNH TẢ (Quan trọng):
- Khách có thể gõ sai chính tả, không dấu, viết tắt, teencode hoặc dùng tiếng lóng (ví dụ: "cần câu đon", "may cau", "ib gia", "ship hn bnh", "gia s bnhieu"). Hãy chủ động suy luận theo ngữ cảnh và đối chiếu với danh sách sản phẩm để trả lời đúng món khách đang quan tâm.
- Nếu bình luận quá mơ hồ hoặc có thể hiểu theo nhiều món khác nhau, hãy lịch sự hỏi lại để làm rõ kèm một gợi ý nhẹ (Ví dụ: "Dạ có phải bác đang hỏi mẫu cần X hay mẫu Y không ạ?").

2. XỬ LÝ THEO TỪNG TÌNH HUỐNG:
- Khách hỏi sản phẩm CÓ trong danh sách: Tư vấn đúng trọng tâm, nêu bật ưu điểm phù hợp với nhu cầu, báo giá rõ ràng và khéo léo mời khách chốt đơn/nhắn tin riêng để tạo đơn nhanh.
- Khách hỏi sản phẩm KHÔNG CÓ hoặc ĐÃ HẾT: Tuyệt đối không từ chối cộc lốc. Hãy phản hồi khéo léo (Ví dụ: "Dạ mẫu này shop em tạm hết/chưa về thêm...") và lập tức gợi ý một sản phẩm khác đang có sẵn mang tính năng tương đương kèm lý do nên chọn.
- Khách chốt đơn (để lại sđt, địa chỉ, "lấy 1 cái", "chốt"): Phản hồi vui vẻ, xác nhận và hướng dẫn khách check tin nhắn riêng để bảo mật thông tin cá nhân.
- Khách comment giao lưu / khen / trêu đùa / tương tác vui: Trò chuyện tự nhiên, duyên dáng như người thật, không gượng ép "chèo kéo" bán hàng trong mọi câu nói.

3. PHONG CÁCH DIỄN ĐẠT:
- Giọng văn đời thực, ngắn gọn (1–3 câu), ngắt ý rõ ràng, dùng thêm 1–2 emoji phù hợp để tạo cảm giác thân thiện.
- Không nói vòng vo máy móc, không lặp lại nguyên văn câu hỏi của khách.
- Chỉ đưa ra thông tin có thật trong dữ liệu được cung cấp, không tự bịa đặt giá cả hay chính sách ngoài danh sách."""

DEFAULT_PLATFORM_INFO = """- Giao hàng: Giao hàng toàn quốc từ 2-4 ngày. Được kiểm tra hàng (đồng kiểm) trước khi thanh toán.
- Đổi trả & Bảo hành: Lỗi 1 đổi 1 trong vòng 7 ngày đầu tiên nếu có lỗi từ nhà sản xuất. Hỗ trợ bảo hành chính hãng.
- Miễn phí vận chuyển: Freeship toàn quốc cho đơn hàng từ 200.000đ hoặc khi áp mã voucher trên live.
- Quà tặng: Tặng kèm phụ kiện chính hãng theo từng phân loại sản phẩm."""

DEFAULT_RULES = """- Luôn trả lời tôn trọng, lịch sự và thân thiện với khách hàng.
- Tuyệt đối không nhắc đến các nền tảng cấm hoặc từ khóa vi phạm chính sách livestream TikTok (không nhắc Shopee, Lazada, số điện thoại ngoài...).
- Không nói tục, không cộc lốc, không tranh cãi với khách hàng.
- Luôn khuyến khích khách bấm vào góc trái màn hình để xem giỏ hàng và chốt đơn."""


class HostLiveChatResponder:
    """Automates Host Chat Replies directly inside TikTok Shop Streamer Live Dashboard."""

    def __init__(
        self,
        qwen_engine: Any = None,
        deepseek_engine: Any = None,
        ai_provider: str = "auto",
        cdp_port: int = 9222,
        log_callback: Callable[[str, str], None] | None = None,
        status_callback: Callable[[str, str], None] | None = None,
        auto_pin_callback: Callable[[str | int], Any] | None = None,
        event_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.qwen_engine = qwen_engine
        self.deepseek_engine = deepseek_engine
        self.ai_provider = ai_provider
        self.cdp_port = cdp_port
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.auto_pin_callback = auto_pin_callback
        self.event_callback = event_callback

        self.is_running: bool = False
        self.system_prompt: str = ""
        self.prompt_template: str = DEFAULT_DYNAMIC_HOST_PROMPT
        self.platform_info: str = DEFAULT_PLATFORM_INFO
        self.rules: str = DEFAULT_RULES

        self.knowledge_catalog_text: str = ""
        self.products_catalog: list[dict[str, Any]] = []
        self.username: str = ""

        # Bộ thích ứng ngành hàng và bách khoa kiến thức chuyên sâu
        self.domain_adapter = DomainKnowledgeAdapter()
        self.tiktok_kb = TikTokShopKnowledgeBase()

        self._reply_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._listener_thread: threading.Thread | None = None
        self._tiktok_client: Any = None
        self.region_dialect: str = "south"
        self.tone_style: str = "genz_casual"
        self.use_slangs: bool = True
        self._reply_count: int = 0

        # Bộ đệm chống phản hồi trùng lặp & Hệ thống Theo Dõi Khách Hàng (Customer Lifecycle Tracker)
        self._processed_comments: dict[str, float] = {}
        self._user_last_reply: dict[str, float] = {}
        self._active_queue_users: set[str] = set()

        # Tập dấu vân tay đã trả lời thành công trong toàn bộ phiên Live (Khóa cứng vĩnh viễn không rep lại)
        self._replied_comment_fingerprints: set[str] = set()
        self._in_progress_comments: set[str] = set()
        self._customer_registry: dict[str, dict[str, Any]] = {}

    def set_prompt_configuration(
        self,
        prompt_template: str = "",
        platform_info: str = "",
        rules: str = "",
    ) -> None:
        """Cập nhật kịch bản prompt động và các biến nền tảng / quy tắc do người dùng cấu hình."""
        if prompt_template:
            self.prompt_template = prompt_template
        if platform_info:
            self.platform_info = platform_info
        if rules:
            self.rules = rules

        # Xây dựng lại System Prompt hoàn chỉnh
        self.system_prompt = self.build_system_prompt_from_template()
        self.log("INFO", "💾 [PROMPT DYNAMIC] Đã đồng bộ Kịch bản Prompt Host & các biến dữ liệu nền tảng.")

    def format_products_catalog_for_prompt(self, products: list[dict[str, Any]] | None = None) -> str:
        """Format danh sách sản phẩm cào về thành chuỗi dữ liệu rõ ràng, chuẩn xác cho AI đọc."""
        prods = products if products is not None else self.products_catalog
        if not prods:
            return "(Hiện tại chưa có sản phẩm nào được cào về từ Giỏ Hàng TikTok Shop)"

        lines = []
        for p in prods:
            stt = p.get("stt", "?")
            name = p.get("name", "Sản phẩm")
            sale_price = p.get("sale_price") or p.get("price") or "Liên hệ Shop"
            orig_price = p.get("original_price", "")
            stock = p.get("stock", "Còn hàng")
            campaign = p.get("campaign", "")
            features = p.get("features") or p.get("description") or "Chính hãng cao cấp"
            variants = p.get("variants") or p.get("classification") or ""

            item_str = f"- SP #{stt}: {name}"
            if variants:
                item_str += f" | Phân loại: {variants}"
            item_str += f" | Giá bán: {sale_price}"
            if orig_price and orig_price != sale_price:
                item_str += f" (Gốc: {orig_price})"
            if campaign:
                item_str += f" | Ưu đãi: {campaign}"
            item_str += f" | Đặc điểm/Công dụng: {features}"
            item_str += f" | Tình trạng kho: {stock}"
            lines.append(item_str)

        return "\n".join(lines)

    def build_system_prompt_from_template(
        self,
        template: str = "",
        platform_info: str = "",
        products: list[dict[str, Any]] | None = None,
        rules: str = "",
    ) -> str:
        """Thay thế 3 biến {{Thong tin nen tang}}, {{List san pham}}, {{Quy tac}} vào Prompt Template."""
        import re

        tmpl = template or self.prompt_template or DEFAULT_DYNAMIC_HOST_PROMPT
        p_info = platform_info or self.platform_info or DEFAULT_PLATFORM_INFO
        p_rules = rules or self.rules or DEFAULT_RULES
        p_catalog_text = self.format_products_catalog_for_prompt(products)

        # Regex thay thế bất kể hoa thường, có/không dấu
        # 1. {{Thong tin nen tang}}
        tmpl = re.sub(r"\{\{\s*(?:thong\s*tin\s*nen\s*tang|thông\s*tin\s*nền\s*tảng|thong_tin_nen_tang)\s*\}\}", p_info, tmpl, flags=re.IGNORECASE)
        # 2. {{List san pham}}
        tmpl = re.sub(r"\{\{\s*(?:list\s*san\s*pham|danh\s*sách\s*sản\s*phẩm|list_san_pham|danh_sach_san_pham)\s*\}\}", p_catalog_text, tmpl, flags=re.IGNORECASE)
        # 3. {{Quy tac}}
        tmpl = re.sub(r"\{\{\s*(?:quy\s*tac|quy\s*tắc|quy_tac)\s*\}\}", p_rules, tmpl, flags=re.IGNORECASE)

        return tmpl.strip()

    def update_catalog(self, products: list[dict[str, Any]]) -> str:
        """Cập nhật giỏ hàng và điền lại biến {{List san pham}} vào Kịch bản Prompt của người dùng."""
        self.products_catalog = products
        self.system_prompt = self.build_system_prompt_from_template()
        self.log("INFO", f"📦 [GIỎ HÀNG] Đã nạp {len(products)} sản phẩm vào biến {{List san pham}} của Kịch bản.")
        return "custom_user_prompt"

    def is_gratitude_or_confirmation(self, text: str) -> bool:
        """Kiểm tra comment có phải là lời cảm ơn, đã săn/chốt đơn, khen hoặc xác nhận ok."""
        t_low = text.lower().strip()
        keywords = [
            "đã săn", "da san", "săn rồi", "san roi", "vừa săn", "vua san", "săn đc", "san dc", "săn được",
            "đã chốt", "da chot", "chốt rồi", "chot roi", "vừa chốt", "vua chot", "chốt đơn", "chot don",
            "đã mua", "da mua", "mua rồi", "mua roi", "vừa mua", "vua mua",
            "đã đặt", "da dat", "đặt rồi", "dat roi", "vừa đặt", "vua dat",
            "đã ủng hộ", "da ung ho", "ủng hộ shop", "ung ho shop", "ung ho", "ủng hộ",
            "ok shop", "oke shop", "ok e", "ok em", "ok nè", "oke nè", "oki shop", "okee", "ok nhe", "oke nhe", "oki",
            "cảm ơn shop", "cam on shop", "thank shop", "thanks shop", "tks shop", "tk shop",
            "cảm ơn em", "cam on em", "cảm ơn bác", "cam on bac", "cảm ơn bạn", "cam on ban", "cảm ơn nha", "cảm ơn", "cam on",
            "đẹp quá", "hang dep", "hàng đẹp", "uy tín", "tuyệt vời", "ưng ý", "ưng bụng", "chất lượng"
        ]
        return any(kw in t_low for kw in keywords)

    def strip_accents(self, text: str) -> str:
        """Loại bỏ dấu tiếng Việt để đối sánh từ khóa linh hoạt."""
        import unicodedata
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.replace('đ', 'd').replace('Đ', 'D').lower().strip()

    def is_explicit_product_query(self, text: str) -> int | None:
        """Kiểm tra xem comment có hỏi đích danh mã số STT sản phẩm (VD: 'mã 1', 'm7', 'ms 2', '#3', 'cây 5', 'mẫu 4')."""
        import re
        t_low = text.lower().strip()

        patterns = [
            r"(?:mã\s*số|ma\s*so|mẫu\s*số|mau\s*so|sản\s*phẩm\s*số|san\s*pham\s*so|sản\s*phẩm|san\s*pham|mã|ma|mẫu|mau|ms|sp|cây\s*số|cay\s*so|cần\s*số|can\s*so|cây|cay|cần|can|áo\s*số|ao\s*so|váy\s*số|vay\s*so|set\s*số|set\s*so|son\s*số|son\s*so|món\s*số|mon\s*so|số|so)\s*#?\s*(\d{1,3})\b",
            r"#\s*(\d{1,3})\b",
            r"\bm\s*#?\s*(\d{1,3})\b",
            r"(?:lên|len|ghim|xem|cho|bật|chốt|hỏi|mua)\s*#?\s*(\d{1,3})\b",
            r"\b(\d{1,3})\s*(?:giá|gia|nhiêu|nhieu|sao|k|đ|d|bao|còn|con|bán|ban|có|co|đợt|dot|hỏi|hoi|mua|xem|giao|ship|bảo\s*hành|bao\s*hanh|chốt|chot|size|màu|mau)\b",
            r"^(?:cho\s*(?:hỏi|hoi|xem)\s*)?(\d{1,3})$",
        ]
        for pat in patterns:
            m = re.search(pat, t_low)
            if m:
                try:
                    stt = int(m.group(1))
                    if 1 <= stt <= 300:
                        return stt
                except Exception:
                    pass

        # Quét thông minh: Nếu câu comment chứa bất kỳ con số nào trùng khớp với STT trong giỏ hàng cào về
        if self.products_catalog:
            digits = re.findall(r"\b\d{1,3}\b", t_low)
            for d in digits:
                try:
                    cand = int(d)
                    if any(int(p.get("stt", 0)) == cand for p in self.products_catalog):
                        return cand
                except Exception:
                    pass

        return None

    def find_matched_product_by_keywords(self, text: str) -> dict[str, Any] | None:
        """Tìm kiếm sản phẩm thông minh theo ý định thực chiến: Combo, Ngành hàng, Giá rẻ/Cao cấp, và Từ khóa."""
        if not self.products_catalog:
            return None

        import re
        t_low = text.lower().strip()
        t_no_acc = self.strip_accents(t_low)

        # 1. Phân tích Ý định về Loại hình & Đặc tính sản phẩm (Hỗ trợ 100% không dấu & lỗi gõ dấu telex)
        is_combo_req = any(w in t_no_acc for w in ("combo", "com bo", "compo", "tron bo", "ca bo", "nguyen bo", "set bo", "set"))
        is_single_req = any(w in t_no_acc for w in (
            "le", "ban le", "mua le", "le ko", "le khong", "le k", "rieng", "rieng ko",
            "moi", "chi mua", "tung mon", "tung cay", "tung hop", "tung cai", "cai le",
            "hop le", "phao le", "can le", "ao le", "quan le", "moi hop", "moi cay"
        ))
        is_cheap_req = any(w in t_no_acc for w in ("gia re", "re nhat", "re", "hat de", "binh dan", "sinh vien", "mem", "hoi", "re di", "re nhat"))
        is_expensive_req = any(w in t_no_acc for w in ("cao cap", "xin", "dat nhat", "chat luong nhat", "tot nhat"))

        # Phân loại danh mục chuyên sâu (Bao quát toàn bộ biến thể sai chính tả, nhầm dấu: pháo->phao, cấn->cần, mái->máy, rộng/dọng->rọng)
        is_box_float_req = any(w in t_no_acc for w in ("hop phao", "hop dung phao", "hop phu kien", "hop"))
        is_rod_req = any(w in t_no_acc for w in ("can", "can cau", "can tay", "can dai", "can lure", "cay can", "5h", "6h", "4h", "8h", "10h")) and not is_box_float_req
        is_float_req = any(w in t_no_acc for w in ("phao", "phao dai", "phao nano", "phao co", "phao kim", "phao dem", "phao cau")) and not is_box_float_req
        is_net_req = any(w in t_no_acc for w in ("rong", "dong", "rong ca", "dong ca", "vot", "gat ca"))
        is_reel_req = any(w in t_no_acc for w in ("may cau", "mai cau", "may dung", "may ngang", "coi may", "may"))
        is_line_req = any(w in t_no_acc for w in ("day cau", "cuoc", "du pe", "day pe", "theo", "truc"))
        is_bait_req = any(w in t_no_acc for w in ("moi", "moi cau", "cam", "tinh mui", "hat xa"))
        is_chair_box_req = any(w in t_no_acc for w in ("ghe", "thung", "tui dung", "o du", "tui"))
        is_fashion_req = any(w in t_no_acc for w in ("ao", "quan", "vay", "dam", "khoac", "hoodie", "polo", "thun"))
        is_cosmetics_req = any(w in t_no_acc for w in ("son", "kem", "phan", "serum", "sua rua mat", "duong da"))
        is_tech_req = any(w in t_no_acc for w in ("tai nghe", "tai nge", "loa", "sac", "cap", "pin", "bluetooth"))

        # Trích xuất từ khóa loại bỏ trợ từ
        raw_stop_words = {
            "cho", "em", "anh", "chi", "minh", "xem", "len", "di", "shop", "shop ơi",
            "voi", "ne", "co", "khong", "ko", "k", "nhe", "nha", "nhi",
            "a", "oi", "bac", "ad", "admin", "hoi", "muon",
            "tu", "van", "san", "pham", "cai", "con", "hang",
            "bao", "nhieu", "nhieu tien", "sao", "giup", "ghim"
        }
        words = re.findall(r"\w+", t_no_acc)
        keywords_no_acc = [w for w in words if w not in raw_stop_words and len(w) >= 2]

        # 2. Tìm giá min/max của catalog để tính điểm giá rẻ / cao cấp
        prices = []
        for p in self.products_catalog:
            p_val = int(re.sub(r"\D", "", str(p.get("sale_price") or p.get("price") or "0")) or "0")
            if p_val > 0:
                prices.append(p_val)
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        scored_products = []

        for p in self.products_catalog:
            p_name = p.get("name", "").lower()
            p_name_no_acc = self.strip_accents(p_name)
            p_desc = str(p.get("description", "")).lower()
            p_desc_no_acc = self.strip_accents(p_desc)
            p_price = int(re.sub(r"\D", "", str(p.get("sale_price") or p.get("price") or "0")) or "0")

            score = 0

            # A. Ưu tiên theo Ý định COMBO vs MUA LẺ (SINGLE ITEM)
            is_product_combo = any(w in p_name_no_acc for w in ("combo", "tron bo", "ca bo", "set bo", "full combo", "kem phao", "kem cuoc"))

            if is_combo_req:
                if is_product_combo:
                    score += 550
                else:
                    score -= 300
            elif is_single_req:
                # Khách yêu cầu mua LẺ: Trừ điểm rất nặng sản phẩm Combo để không bị lẫn lộn
                if is_product_combo:
                    score -= 800
                else:
                    score += 450

            # B. Phân định Danh mục chính xác tuyệt đối (Bao trùm không dấu)
            if is_box_float_req:
                if any(w in p_name_no_acc for w in ("hop phao", "hop dung phao", "hop phu kien", "hop")):
                    score += 650
                elif not is_combo_req:
                    # Trừ điểm cần câu / combo chỉ có quà tặng hộp phao
                    score -= 400

            if is_rod_req:
                if any(w in p_name_no_acc for w in ("can", "can cau", "can tay", "can dai", "can lure", "5h", "6h", "4h", "8h", "10h")):
                    score += 400
                if any(w in p_name_no_acc for w in ("rong", "dong", "tui dung", "ghe", "hop phao", "may cau")) and not is_combo_req:
                    score -= 500

            if is_float_req:
                if any(w in p_name_no_acc for w in ("phao", "phao dai", "phao nano", "phao co")):
                    score += 550
                elif not is_combo_req:
                    score -= 500

            if is_net_req:
                if any(w in p_name_no_acc for w in ("rong", "dong", "vot", "gat ca")):
                    score += 550
                else:
                    score -= 500

            if is_reel_req:
                if any(w in p_name_no_acc for w in ("may", "may cau", "coi")):
                    score += 550
                else:
                    score -= 500

            if is_chair_box_req:
                if any(w in p_name_no_acc for w in ("ghe", "thung", "tui")):
                    score += 500

            if is_fashion_req:
                if any(w in p_name_no_acc for w in ("ao", "quan", "vay", "dam", "khoac")):
                    score += 500

            if is_cosmetics_req:
                if any(w in p_name_no_acc for w in ("son", "kem", "phan", "serum")):
                    score += 500

            if is_tech_req:
                if any(w in p_name_no_acc for w in ("tai nghe", "tai nge", "loa", "sac", "pin")):
                    score += 500

            # C. Khớp từ khóa không dấu trực tiếp
            for kw_no in keywords_no_acc:
                if kw_no in ("combo", "re", "gia", "nhiu", "nhat"):
                    continue
                if kw_no in p_name_no_acc:
                    score += 50 + len(kw_no) * 5
                elif kw_no in p_desc_no_acc:
                    score += 15

            # D. Xử lý Ý định GIÁ RẺ hoặc CAO CẤP
            if is_cheap_req and p_price > 0:
                if min_price > 0:
                    cheap_bonus = int(max(0, 1.0 - (p_price - min_price) / max(1, max_price - min_price)) * 250)
                    score += cheap_bonus
            elif is_expensive_req and p_price > 0:
                if max_price > 0:
                    exp_bonus = int(max(0, (p_price - min_price) / max(1, max_price - min_price)) * 250)
                    score += exp_bonus

            scored_products.append((score, p))

        # Sắp xếp sản phẩm theo điểm số giảm dần
        scored_products.sort(key=lambda x: x[0], reverse=True)

        if scored_products and scored_products[0][0] > 30:
            return scored_products[0][1]

        return None

    def find_matched_product(self, text: str) -> dict[str, Any] | None:
        """Find product in catalog matching comment by explicit STT OR intelligent keyword semantics."""
        if not self.products_catalog:
            return None

        if self.is_gratitude_or_confirmation(text):
            return None

        # Tuyệt đối không match sản phẩm nếu câu hỏi thuộc chính sách TikTok Shop (Màu sắc combo/hàng thật trên live, ship, đồng kiểm, bảo hành, voucher)
        if self.tiktok_kb.detect_policy_intent(text):
            return None

        # 1. Ưu tiên khớp theo số STT cụ thể
        explicit_stt = self.is_explicit_product_query(text)
        if explicit_stt:
            for p in self.products_catalog:
                try:
                    if int(str(p.get("stt", 0))) == explicit_stt:
                        return p
                except Exception:
                    pass

        # 2. Khớp theo từ khóa sản phẩm thông minh (VD: 'lên mã phao', 'cho xem áo khoác', 'son đỏ', 'tai nghe')
        keyword_match = self.find_matched_product_by_keywords(text)
        if keyword_match:
            return keyword_match

        return None

    def is_advisory_or_knowledge_query(self, text: str) -> bool:
        """Kiểm tra xem khách có đang hỏi tư vấn kiến thức, cách dùng, chọn size, phối đồ, kỹ thuật không."""
        if self.is_gratitude_or_confirmation(text):
            return False

        # Nếu là câu hỏi chính sách TikTok Shop, không phân loại vào advisory chung
        if self.tiktok_kb.detect_policy_intent(text):
            return False

        t_low = text.lower().strip()
        advisory_keywords = [
            "tư vấn", "tu van", "nên mua", "nen mua", "loại nào", "loai nao", "chọn", "chon",
            "mấy h", "may h", "mấy mét", "may met", "cần gì", "mồi gì", "phao gì", "dây gì",
            "size gì", "mặc size", "nặng bao nhiêu", "cao mét", "kg mặc", "chất gì", "vải gì",
            "dùng cho", "da dầu", "da khô", "da mụn", "cách dùng", "hướng dẫn", "chống nước",
            "câu sông", "câu hồ", "săn hàng", "trời mưa", "thời tiết", "bo cá", "tải cá", "phôi carbon",
            "nước chảy", "cá chép", "cá trắm", "câu cá", "mùa này", "bo nổi", "đánh phao", "câu gì"
        ]
        return any(kw in t_low for kw in advisory_keywords)

    def find_best_product_for_advisory(self, text: str) -> dict[str, Any] | None:
        """Tìm sản phẩm phù hợp nhất trong giỏ hàng để gợi ý ghim cho khách khi hỏi tư vấn chung."""
        if not self.products_catalog:
            return None

        # 1. Thử tìm theo từ khóa xuất hiện trong câu tư vấn
        matched = self.find_matched_product_by_keywords(text)
        if matched:
            return matched

        # 2. Tìm theo đặc tính ngành hàng
        detected_domain = self.domain_adapter.detect_domain_from_catalog(self.products_catalog)
        t_low = text.lower()

        if detected_domain == "fishing":
            if any(w in t_low for w in ("săn hàng", "trắm đen", "cá to", "cá khủng", "8h", "10h", "bạo lực", "10kg", "15kg", "tra")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("7h", "8h", "9h", "10h", "săn hàng", "thánh kiếm", "đại lực")):
                        return p
            elif any(w in t_low for w in ("sông", "5h", "6h", "tổng hợp", "mới tập", "mới chơi")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("5h", "6h", "hoàng đan", "huyền thiên", "sông")):
                        return p
        elif detected_domain == "fashion_apparel":
            if any(w in t_low for w in ("ấm", "lạnh", "mùa đông", "khoác", "phao", "dày")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("phao", "khoác", "hoodie", "len", "nỉ", "dày")):
                        return p
            elif any(w in t_low for w in ("mát", "mùa hè", "thun", "ngắn tay", "cotton")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("thun", "polo", "cotton", "mát", "ngắn")):
                        return p
        elif detected_domain == "cosmetics_beauty":
            if any(w in t_low for w in ("mụn", "dầu", "sạch", "rửa mặt")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("rửa mặt", "bha", "mụn", "tràm trà")):
                        return p
            elif any(w in t_low for w in ("trắng", "sáng", "dưỡng", "serum")):
                for p in self.products_catalog:
                    p_name = p.get("name", "").lower()
                    if any(k in p_name for k in ("serum", "dưỡng", "trắng", "niacinamide", "kem")):
                        return p

        # Nếu không có sản phẩm khớp đặc tính tư vấn thì không tự tiện ghim bừa
        return None

    def generate_test_response(
        self,
        customer_name: str = "Khach_Hang",
        question: str = "",
        region_dialect: str | None = None,
        tone_style: str | None = None,
        use_slangs: bool | None = None,
    ) -> dict[str, Any]:
        """Generate response for instant testing preview with AI decision-driven auto-pin."""
        import re

        if region_dialect:
            self.region_dialect = region_dialect
        if tone_style:
            self.tone_style = tone_style
        if use_slangs is not None:
            self.use_slangs = use_slangs

        # GỬI Y NGUYÊN CHO AI PHÂN TÍCH VÀ QUYẾT ĐỊNH
        raw_reply = self._generate_ai_reply(customer_name, question)

        # BÓC TÁCH LỆNH GHIM DO AI CHỈ ĐỊNH
        pinned_id = None
        pin_tag_match = re.search(r"\[(?:GHIM|PIN|SP|MÃ)\s*[:#]?\s*(\d+)\]", raw_reply, re.IGNORECASE)
        if pin_tag_match:
            pinned_id = pin_tag_match.group(1)
        else:
            m_code = re.search(r"(?:mã|số|sp|combo|#)\s*(\d+)", raw_reply, re.IGNORECASE)
            if m_code:
                pinned_id = m_code.group(1)

        clean_reply = re.sub(r"\[(?:GHIM|PIN|SP|MÃ)\s*[:#]?\s*\d+\]", "", raw_reply).strip()
        clean_reply = re.sub(r"^@\S+\s*", "", clean_reply).strip()
        clamped_reply = self._clamp_message(clean_reply, nickname=customer_name, max_total_chars=95)

        if pinned_id and self.auto_pin_callback:
            self.auto_pin_callback(str(pinned_id))
            self.log("ACTION", f"📌 [AUTO-PIN] AI đã chỉ định Ghim SP #{pinned_id} theo câu hỏi của khách [{customer_name}]!")

        self.log("ACTION", f"⚡ [Test Host AI] Khách: '{question}' -> Trả lời ({self.region_dialect}): '{clamped_reply}'")
        return {
            "customer": customer_name,
            "question": question,
            "reply": clamped_reply,
            "pinned_id": pinned_id,
            "pinned_product_id": pinned_id,
            "region_dialect": self.region_dialect,
            "tone_style": self.tone_style,
            "time": time.strftime("%H:%M:%S"),
        }

    def benchmark_response_speed(self) -> dict[str, Any]:
        """Measure inference latency and tokens per second."""
        t0 = time.time()
        test_q = "Sản phẩm mã số 1 có ưu đãi gì và chất lượng thế nào shop?"
        matched = self.find_matched_product(test_q)
        ans = self._generate_ai_reply("Test_User", test_q, matched)
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "elapsed_ms": elapsed_ms,
            "response": ans,
            "gpu_accelerated": bool(self.qwen_engine and getattr(self.qwen_engine, "is_loaded", False)),
            "tokens_estimate": len(ans.split()) * 2,
        }

    def _typing_worker_loop(self) -> None:
        """Background worker gửi nguyên bản comment cho AI xử lý và điều khiển DOM ghim/trả lời."""
        import re

        while self.is_running:
            try:
                nickname, comment_text = self._reply_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            nick_low = nickname.lower().strip().lstrip("@")
            cmt_low = comment_text.lower().strip()
            norm_cmt = " ".join(cmt_low.split())
            fingerprint = f"{nick_low}::{norm_cmt}"

            # Nếu bình luận này đã từng được trả lời thành công -> Bỏ qua chống lặp
            if fingerprint in self._replied_comment_fingerprints:
                self._in_progress_comments.discard(fingerprint)
                self._active_queue_users.discard(nick_low)
                continue

            try:
                # 0. Lọc bỏ chỉ những tin nhắn thực sự là của Host / Chủ phòng
                host_blacklist = ["chủ phòng", "chu phong", "quản trị viên", "quan tri vien", "admin", "(bạn)"]
                if any(k == nick_low or f"({k})" in nick_low for k in host_blacklist) or (self.username and self.username.lower() == nick_low):
                    self._in_progress_comments.discard(fingerprint)
                    continue

                # Cập nhật trạng thái Đang xử lý
                if nick_low in self._customer_registry:
                    self._customer_registry[nick_low]["status"] = "PROCESSING"

                self.log("ACTION", f"🧠 [GỬI AI PHÂN TÍCH] Khách [{nickname}]: \"{comment_text}\"")

                # 1. GỬI Y NGUYÊN COMMENT CHO AI TỰ PHÂN TÍCH VÀ QUYẾT ĐỊNH
                raw_ai_reply = self._generate_ai_reply(nickname, comment_text)

                # 2. BÓC TÁCH LỆNH GHIM DO AI CHỈ ĐỊNH (AI tự tra cứu {{List san pham}} và quyết định)
                pinned_stt = ""
                # Tìm thẻ chỉ định ghim rõ ràng do AI trả về: [GHIM: X] hoặc [PIN: X]
                pin_tag_match = re.search(r"\[(?:GHIM|PIN|SP|MÃ)\s*[:#]?\s*(\d+)\]", raw_ai_reply, re.IGNORECASE)
                if pin_tag_match:
                    pinned_stt = pin_tag_match.group(1)
                else:
                    # Hoặc nếu AI đề cập đến mã sản phẩm trong câu trả lời
                    m_code = re.search(r"(?:mã|số|sp|combo|#)\s*(\d+)", raw_ai_reply, re.IGNORECASE)
                    if m_code:
                        pinned_stt = m_code.group(1)

                # 3. ĐIỀU KHIỂN DOM: NẾU AI RA LỆNH GHIM MÃ NÀO THÌ APP GHIM TRÊN DOM MÃ ĐÓ
                if pinned_stt and self.auto_pin_callback:
                    try:
                        self.log("SUCCESS", f"📌 [AI CHỈ ĐỊNH GHIM] AI quyết định ghim SP #{pinned_stt} theo câu hỏi của khách [{nickname}]!")
                        self.auto_pin_callback(str(pinned_stt))
                    except Exception as pin_err:
                        self.log("ERROR", f"❌ Lỗi điều khiển DOM ghim SP #{pinned_stt}: {pin_err}")

                # 4. CHUẨN HÓA CÂU TRẢ LỜI SẠCH SẼ (Gỡ bỏ thẻ kỹ thuật [GHIM: X] nếu có)
                clean_ai_reply = re.sub(r"\[(?:GHIM|PIN|SP|MÃ)\s*[:#]?\s*\d+\]", "", raw_ai_reply).strip()
                clean_ai_reply = re.sub(r"^@\S+\s*", "", clean_ai_reply).strip()
                clamped_reply = self._clamp_message(clean_ai_reply, nickname=nickname, max_total_chars=95)

                # 5. ĐIỀU KHIỂN DOM: GÕ VÀO CHATBOX TRÊN TIKTOK LIVE DASHBOARD
                success = self._type_into_chatbox(message=clamped_reply, nickname=nickname, comment_snippet=comment_text)
                if success:
                    self._reply_count += 1
                    self._replied_comment_fingerprints.add(fingerprint)
                    self._in_progress_comments.discard(fingerprint)

                    if nick_low in self._customer_registry:
                        self._customer_registry[nick_low]["status"] = "REPLIED"
                        self._customer_registry[nick_low]["last_reply"] = clamped_reply

                    self.log("SUCCESS", f"🤖 [DOM ĐÃ TRẢ LỜI] @{nickname}: {clamped_reply}")

                # 6. Bắn sự kiện hiển thị lên giao diện UI DTA AutoLive
                if self.event_callback:
                    try:
                        self.event_callback({
                            "type": "HOST_CHATBOT_REPLY_EVENT",
                            "data": {
                                "customer": nickname,
                                "question": comment_text,
                                "reply": clamped_reply,
                                "pinned_product_id": pinned_stt if pinned_stt else None,
                                "region_dialect": self.region_dialect,
                                "tone_style": self.tone_style,
                                "status": "REPLIED" if success else "FAILED",
                                "time": time.strftime("%H:%M:%S"),
                            }
                        })
                    except Exception:
                        pass

                # Khoảng nghỉ tự nhiên tránh bị TikTok chặn spam
                time.sleep(random.uniform(1.6, 2.8))

            except Exception as loop_err:
                self.log("WARNING", f"⚠️ Ngoại lệ trong luồng trả lời chat: {loop_err}")
            finally:
                self._user_last_reply[nick_low] = time.time()
                self._in_progress_comments.discard(fingerprint)
                self._active_queue_users.discard(nick_low)

    def _clamp_message(self, reply: str, nickname: str = "", max_total_chars: int = 95) -> str:
        """Khóa cứng giới hạn an toàn tối đa 95 ký tự (đã trừ hao độ dài tiền tố @nickname).

        Sử dụng thuật toán cắt thông minh tại dấu câu (., !, ?, ,) hoặc dấu cách gần nhất,
        đảm bảo câu luôn trọn vẹn ý nghĩa, không bị cụt chữ và được TikTok Live chấp nhận 100%.
        """
        clean_reply = reply.strip()

        # 1. Tính toán trừ hao độ dài của tiền tố @nickname
        prefix_len = 0
        if nickname:
            clean_nick = nickname.strip().lstrip("@")
            if clean_nick:
                prefix_len = len(f"@{clean_nick} ")

        # Độ dài tối đa dành riêng cho phần nội dung trả lời
        target_max = max(max_total_chars - prefix_len, 25)

        if len(clean_reply) <= target_max:
            return clean_reply

        # 2. Thuật toán cắt thông minh tại ranh giới dấu câu hoặc khoảng trắng
        sub = clean_reply[:target_max].rstrip()

        # Ưu tiên 1: Cắt tại dấu câu hoàn chỉnh câu (. ! ?)
        sentence_enders = [". ", "! ", "? ", ".", "!", "?"]
        best_idx = -1
        best_sep_len = 0
        for sep in sentence_enders:
            idx = sub.rfind(sep)
            if idx >= max(0, target_max - 28) and idx > best_idx:
                best_idx = idx
                best_sep_len = len(sep.strip())
        if best_idx != -1:
            return sub[:best_idx + best_sep_len].strip()

        # Ưu tiên 2: Cắt tại dấu phẩy hoặc dấu cách gần nhất để không bao giờ cụt chữ
        for sep in [", ", ",", " "]:
            idx = sub.rfind(sep)
            if idx >= max(0, target_max - 22):
                truncated = sub[:idx].rstrip().rstrip(",").strip()
                if truncated and truncated[-1] not in (".", "!", "?"):
                    truncated += "!"
                return truncated

        # Fallback an toàn
        return sub

    def _generate_ai_reply(
        self,
        nickname: str,
        comment_text: str,
        matched_product: dict[str, Any] | None = None,
        suggested_product: dict[str, Any] | None = None,
    ) -> str:
        """Sinh câu trả lời trực tiếp từ Mô hình AI dựa 100% vào Kịch bản & Prompt do người dùng cấu hình trên UI."""
        import re

        # Gọi trực tiếp Động cơ AI (DeepSeek / Qwen) với Prompt Template của Người dùng
        user_query = f"Khách hàng [{nickname}] bình luận: \"{comment_text}\""
        gen_out = self._call_active_ai_engine(user_query, max_tokens=150)

        if gen_out:
            clean_reply = re.sub(r"^@\S+\s*", "", gen_out.strip()).strip()
            return self._clamp_message(clean_reply, nickname=nickname, max_total_chars=95)

        # Fallback tối giản chỉ khi AI Engine chưa sẵn sàng (chưa tải model hoặc chưa nhập API Key)
        target_prod = matched_product or suggested_product or self.find_matched_product(comment_text)
        if target_prod:
            stt = target_prod.get("stt", "1")
            name = target_prod.get("name", f"Mã #{stt}")
            price = format_price_shorthand(target_prod.get("sale_price") or target_prod.get("price") or "")
            return f"[GHIM: {stt}] Dạ em ghim mã #{stt} ({name[:20]}) giá {price} lên góc trái rồi ạ!"

        return "Dạ shop chào bác ạ! Bác cần tư vấn mẫu nào cứ nhắn em hỗ trợ ngay nha!"

    def handle_pin_callout(self, prod_info: dict[str, Any]) -> str:
        """Kêu gọi chốt đơn khi ghim sản phẩm mới lên live."""
        stt = prod_info.get("stt") or prod_info.get("product_id") or "1"
        raw_name = prod_info.get("name") or prod_info.get("product_name") or f"Sản phẩm #{stt}"
        sale_price = prod_info.get("sale_price") or prod_info.get("price") or ""
        return f"🔥 Em vừa ghim mã #{stt} ({raw_name[:25]}) giá ưu đãi {sale_price}! Bác bấm góc trái màn hình săn liền nha!"

    def _call_active_ai_engine(self, prompt: str, max_tokens: int = 150) -> str | None:
        """Call DeepSeek V3 (Cloud) or Qwen Local (GPU) using the user's Dynamic Prompt Template."""
        active_system_prompt = self.build_system_prompt_from_template()

        # 1. DeepSeek V3 if configured or provider is 'deepseek' / 'auto'
        if self.ai_provider in ("deepseek", "auto") and self.deepseek_engine and getattr(self.deepseek_engine, "is_configured", False):
            try:
                gen_out = self.deepseek_engine.generate_response(
                    user_prompt=prompt,
                    system_prompt=active_system_prompt,
                    knowledge_catalog="",  # Đã nhúng trực tiếp trong {{List san pham}} của system prompt
                    region_dialect=self.region_dialect,
                    tone_style=self.tone_style,
                    use_slangs=self.use_slangs,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                if gen_out:
                    return gen_out
            except Exception as e:
                logger.warning("deepseek_engine_call_fallback", error=str(e))

        # 2. Qwen Local Engine (GPU Offline)
        if self.qwen_engine and getattr(self.qwen_engine, "is_loaded", False) and self.qwen_engine.llm != "SIMULATED_ENGINE":
            try:
                gen_out = self.qwen_engine.generate_response(
                    user_prompt=prompt,
                    system_prompt=active_system_prompt,
                    knowledge_catalog="",
                    region_dialect=self.region_dialect,
                    tone_style=self.tone_style,
                    use_slangs=self.use_slangs,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                if gen_out:
                    return gen_out
            except Exception as e:
                logger.warning("qwen_engine_call_failed", error=str(e))

        return None

    def log(self, tag: str, text: str) -> None:
        """Log to console."""
        if self.log_callback:
            self.log_callback(tag, text)
        else:
            try:
                logger.info("host_chat_responder", tag=tag, text=text)
            except Exception:
                pass

    def set_status(self, text: str, color: str = "#00FF66") -> None:
        """Update status badge."""
        if self.status_callback:
            self.status_callback(text, color)

    def start_responder(
        self,
        username: str,
        system_prompt: str = "",
        knowledge_catalog_text: str = "",
    ) -> bool:
        """Start listening to comments and auto-replying in chatbox."""
        if self.is_running:
            self.log("WARNING", "⚠️ Host Live Chatbot đang hoạt động!")
            return False

        clean_user = username.strip().replace("@", "")
        if not clean_user:
            self.log("ERROR", "❌ Chưa nhập tên tài khoản TikTok Live (@username)!")
            return False

        self.username = clean_user
        self.system_prompt = system_prompt
        self.knowledge_catalog_text = knowledge_catalog_text
        self.is_running = True
        self._reply_count = 0

        self.set_status("Đang Trả Lời Live (Qwen GPU)...", "#00FFFF")
        self.log("SUCCESS", f"🤖 Đã kích hoạt Host Auto-Responder cho kênh @{self.username} (Động cơ Qwen Local GPU).")

        # Start background typing worker
        self._worker_thread = threading.Thread(target=self._typing_worker_loop, daemon=True)
        self._worker_thread.start()

        # Start TikTok Live chat listener
        self._listener_thread = threading.Thread(target=self._run_live_listener, daemon=True)
        self._listener_thread.start()

        return True

    def stop_responder(self) -> None:
        """Stop host chat responder."""
        if self.is_running:
            self.is_running = False
            try:
                if self._tiktok_client:
                    self._tiktok_client.stop()
            except Exception:
                pass
        self.set_status("Đã Dừng Chatbot", "#FFCC00")
        self.log("SYSTEM", f"🛑 Đã dừng Host Chatbot. Tổng số câu đã trả lời: {self._reply_count}")

    def get_customer_tracking_summary(self) -> list[dict[str, Any]]:
        """Lấy danh sách trạng thái nhận diện khách hàng: Đã trả lời / Đang chờ / Đang xử lý."""
        return list(self._customer_registry.values())

    def enqueue_comment(self, nickname: str, comment_text: str) -> None:
        """Đưa bình luận vào hàng đợi xử lý với hệ thống nhận diện và chống vòng lặp lặp lại tuyệt đối."""
        if not self.is_running:
            return

        clean_nick = nickname.strip()
        clean_cmt = comment_text.strip()
        if not clean_nick or not clean_cmt:
            return

        norm_nick = clean_nick.lower()
        norm_cmt = " ".join(clean_cmt.lower().split())
        fingerprint = f"{norm_nick}::{norm_cmt}"

        now = time.time()

        # 1. KIỂM TRA ĐÃ TRẢ LỜI CHƯA: Nếu dấu vân tay comment này ĐÃ ĐƯỢC TRẢ LỜI -> BỎ QUA 100%
        if fingerprint in self._replied_comment_fingerprints:
            return

        # 2. KIỂM TRA ĐANG TRONG HÀNG ĐỢI HOẶC ĐANG GÕ -> BỎ QUA 100%
        if fingerprint in self._in_progress_comments:
            return

        # 3. User Cooldown: Nếu khách vừa được rep trong 15s qua mà gửi lại câu tương tự -> BỎ QUA
        if norm_nick in self._user_last_reply and (now - self._user_last_reply[norm_nick] < 15.0):
            # Nếu là comment giống hệt câu vừa rep -> Bỏ qua
            reg = self._customer_registry.get(norm_nick)
            if reg and reg.get("last_comment") == clean_cmt:
                return

        # Đánh dấu comment đang được tiếp nhận xử lý
        self._in_progress_comments.add(fingerprint)
        self._active_queue_users.add(norm_nick)

        # Cập nhật Registry theo dõi khách hàng
        if norm_nick not in self._customer_registry:
            self._customer_registry[norm_nick] = {
                "nickname": clean_nick,
                "total_comments": 1,
                "last_comment": clean_cmt,
                "last_reply": "",
                "status": "PENDING",  # PENDING | PROCESSING | REPLIED
                "time": time.strftime("%H:%M:%S"),
            }
        else:
            self._customer_registry[norm_nick]["total_comments"] += 1
            self._customer_registry[norm_nick]["last_comment"] = clean_cmt
            self._customer_registry[norm_nick]["status"] = "PENDING"
            self._customer_registry[norm_nick]["time"] = time.strftime("%H:%M:%S")

        self.log("INFO", f"💬 [CHƯA TRẢ LỜI] Tiếp nhận bình luận mới từ [{clean_nick}]: \"{clean_cmt}\"")
        self._reply_queue.put((clean_nick, clean_cmt))

    def _type_into_chatbox(self, message: str, nickname: str = "", comment_snippet: str = "") -> bool:
        """Locate chat input in Streamer Dashboard, click 'Trả lời' on comment, type message and trigger Send once."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                except Exception as conn_err:
                    self.log("ERROR", f"❌ Không thể kết nối Chrome CDP (port {self.cdp_port}): {conn_err}")
                    return False

                contexts = browser.contexts
                active_context = contexts[0] if contexts else browser
                pages = active_context.pages

                target_page = None
                for pg in pages:
                    try:
                        url_l = (pg.url or "").lower()
                        if "tiktok.com" in url_l and ("streamer" in url_l or "product" in url_l or "dashboard" in url_l):
                            target_page = pg
                            break
                    except Exception:
                        pass

                page = target_page or (pages[0] if pages else None)
                if not page:
                    self.log("WARNING", "⚠️ Không tìm thấy tab TikTok Live Dashboard đang mở trên Chrome.")
                    return False

                # =========================================================================
                # VÙNG 2: TƯƠNG TÁC TRẢ LỜI COMMENT KHÁCH HÀNG
                # 1. Di chuột (Hover) vào comment để hiện 3 nút (Trả lời, Ghim, Khác)
                # 2. Bấm nút "Trả lời" (Reply)
                # 3. Gõ câu trả lời theo đúng prompt kịch bản và gửi đi
                # =========================================================================
                try:
                    cards = page.locator("div.rounded-8.relative:not(:has-text('Chủ phòng')):not(:has-text('Quản trị viên')), div[class*='comment-item']:not(:has-text('Chủ phòng')), div[class*='chat-item']:not(:has-text('Chủ phòng')), div[class*='message-item']:not(:has-text('Chủ phòng'))")
                    count = cards.count()
                    if count > 0:
                        target_card = None
                        if nickname:
                            nick_clean = nickname.replace("@", "").strip()
                            nick_cards = cards.filter(has_text=nick_clean)
                            if nick_cards.count() > 0:
                                target_card = nick_cards.nth(nick_cards.count() - 1)
                        if not target_card and comment_snippet:
                            snip_clean = comment_snippet.strip()[:10]
                            snip_cards = cards.filter(has_text=snip_clean)
                            if snip_cards.count() > 0:
                                target_card = snip_cards.nth(snip_cards.count() - 1)
                        if not target_card:
                            target_card = cards.nth(count - 1)

                        box = target_card.bounding_box()
                        if box:
                            # 1. Di chuyển chuột thật vào vị trí thẻ comment để kích hoạt hiển thị 3 nút
                            page.mouse.move(box["x"] + box["width"] - 25, box["y"] + 12)
                            time.sleep(0.15)

                            # 2. Tìm và BẤM NÚT TRẢ LỜI (svg.arco-icon-recover / button Trả lời)
                            reply_btn = target_card.locator("button:has(svg.arco-icon-recover), svg.arco-icon-recover, button[aria-label*='Trả lời'], button[aria-label*='Reply'], button[title*='Trả lời'], button:has-text('Trả lời')").first
                            if reply_btn.is_visible():
                                reply_btn.click()
                            else:
                                # Nhấp tọa độ chính xác của nút Trả lời (cách mép phải comment khoảng 75px)
                                page.mouse.click(box["x"] + box["width"] - 75, box["y"] + 12)
                            time.sleep(0.2)
                except Exception as hover_err:
                    self.log("WARNING", f"⚠️ [VÙNG 2] Hover comment để hiện nút Reply: {hover_err}")

                # Bước 2: Tìm ô Chatbox trên Streamer Dashboard (Bao quát cả input, textarea, arco design)
                chat_locator = page.locator("input[placeholder*='Nhập'], textarea[placeholder*='Nhập'], textarea.arco-textarea, [contenteditable='true'], input[type='text'], textarea").first
                if not chat_locator.is_visible():
                    chat_locator = page.locator("[contenteditable='true']").first

                if not chat_locator.is_visible():
                    self.log("ERROR", "❌ Không tìm thấy ô nhập chatbox trên màn hình Live.")
                    return False

                # Đọc giá trị hiện tại của chatbox (TikTok thường tự điền @nickname sau khi bấm Reply)
                current_val = ""
                try:
                    current_val = (chat_locator.input_value() if hasattr(chat_locator, "input_value") else "") or ""
                except Exception:
                    pass

                # Lọc bỏ sạch mọi thẻ @ ở đầu câu trả lời nếu AI vô tình sinh ra
                import re
                clean_body = re.sub(r"^@\S+\s*", "", message.strip()).strip()

                # Kiểm tra xem TikTok đã tự động điền thẻ @tenkhach sau khi bấm Reply hay chưa
                if current_val.startswith("@"):
                    tag_prefix = current_val.strip() + " "
                    clamped_body = self._clamp_message(clean_body, nickname=tag_prefix, max_total_chars=95)
                    final_text = f"{tag_prefix}{clamped_body}".strip()
                else:
                    # Nếu nút Reply chưa gắn thẻ, chỉ gõ nội dung thuần câu trả lời
                    clamped_body = self._clamp_message(clean_body, nickname="", max_total_chars=95)
                    final_text = clamped_body.strip()

                # Khóa cứng an toàn hai lớp: Tối đa 95 ký tự, không bị cụt chữ
                if len(final_text) > 95:
                    sub_final = final_text[:95].rstrip()
                    for sep in [".", "!", "?", ",", " "]:
                        idx = sub_final.rfind(sep)
                        if idx >= 75:
                            sub_final = sub_final[:idx].rstrip().rstrip(",")
                            if sub_final and sub_final[-1] not in (".", "!", "?"):
                                sub_final += "!"
                            break
                    final_text = sub_final

                # Bước 3: Gõ nội dung và gửi ĐÚNG 1 LẦN DUY NHẤT
                chat_locator.click()
                chat_locator.fill(final_text)
                time.sleep(0.15)
                chat_locator.press("Enter")
                time.sleep(0.3)

                # Bước 4: Kiểm tra nếu ô chat vẫn chưa gửi được (còn chữ) -> Click nút Gửi fallback
                try:
                    rem_val = (chat_locator.input_value() if hasattr(chat_locator, "input_value") else "") or ""
                    if rem_val != "":
                        send_btn = page.locator("span.index-module__fillIcon--ziNjQ, svg.arco-icon-publish_management_fill, button:has-text('Gửi'), [aria-label*='Gửi']").first
                        if send_btn.is_visible():
                            send_btn.click()
                            time.sleep(0.15)
                except Exception:
                    pass

                return True

        except Exception as e:
            self.log("ERROR", f"❌ Lỗi khi gửi câu trả lời vào chatbox: {e}")
            return False

    def _run_live_listener(self) -> None:
        """Lắng nghe luồng chat và sự kiện xem sản phẩm trực tiếp từ Tab Chrome Live Dashboard qua CDP."""
        from collections import deque
        from playwright.sync_api import sync_playwright

        seen_messages: set[str] = set()
        seen_queue: deque[str] = deque(maxlen=400)

        self.log("INFO", f"📡 Đang kết nối Chrome CDP ({self.cdp_port}) để đọc luồng bình luận & sự kiện người xem...")

        while self.is_running:
            try:
                with sync_playwright() as p:
                    try:
                        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                    except Exception as err:
                        time.sleep(2.0)
                        continue

                    contexts = browser.contexts
                    active_context = contexts[0] if contexts else browser
                    pages = active_context.pages

                    target_page = None
                    for pg in pages:
                        try:
                            url_l = (pg.url or "").lower()
                            if "tiktok.com" in url_l:
                                target_page = pg
                                break
                        except Exception:
                            pass

                    if not target_page and pages:
                        target_page = pages[0]

                    if not target_page:
                        time.sleep(2.0)
                        continue

                    self.log("SUCCESS", "🟢 Đã kết nối thành công đến bảng Live TikTok! Đang nhận diện bình luận của khách...")

                    # Vòng lặp quét tin nhắn liên tục từ DOM
                    while self.is_running:
                        try:
                            structured_items: list[dict[str, Any]] = target_page.evaluate(r"""() => {
                                const items = [];
                                
                                // 1. Tìm vùng chứa bình luận (Chatbox List)
                                let chatContainer = document.body;
                                const chatInput = document.querySelector("input[placeholder*='Nhập'], textarea[placeholder*='Nhập'], [contenteditable='true'], textarea, input[type='text']");
                                if (chatInput) {
                                    let p = chatInput.parentElement;
                                    for (let i = 0; i < 10; i++) {
                                        if (!p || p === document.body) break;
                                        const pTxt = p.innerText || '';
                                        if (pTxt.includes('Trò chuyện') || pTxt.includes('Bình luận') || pTxt.includes('Tất cả bình luận') || p.scrollHeight > 250) {
                                            chatContainer = p;
                                            break;
                                        }
                                        p = p.parentElement;
                                    }
                                }

                                // 2. Quét TẤT CẢ các thẻ comment bên trong chatContainer
                                const commentCards = Array.from(chatContainer.querySelectorAll("div, li, [role='listitem']")).filter(el => {
                                    if (el.querySelector('table, .arco-table, video, canvas, select, input, textarea')) return false;
                                    if (el.closest('table, .arco-table, [class*="product-list"]')) return false;
                                    const raw = (el.innerText || '').trim();
                                    if (!raw || raw.length < 1 || raw.length > 300) return false;
                                    return el.children.length >= 1 && el.children.length <= 8;
                                });

                                for (const card of commentCards) {
                                    const rawText = (card.innerText || '').trim();
                                    if (!rawText) continue;

                                    const rawLower = rawText.toLowerCase();

                                    // Chỉ bỏ qua các thông báo hệ thống của TikTok (vào phòng, quà tặng, follow, share)
                                    if (rawLower.includes('vừa tham gia') || rawLower.includes('đã thích') || rawLower.includes('đã chia sẻ') || rawLower.includes('đã gửi quà') || rawLower.includes('chào mừng bạn đến')) {
                                        continue;
                                    }

                                    // Bỏ qua nếu chính xác là tin nhắn từ Host / Chủ phòng
                                    if (rawLower.includes('chủ phòng') || rawLower.includes('quản trị viên') || rawLower.includes('(bạn)')) {
                                        continue;
                                    }

                                    // Lấy tên khách và nội dung comment từ cấu trúc DOM
                                    let user = '';
                                    let content = '';

                                    const nameEl = card.querySelector(".text-body-s-medium, [data-tid='m4b_overflow_text_single'], [class*='truncate'], span[class*='name'], div[class*='name']");
                                    const msgEl = card.querySelector(".text-neutral-text1, .text-body-s-regular, [class*='pl-32'], [class*='content'], [class*='text']");

                                    if (nameEl && msgEl && nameEl !== msgEl) {
                                        user = (nameEl.innerText || '').trim();
                                        content = (msgEl.innerText || '').trim();
                                    } else {
                                        const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
                                        if (lines.length >= 2) {
                                            user = lines[0];
                                            content = lines.slice(1).join(' ');
                                        } else if (rawText.includes(':')) {
                                            const colonIdx = rawText.indexOf(':');
                                            user = rawText.substring(0, colonIdx).trim();
                                            content = rawText.substring(colonIdx + 1).trim();
                                        }
                                    }

                                    user = user.replace(/(?:fan\s*cứng|cấp\s*\d+|lv\.\s*\d+|no\.\s*\d+|thành\s*viên)/gi, '').trim();

                                    if (user && content && user !== content) {
                                        items.push({
                                            type: 'COMMENT',
                                            user: user,
                                            content: content,
                                            raw: rawText
                                        });
                                    }
                                }

                                // 3. Quét các sự kiện người xem bấm vào giỏ hàng / xem sản phẩm
                                const filterRows = Array.from(chatContainer.querySelectorAll("div[type*='filter'], div[class*='items-center']")).filter(el => {
                                    const t = (el.innerText || '').trim();
                                    return t.includes('đang xem sản phẩm này');
                                });

                                for (const row of filterRows) {
                                    const rawText = (row.innerText || '').trim();
                                    if (rawText.includes('đang xem sản phẩm này')) {
                                        const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
                                        const user = (lines[0] || 'Khách_Xem').replace(/đang xem.*$/i, '').trim();
                                        let stt = null;
                                        const sttMatch = rawText.match(/(?:Số|#)\s*(\d+)/i) || rawText.match(/(\d+)/);
                                        if (sttMatch) stt = parseInt(sttMatch[1], 10);
                                        items.push({
                                            type: 'VIEW_PRODUCT',
                                            user: user,
                                            stt: stt,
                                            raw: rawText
                                        });
                                    }
                                }

                                const unique = [];
                                const seenRaw = new Set();
                                for (const it of items) {
                                    if (!seenRaw.has(it.raw)) {
                                        seenRaw.add(it.raw);
                                        unique.push(it);
                                    }
                                }
                                return unique.slice(-35);
                            }""")

                            for item in structured_items:
                                itype = item.get("type")
                                user_nick = item.get("user", "").strip()
                                cmt_body = item.get("content", "").strip()

                                if itype == "VIEW_PRODUCT":
                                    stt_viewed = item.get("stt")
                                    view_key = f"VIEW::{user_nick.lower()}::{stt_viewed}"
                                    if view_key in seen_messages:
                                        continue
                                    seen_messages.add(view_key)
                                    seen_queue.append(view_key)
                                    if len(seen_messages) > 400:
                                        oldest = seen_queue.popleft()
                                        seen_messages.discard(oldest)

                                    viewer_name = user_nick or "Khách_Xem"
                                    self.log("INFO", f"👀 [LIVE SỰ KIỆN] Khán giả [{viewer_name}] đang xem sản phẩm #{stt_viewed}!")
                                    if self.auto_pin_callback and stt_viewed:
                                        try:
                                            self.auto_pin_callback(int(stt_viewed))
                                        except Exception:
                                            pass

                                elif itype == "COMMENT":
                                    if not user_nick or not cmt_body:
                                        continue
                                    norm_key = f"CMT::{user_nick.lower()}::{' '.join(cmt_body.lower().split())}"
                                    if norm_key in seen_messages:
                                        continue
                                    seen_messages.add(norm_key)
                                    seen_queue.append(norm_key)
                                    if len(seen_messages) > 400:
                                        oldest = seen_queue.popleft()
                                        seen_messages.discard(oldest)

                                    # Đưa Y NGUYÊN comment của khách vào hàng đợi để gửi cho AI
                                    self.enqueue_comment(user_nick, cmt_body)

                        except Exception:
                            time.sleep(1.0)

                        time.sleep(0.5)

            except Exception:
                time.sleep(2.0)

