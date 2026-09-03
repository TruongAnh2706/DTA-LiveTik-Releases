# 🚀 DTA AutoLive PRO v2.4.0 - Hệ Thống Tự Động Hóa Livestream Bán Hàng Thông Minh

[![Version](https://img.shields.io/badge/Version-2.4.0-neonblue)](https://github.com/TruongAnh2706/DTA-LiveTik-Releases)
[![DTA Studio](https://img.shields.io/badge/Developed_by-DTA_Studio-brightgreen)](https://dta-studio.vercel.app/)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#)

> **Phát triển bởi DTA Studio - Chủ quản: Đức Trường AI**  
> - 📞 **Hotline / Zalo:** 0962.775.506  
> - 📧 **Email:** ductruong.onl@gmail.com  
> - 🌐 **Website:** [https://dta-studio.vercel.app/](https://dta-studio.vercel.app/)  
> - 👤 **Facebook:** [phamductruong17](https://www.facebook.com/phamductruong17/)  
> - 🐙 **GitHub:** [TruongAnh2706](https://github.com/TruongAnh2706)

---

## 📌 GIỚI THIỆU TỔNG QUAN

**DTA AutoLive PRO** là giải pháp phần mềm desktop thế hệ mới chuyên biệt cho nhà bán hàng, KOC và nhà sáng tạo nội dung trên nền tảng **TikTok Live & TikTok Shop**.

Ứng dụng kết hợp sức mạnh kiến trúc **Hybrid Electron Frontend** và **Python High-Performance Core**, cung cấp khả năng phát sóng video lặp mượt mà không delay sang **TikTok Live Studio** thông qua trình điều khiển ảo DirectShow độc quyền, đồng thời tự động hóa hoàn toàn quy trình ghim sản phẩm và chăm sóc khách hàng bằng AI.

---

## ✨ CÁC TÍNH NĂNG ĐỘT PHÁ TRÊN BẢN v2.4.0

### 1. 🎥 DirectShow Virtual Device Filter Gốc (Native Registry)
- Đăng ký bộ lọc ảo **DTA Camera** và **DTA Audio** trực tiếp vào hệ thống DirectShow Windows.
- Tương thích 100% với TikTok Live Studio, OBS Studio, vMix mà không cần phần mềm ảo bên thứ ba.
- Cài đặt nhanh chóng, độ trễ tiệm cận 0ms, không chiếm dụng tài nguyên CPU thừa.

### 2. 🎯 Bộ Đo Tọa Độ F8 Độc Lập & Auto Click TikTok Live Studio
- Khắc phục xung đột phím tắt: Đo vị trí nút bấm giao diện chỉ bằng phím tắt **F8** chuyên biệt.
- Tự động hóa thao tác tắt live / thao tác điều khiển trực tiếp trên mặt cửa sổ TikTok Live Studio một cách chính xác tuyệt đối.

### 3. 🎲 Ghim Sản Phẩm Tự Động với Khoảng Thời Gian Ngẫu Nhiên (Randomized Interval)
- Thuật toán ghim tự động bổ sung cơ chế dao động ngẫu nhiên (Jitter Random Delay) giữa các lần ghim.
- Chống bot detection, tối ưu hóa hiển thị giỏ hàng tự nhiên như người thao tác thủ công.

### 4. 🎵 Bộ Trộn Âm Thanh Kép (Dual Audio Mixer) & Chuyển Bài Tức Thì
- Trộn mượt mà âm thanh video gốc, microphone và nhạc nền BGM độc lập.
- Nút bấm **Next bài (⏭)** hoạt động chính xác cả khi đang phát lẫn khi đang tạm dừng, loại bỏ hoàn toàn hiện tượng lệch tiếng hoặc mất âm thanh giữa các video playlist.

### 5. 🔄 Đồng Bộ Hóa Đa Luồng (Seamless Media Pipeline)
- Cơ chế giám sát đồng bộ khung hình và buffer âm thanh giữa ứng dụng và TikTok Live Studio, chấm dứt triệt để tình trạng video chạy trước âm thanh hoặc mất tiếng khi chuyển video.

### 6. 🛡️ Hệ Thống Cập Nhật OTA Tự Động (Auto-Updater)
- Tích hợp kiểm tra phiên bản từ GitHub Releases.
- Người dùng chỉ cần nhấp cài đặt một lần, hệ thống sẽ tự động thông báo và nâng cấp phiên bản mới nhất.

---

## 🏗️ KIẾN TRÚC MÃ NGUỒN

`
dta-autolive/
├── assets/                    # Biểu tượng, hình ảnh, thương hiệu DTA Studio
├── drivers/                   # Bộ lọc thiết bị ảo DirectShow (Camera & Audio INF/DLL)
├── electron/                  # Giao diện Electron High-Tech Dark Mode & Inter-Process Communication
│   ├── renderer/              # Giao diện điều khiển (HTML5, CSS Neon, Vanilla JS)
│   ├── main.js                # Tiến trình chính Electron & Quản lý Window
│   └── ota_updater.js         # Động cơ tự động cập nhật OTA qua GitHub Releases
├── installer/                 # Kịch bản đóng gói Inno Setup chuyên nghiệp
├── src/                       # Lõi xử lý nghiệp vụ Python (Clean Architecture)
│   └── dta_autolive/
│       ├── application/       # Sắp xếp timeline và điều phối sự kiện
│       ├── domain/            # Máy trạng thái hữu hạn (FSM) và mô hình dữ liệu
│       ├── infrastructure/    # SoftCam, BGM Player, Audio Mixer, Chrome Bridge, AI Engines
│       └── launcher/          # Máy chủ Backend API Service
├── tests/                     # Hệ thống kiểm thử toàn diện (101 Unit & Integration Tests)
├── build_backend.py           # Kịch bản đóng gói nhị phân Python an toàn (PyInstaller Onedir)
└── package.json               # Cấu hình dự án Electron & Electron-Builder
`

---

## 💻 HƯỚNG DẪN CÀI ĐẶT & CHẠY MÔI TRƯỜNG PHÁT TRIỂN

### Yêu cầu hệ thống:
- Hệ điều hành: **Windows 10 / 11 64-bit**
- Node.js: **v18+**
- Python: **3.11 64-bit**

### Khởi chạy môi trường phát triển:
`ash
# 1. Cài đặt thư viện Node.js
npm install

# 2. Cài đặt các gói phụ thuộc Python
pip install -e .

# 3. Chạy toàn bộ kiểm thử
pytest tests/

# 4. Khởi động ứng dụng
npm start
`

### Đóng gói ứng dụng:
Nhấp đúp chuột vào tệp uild_all.bat để tự động biên dịch toàn bộ Backend và tạo gói cài đặt Windows.

---

## 📄 BẢN QUYỀN & PHÁP LÝ

Mã nguồn và bản quyền thuộc về **DTA Studio - Đức Trường AI**.  
Nghiêm cấm sao chép, phân phối lại trái phép dưới mọi hình thức khi chưa có sự đồng ý bằng văn bản của chủ sở hữu.
