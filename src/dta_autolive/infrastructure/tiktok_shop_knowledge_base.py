"""DTA Studio - TikTok Shop Knowledge Base & AI Sales Brain.

Bách khoa toàn thư chính sách bán hàng & Bộ não AI Sales thực chiến trên TikTok Shop.
Giải quyết triệt để các lỗi trả lời lệch sóng, trả lời sai sự thật hoặc nhảy nhầm sản phẩm ghim.
"""

import random


class TikTokShopKnowledgeBase:
    """Bách khoa toàn thư & Bộ điều phối tri thức bán hàng TikTok Shop thực chiến."""

    # 1. TỪ KHÓA NHẬN DIỆN MÀU SẮC COMBO & HÌNH THẬT TRÊN LIVE
    COLOR_REAL_ITEM_KEYWORDS = [
        "đúng màu", "dung mau", "chuẩn màu", "chuan mau", "giống trên live", "giong tren live",
        "giống live", "giong live", "như trên live", "nhu tren live", "như live", "nhu live",
        "màu như live", "mau nhu live", "màu trên live", "mau tren live", "combo có đúng màu",
        "combo co dung mau", "combo giống", "combo giong", "có giống hình", "co giong hinh",
        "giống ảnh", "giong anh", "hàng thật", "hang that", "hình thật", "hinh that",
        "ở ngoài giống", "o ngoai giong", "bên ngoài có giống", "ben ngoai co giong",
        "có ảo không", "co ao khong", "màu thật", "mau that", "ảnh thật", "anh that",
        "chuẩn hình", "chuan hinh", "y hình", "y hinh", "y live", "đúng mẫu", "dung mau"
    ]

    # 2. TỪ KHÓA NHẬN DIỆN THỜI GIAN GIAO HÀNG / SHIP
    SHIPPING_KEYWORDS = [
        "bao giờ nhận", "bao gio nhan", "khi nào nhận", "khi nao nhan", "mấy ngày nhận", "may ngay nhan",
        "mấy ngày tới", "may ngay toi", "mấy ngày đến", "may ngay den", "bao lâu nhận", "bao lau nhan",
        "bao lâu tới", "bao lau toi", "bao lâu thì có", "bao lau thi co", "bao giờ có hàng", "bao gio co hang",
        "khi nào giao", "khi nao giao", "khi nào tới", "khi nao toi", "ship mấy ngày", "ship may ngay",
        "ship bao lâu", "ship bao lau", "giao mấy ngày", "giao may ngay", "giao bao lâu", "giao bao lau",
        "giao hàng nhanh không", "giao hang nhanh khong", "vận chuyển mấy ngày", "van chuyen may ngay",
        "ship hỏa tốc", "ship nhanh", "giao nhanh", "đặt thì bao giờ", "dat thi bao gio"
    ]

    # 3. TỪ KHÓA NHẬN DIỆN ĐỒNG KIỂM / MỞ RA XEM
    CO_INSPECTION_KEYWORDS = [
        "mở ra xem", "mo ra xem", "được mở", "duoc mo", "cho mở", "cho mo",
        "xem hàng", "xem hang", "được xem hàng", "duoc xem hang", "cho xem hàng", "cho xem hang",
        "đồng kiểm", "dong kiem", "có đồng kiểm", "co dong kiem", "kiểm tra hàng", "kiem tra hang",
        "cho kiểm", "cho kiem", "được kiểm", "duoc kiem", "xem trước khi", "xem truoc khi",
        "mở hộp", "mo hop", "bóc hàng", "boc hang", "khui hàng", "khui hang",
        "kiểm tra rồi mới", "kiem tra roi moi", "xem có ưng", "xem co ung"
    ]

    # 4. TỪ KHÓA NHẬN DIỆN BẢO HÀNH & ĐỔI TRẢ
    RETURN_WARRANTY_KEYWORDS = [
        "đổi trả", "doi tra", "được đổi", "duoc doi", "cho đổi", "cho doi",
        "lỗi thì sao", "loi thi sao", "lỗi đổi", "loi doi", "bị lỗi", "bi loi",
        "bảo hành", "bao hanh", "hỏng thì sao", "hong thi sao", "gãy thì sao", "gay thi sao",
        "không vừa", "khong vua", "đổi size", "doi size", "hàng lỗi", "hang loi",
        "trả hàng", "tra hang", "hoàn tiền", "hoan tien", "chính sách đổi", "chinh sach doi"
    ]

    # 5. TỪ KHÓA NHẬN DIỆN VOUCHER / FREESHIP
    VOUCHER_FREESHIP_KEYWORDS = [
        "freeship", "free ship", "miễn phí ship", "mien phi ship", "phí ship", "phi ship",
        "có freeship", "co freeship", "freeship không", "freeship ko", "free ship ko",
        "bao ship", "có bao ship", "co bao ship", "miễn ship", "mien ship", "tiền ship", "tien ship",
        "ship đắt", "ship dat", "hỗ trợ ship", "ho tro ship", "ship cao",
        "voucher", "mã giảm", "ma giam", "mã freeship", "ma freeship", "mã giảm giá", "ma giam gia",
        "ưu đãi", "uu dai", "khuyến mãi", "khuyen mai", "giảm 30k", "giam 30k", "giảm 50k", "giam 50k",
        "áp mã", "ap ma", "lưu mã", "luu ma", "săn mã", "san ma", "mã vận chuyển", "ma van chuyen"
    ]

    @classmethod
    def is_color_or_real_item_query(cls, text: str) -> bool:
        """Khách hỏi về màu sắc combo trên live, hình thật, chất lượng thật bên ngoài."""
        t_low = text.lower().strip()
        # Chặn các câu ghim hỏi đích danh (VD: "mã 1 màu gì", "cho xem màu mã 2")
        return any(kw in t_low for kw in cls.COLOR_REAL_ITEM_KEYWORDS)

    @classmethod
    def is_shipping_query(cls, text: str) -> bool:
        """Khách hỏi về thời gian giao hàng, ship mấy ngày, khi nào tới."""
        t_low = text.lower().strip()
        return any(kw in t_low for kw in cls.SHIPPING_KEYWORDS)

    @classmethod
    def is_co_inspection_query(cls, text: str) -> bool:
        """Khách hỏi về chính sách đồng kiểm, mở ra xem hàng trước khi nhận."""
        t_low = text.lower().strip()
        return any(kw in t_low for kw in cls.CO_INSPECTION_KEYWORDS)

    @classmethod
    def is_return_warranty_query(cls, text: str) -> bool:
        """Khách hỏi về chính sách đổi trả, bảo hành, hàng lỗi."""
        t_low = text.lower().strip()
        return any(kw in t_low for kw in cls.RETURN_WARRANTY_KEYWORDS)

    @classmethod
    def is_voucher_freeship_query(cls, text: str) -> bool:
        """Khách hỏi về voucher, mã giảm giá, mã freeship."""
        t_low = text.lower().strip()
        return any(kw in t_low for kw in cls.VOUCHER_FREESHIP_KEYWORDS)

    @classmethod
    def detect_policy_intent(cls, text: str) -> str | None:
        """Phát hiện chính xác Intent chính sách TikTok Shop.
        
        Trả về:
        - 'COLOR_REAL_ITEM': Hỏi màu sắc combo / hàng thật trên live
        - 'SHIPPING': Hỏi thời gian giao hàng / ship
        - 'CO_INSPECTION': Hỏi chính sách đồng kiểm mở hộp
        - 'RETURN_WARRANTY': Hỏi bảo hành & đổi trả 6 ngày
        - 'VOUCHER_FREESHIP': Hỏi voucher & mã freeship
        - None: Không thuộc câu hỏi chính sách nền tảng
        """
        # Thứ tự ưu tiên kiểm tra chặt chẽ
        if cls.is_color_or_real_item_query(text):
            return "COLOR_REAL_ITEM"
        if cls.is_co_inspection_query(text):
            return "CO_INSPECTION"
        if cls.is_shipping_query(text):
            return "SHIPPING"
        if cls.is_return_warranty_query(text):
            return "RETURN_WARRANTY"
        if cls.is_voucher_freeship_query(text):
            return "VOUCHER_FREESHIP"
        return None

    @classmethod
    def generate_policy_response(
        cls,
        intent: str,
        nickname: str = "bạn",
        region_dialect: str = "south",
        use_slangs: bool = True
    ) -> str:
        """Sinh câu trả lời chuẩn xác 100% theo bách khoa tri thức TikTok Shop theo 3 miền."""
        res = ""

        # ---------------------------------------------------------------------
        # 1. Màu sắc combo trên live / Hàng thật 100%
        # ---------------------------------------------------------------------
        if intent == "COLOR_REAL_ITEM":
            if region_dialect == "north":
                res = random.choice([
                    "Hàng thật 100% y hệt trên live bác nhá! Bác được mở ra đồng kiểm tra hàng ạ!",
                    "Cam kết hàng thật như trên live bác nhá! Bác nhận hàng được đồng kiểm thoải mái ạ!"
                ])
            elif region_dialect == "central":
                res = random.choice([
                    "Hàng thật 100% y hình trên live nghe bồ! Được mở ra đồng kiểm tra hàng hỉ!",
                    "Cam kết chuẩn như trên live bồ nghe! Bồ được mở hộp đồng kiểm thoải mái hỉ!"
                ])
            else:  # South
                res = random.choice([
                    "Hàng thật 100% y chang trên live nha bồ! Cho mở hộp đồng kiểm tra thoải mái nè!",
                    "Cam kết hàng thật như trên live nha! Bồ được mở hàng đồng kiểm tra đúng mẫu mới nhận nè!"
                ])

        # ---------------------------------------------------------------------
        # 2. Thời gian giao hàng / Ship TikTok Shop (2-3 ngày, J&T/GHN/SPX)
        # ---------------------------------------------------------------------
        elif intent == "SHIPPING":
            if region_dialect == "north":
                res = random.choice([
                    "Giao 2-3 ngày qua J&T/GHN/SPX, bác nhớ để ý điện thoại nhận hàng nhá!",
                    "Ship nhanh 2-3 ngày qua J&T/GHN/SPX, bác giữ máy nhận hàng giúp em nha!"
                ])
            elif region_dialect == "central":
                res = random.choice([
                    "Giao 2-3 ngày qua J&T/GHN/SPX, bồ nhớ để ý điện thoại nhận hàng nghe!",
                    "Ship 2-3 ngày qua J&T/GHN/SPX tới nơi, bồ nhớ giữ máy nhận hàng hỉ!"
                ])
            else:  # South
                res = random.choice([
                    "Giao 2-3 ngày qua J&T/GHN/SPX, bồ nhớ để ý điện thoại nhận hàng nha!",
                    "Giao nhanh 2-3 ngày qua J&T/GHN/SPX, bồ giữ máy nhận hàng giúp em nè!"
                ])

        # ---------------------------------------------------------------------
        # 3. Chính sách đồng kiểm (Cho mở ra xem 100%)
        # ---------------------------------------------------------------------
        elif intent == "CO_INSPECTION":
            if region_dialect == "north":
                res = random.choice([
                    "TikTok Shop cho đồng kiểm 100% bác nhá! Bác cứ mở hộp kiểm tra ưng mới nhận!",
                    "Bác được mở ra xem đồng kiểm 100% nhá! Đúng chuẩn ưng ý mới thanh toán ạ!"
                ])
            elif region_dialect == "central":
                res = random.choice([
                    "TikTok Shop cho đồng kiểm 100% bồ nghe! Khui ra xem ưng bụng mới nhận hỉ!",
                    "Bồ được mở ra xem đồng kiểm 100% nghe! Hàng đẹp ưng ý mới trả tiền hỉ!"
                ])
            else:  # South
                res = random.choice([
                    "TikTok Shop cho đồng kiểm 100% nha bồ! Mở hộp kiểm tra ưng mới thanh toán nè!",
                    "Bồ được mở ra xem đồng kiểm 100% nha! Hàng chuẩn đẹp mới nhận nè!"
                ])

        # ---------------------------------------------------------------------
        # 4. Bảo hành & Đổi trả (Đổi trả miễn phí trong 6 ngày)
        # ---------------------------------------------------------------------
        elif intent == "RETURN_WARRANTY":
            if region_dialect == "north":
                res = random.choice([
                    "Lỗi đổi trả miễn phí trong 6 ngày chuẩn TikTok Shop, bác yên tâm nhá!",
                    "Bảo hành uy tín, hỗ trợ đổi trả miễn phí 6 ngày theo TikTok Shop bác nhá!"
                ])
            elif region_dialect == "central":
                res = random.choice([
                    "Lỗi đổi trả miễn phí 6 ngày chuẩn TikTok Shop, bồ yên tâm nghe!",
                    "Bảo hành chính hãng, đổi trả miễn phí trong 6 ngày chuẩn TikTok Shop hỉ!"
                ])
            else:  # South
                res = random.choice([
                    "Lỗi đổi trả miễn phí trong 6 ngày chuẩn TikTok Shop, bồ an tâm nha!",
                    "Hàng chính hãng, đổi trả miễn phí trong 6 ngày theo TikTok Shop nha bồ!"
                ])

        # ---------------------------------------------------------------------
        # 5. Voucher & Freeship Extra góc trái màn hình
        # ---------------------------------------------------------------------
        elif intent == "VOUCHER_FREESHIP":
            if region_dialect == "north":
                res = random.choice([
                    "Bác bấm giỏ hàng góc trái lưu mã Freeship Extra với voucher 30k-50k nhá!",
                    "Dạ giỏ hàng góc trái có mã Freeship Extra với voucher 30k-50k, bác lưu lẹ nha!"
                ])
            elif region_dialect == "central":
                res = random.choice([
                    "Bồ bấm vô giỏ hàng góc trái lưu mã Freeship Extra với voucher 30k-50k nghe!",
                    "Giỏ hàng góc trái có mã Freeship Extra kèm voucher 30k-50k, lưu liền bồ hỉ!"
                ])
            else:  # South
                res = random.choice([
                    "Bồ bấm giỏ hàng góc trái lưu mã Freeship Extra với voucher 30k-50k nha!",
                    "Vô giỏ hàng góc trái lụm mã Freeship Extra kèm voucher 30k-50k liền nha ní!"
                ])

        if use_slangs and res:
            from dta_autolive.infrastructure.dta_qwen_engine import apply_human_slangs_and_typos
            res = apply_human_slangs_and_typos(res, region_dialect)

        return res

    @classmethod
    def get_knowledge_summary_for_ai_prompt(cls) -> str:
        """Đoạn chỉ dẫn tri thức TikTok Shop cốt lõi để nạp trực tiếp vào System Prompt của các mô hình LLM."""
        return (
            "=== BỘ NÃO AI SALES THỰC CHIẾN & BÁCH KHOA TOÀN THƯ TIKTOK SHOP ===\n"
            "Khi trả lời bình luận khán giả, TUYỆT ĐỐI tuân thủ 5 nguyên tắc chuẩn mực sau:\n"
            "1. KHÁCH HỎI MÀU SẮC COMBO / HÌNH THẬT TRÊN LIVE: Cam kết hàng thật hình thật 100%, y chang trên live, "
            "khách được đồng kiểm tra hàng trước khi nhận, KHÔNG ĐƯỢC tự ý nhảy sang ghim sản phẩm khác.\n"
            "2. KHÁCH HỎI THỜI GIAN GIAO HÀNG / SHIP: Trả lời chuẩn thời gian vận chuyển TikTok Shop là 2-3 ngày toàn quốc "
            "qua các đơn vị vận chuyển J&T Express, GHN, SPX; dặn dò khách để ý giữ điện thoại để shipper giao hàng.\n"
            "3. KHÁCH HỎI CHÍNH SÁCH ĐỒNG KIỂM / XEM HÀNG: Xác nhận rõ ràng TikTok Shop CHO PHÉP ĐỒNG KIỂM 100%, "
            "mở hộp kiểm tra hàng đúng mẫu đúng màu mới thanh toán.\n"
            "4. KHÁCH HỎI BẢO HÀNH & ĐỔI TRẢ: Hướng dẫn đổi trả MIỄN PHÍ TRONG 6 NGÀY theo chuẩn chính sách TikTok Shop nếu có lỗi, "
            "thao tác trên app có shipper thu hồi tận nhà.\n"
            "5. KHÁCH HỎI VOUCHER / FREESHIP: Hướng dẫn khách bấm vào giỏ hàng góc trái màn hình để lưu mã Freeship Extra "
            "và voucher giảm 30k-50k áp dụng khi chốt đơn.\n"
        )
