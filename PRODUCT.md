# Product Context – DTA AutoLive

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

- **Frontend:** Electron Desktop App, HTML5, Modern CSS3 (CSS Custom Properties, Glassmorphism, Dual-Theme Light/Dark), Vanilla JavaScript ES2024.
- **Backend:** Standalone Python 3.11 Daemon Service (PyInstaller bundled executable), PySide6, DirectShow Virtual Camera & Audio Drivers, WebSocket IPC (ws://127.0.0.1:8765), OpenCV, NumPy, FFmpeg GPU Acceleration.
- **AI Core:** Qwen 2.5 7B Instruct GGUF (Local GPU Inference qua llama.cpp / CUDA Engine), SadCaptcha Cloud API Solver.

## Users

- **Chủ kênh & Live Streamer:** Các nhà sáng tạo nội dung, KOC/KOL phát sóng trực tiếp trên TikTok LIVE Studio.
- **Chủ Shop & Đội ngũ E-commerce:** Các doanh nghiệp bán hàng online, shop thời trang, mỹ phẩm, đồ gia dụng vận hành mô hình Live Stream bán hàng tự động 24/7.
- **Kỹ thuật viên Vận hành Studio:** Người trực tiếp quản trị luồng phát, cấu hình kịch bản seeding vệ tinh, ghim sản phẩm giỏ hàng theo kịch bản và nạp VRAM GPU cho máy chủ AI.

## Product Purpose

**DTA AutoLive** là Trung tâm Điều khiển Phát sóng Live Stream Chuyên nghiệp Toàn diện (All-in-One Live Automation Studio) dành riêng cho TikTok LIVE Studio. Ứng dụng giải quyết triệt để bài toán tự động hóa phòng Live:
1. Phát lại video/playlist bản quyền mượt mà 60 FPS qua driver ảo độc quyền (DTA Camera / DTA Audio).
2. Tự động quét giỏ hàng TikTok Shop qua cổng CDP 9222 và ghim sản phẩm thông minh theo timeline.
3. Seeding vệ tinh AI tương tác thời gian thực với văn phong tự nhiên 3 miền Bắc – Trung – Nam.
4. Host Chatbot AI trả lời bình luận của khán giả siêu tốc bằng mô hình Local GPU Qwen 2.5 7B không tốn chi phí API.
5. Giải Captcha TikTok tự động qua SadCaptcha API đảm bảo luồng Live không bị gián đoạn.

## Positioning

Khác biệt hoàn toàn so với các công cụ phát video đơn thuần (như OBS phát lặp video):
- **Trí tuệ nhân tạo Local 100%:** Mô hình ngôn ngữ lớn Qwen 2.5 chạy trực tiếp trên GPU máy chủ người dùng, bảo mật tuyệt đối dữ liệu khách hàng, phản hồi dưới 300ms và không tốn phí thuê token API hàng tháng.
- **Văn phong GenZ & Đa vùng miền:** Hệ thống seeding và Host Chatbot phản hồi cực kỳ tự nhiên, hỗ trợ chọn giọng điệu 3 miền Bắc – Trung – Nam với từ ngữ đời thường, gãy gọn, kích thích chốt đơn mạnh mẽ.
- **Hệ sinh thái đồng bộ:** Một cửa sổ duy nhất quản lý từ Driver DirectShow, Giỏ hàng, Seeding, Chatbot đến Quản lý GPU VRAM.

## Operating Context

- Môi trường chạy chính: Hệ điều hành Windows 10/11 64-bit trên PC/Laptop có card đồ họa NVIDIA GeForce GTX/RTX hoặc CPU đa nhân.
- Phần mềm đồng hành: TikTok LIVE Studio, trình duyệt Google Chrome (bật remote debugging port 9222), driver ảo DTA DirectShow.
- Không gian làm việc: Studio phát sóng ban ngày lẫn đêm khuya với chế độ Dark Mode bảo vệ thị lực và Light Mode cho văn phòng sáng.

## Capabilities and Constraints

### 5 Module Tính Năng Cốt Lõi:
1. **Studio Phát Live (Tab 1):**
   - Quản lý Playlist video không giới hạn, hỗ trợ trộn ngẫu nhiên, lặp vô tận, tiếp sóng video live stream.
   - Bảng điều khiển hiệu ứng thời gian thực (Brightness, Contrast, Saturation, Hue, Zoom, Sharpen, Lật gương, Khử nhiễu).
   - Bộ ghi hình trực tiếp (Live Stream Recorder) lưu file MP4 chất lượng cao kèm 1-click đưa vào Playlist.
2. **Giỏ Hàng & Ghim Sản Phẩm (Tab 2):**
   - Quét dữ liệu sản phẩm thực từ TikTok Shop qua CDP 9222 (Tên, Giá, Ảnh, Lượt bán, Link).
   - Tự động ghim sản phẩm theo khoảng thời gian tùy chỉnh kèm thuyết minh AI.
3. **Seeding Vệ Tinh AI (Tab 3):**
   - Tự động tạo kịch bản hỏi đáp mồi chốt đơn theo 3 miền (Bắc, Trung, Nam).
   - Điều chỉnh tốc độ seeding, tần suất và kịch bản GenZ tự nhiên.
4. **Host Live Chatbot (Tab 4):**
   - Lắng nghe comment luồng live và phản hồi tự động theo kịch bản bán hàng.
   - Tự động nhận diện câu hỏi về sản phẩm trong giỏ hàng để tư vấn chi tiết thông số và khuyến mãi.
5. **AI Qwen & Cài Đặt Hệ Thống (Tab 5):**
   - Quản lý tải và nạp model Qwen 2.5 7B GGUF vào GPU VRAM (n_gpu_layers=-1).
   - Đo Benchmark độ trễ AI (ms), đo nhiệt độ và dung lượng VRAM thực tế.
   - Cấu hình SadCaptcha API Key giải mã xác thực TikTok.

## Brand Commitments

- **Tên Thương Hiệu:** DTA Studio – DTA AutoLive
- **Chủ sở hữu:** Đức Trường AI
- **Hotline / Zalo:** 0962.775.506
- **Email:** ductruong.onl@gmail.com
- **Website Chính Thức:** https://dta-studio.vercel.app/
- **Facebook:** https://www.facebook.com/phamductruong17/
- **GitHub:** https://github.com/TruongAnh2706

## Evidence on Hand

- Hệ thống mã nguồn Desktop App hoàn chỉnh trong thư mục electron/ và src/dta_autolive/.
- Bộ 50/50 Unit Test tự động hóa đạt chuẩn chất lượng Quality Gate 100% Pass.
- Pipeline CI/CD tự động đóng gói bộ cài Windows NSIS Setup .exe và Portable .exe trên GitHub Actions.

## Product Principles

1. **Zero-Dependency Execution:** Người dùng tải file .exe cài đặt trên bất kỳ máy tính Windows nào cũng chạy được ngay lập tức 100%, không đòi hỏi cài thêm Python hay cấu hình phức tạp.
2. **Siêu Mượt & Ổn Định Tuyệt Đối:** Luồng phát video và tiến trình AI chạy nền độc lập không bao giờ làm đơ giao diện chính.
3. **Tự Nhiên & Chân Thật:** Từng câu chữ do AI tạo ra phải gần gũi, đúng ngữ điệu người Việt, xóa bỏ cảm giác máy móc rập khuôn.
4. **Trải Nghiệm Đỉnh Cao (GenZ High-Tech):** Giao diện Dark Mode kết hợp Neon Glow hiện đại, dễ thao tác trong phòng Live tối.
