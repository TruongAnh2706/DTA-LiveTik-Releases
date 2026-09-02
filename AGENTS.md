# AGENTS.md - DTA AUTOLIVE AGENT OPERATIONAL RULES

Bạn đang làm việc trong repository **DTA AutoLive** thuộc sở hữu của **DTA Studio** (Chủ quản: **Đức Trường**).

## 🛠️ THÔNG TIN BẢN QUYỀN & LIÊN HỆ
- **Đơn vị phát triển:** DTA Studio
- **Chủ sở hữu:** Đức Trường
- **Email:** ductruong.onl@gmail.com
- **Hotline / Zalo:** 0962.775.506
- **Website:** https://dta-studio.vercel.app/

---

## 🧠 TƯ DUY VẬN HÀNH BẮT BUỘC (AGENT-FIRST)
1. **Lập Kế Hoạch Trước Khi Sửa Code:** Trước khi sửa bất kỳ mã nguồn nào, phải đối chiếu với `implementation_plan.md` và `docs/`.
2. **Quy Tắc Chặn File (Scope Boundary):** Chỉ sửa các file thuộc `ALLOWED FILES` của tác vụ tương ứng.
3. **Chất Lượng Code (Quality Gate):** Mọi thay đổi phải đi kèm Unit Test. Luôn chạy `ruff check .`, `mypy src/` và `pytest` để xác minh code pass 100%.
4. **Không Tạo Side-Effects:** 
   - Không được tắt bớt validation để test pass.
   - Không được hardcode API Token, Secret hoặc đường dẫn cá nhân.
   - Luôn sử dụng Tiếng Việt trong tài liệu hướng dẫn và log giao diện.
