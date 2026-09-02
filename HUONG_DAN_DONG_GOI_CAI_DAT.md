# 📦 HƯỚNG DẪN ĐÓNG GÓI & CÀI ĐẶT ỨNG DỤNG DTA AUTOLIVE (CHUYÊN NGHIỆP)

**Phát triển bởi:** DTA Studio - Chủ quản: **Đức Trường AI**  
**Hotline / Zalo:** 0962.775.506  
**Website:** [https://dta-studio.vercel.app/](https://dta-studio.vercel.app/)  
**Email:** ductruong.onl@gmail.com  

---

## 🎯 1. TẠI SAO PHẢI ĐÓNG GÓI ĐA THƯ MỤC THAY VÌ 1 FILE .EXE DUY NHẤT?

| Tiêu Chí | Đóng Gói 1 File .EXE (`--onefile`) | Đóng Gói Đa Thư Mục Chuyên Nghiệp (`Inno Setup` / `Onedir`) |
| :--- | :--- | :--- |
| **Tốc độ khởi động** | ❌ Chậm chạp (15 - 30 giây do phải giải nén tạm) | ⚡ Siêu tốc (Dưới 1 giây, mở là chạy ngay) |
| **Độ ổn định trên Windows** | ❌ Dễ bị xung đột Antivirus, lỗi khóa file `%TEMP%` | ✅ Ổn định 100%, chạy trực tiếp từ thư mục cài đặt |
| **Bảo toàn dữ liệu người dùng** | ❌ Khi restart máy dễ mất cấu hình lưu tạm | ✅ Tách riêng thư mục `data/` & `models/`, không bị mất khi cập nhật |
| **Bảo mật mã nguồn** | ⚠️ File `.pyc` dễ bị trích xuất từ thư mục tạm | 🔒 Mã hóa nhị phân `app.asar` và C-Extensions `.pyd`, không lộ file `.py` |
| **Tự động Cập Nhật (OTA Update)** | ❌ Phải tải lại toàn bộ file 1GB | ⚡ Cập nhật nhanh qua `electron-updater` |

---

## 🏗️ 2. CẤU TRÚC THƯ MỤC ỨNG DỤNG SAU KHI CÀI ĐẶT

```
C:\Program Files\DTA Studio\DTA AutoLive\  (hoặc %LOCALAPPDATA%\Programs\DTA AutoLive\)
│
├── 🚀 DTA AutoLive.exe              # Tệp thực thi chính của ứng dụng
├── 🗑️ unins000.exe                  # Trình gỡ cài đặt sạch sẽ chuẩn Windows
│
├── 📂 resources/                   # Tài nguyên mã nguồn lõi đã được mã hóa bảo vệ
│   ├── 🔒 app.asar                 # Mã nguồn Frontend Electron (đóng gói nhị phân an toàn)
│   │
│   ├── 🧠 backend/                 # Máy chủ Python AI Server (PyInstaller Onedir)
│   │   ├── dta_backend.exe         # Binary máy chủ backend độc lập
│   │   ├── python311.dll           # Thư viện runtime tối ưu
│   │   ├── _internal/              # Các C-Extension compiled (.pyd / .dll)
│   │   └── ...                     # Tuyệt đối KHÔNG có file .py thô
│   │
│   ├── 📷 drivers/                 # Bộ driver Virtual Camera & DirectShow Audio
│   │   ├── camera/ (dta_camera.inf, dta_camera_filter.dll)
│   │   ├── audio/ (dta_audio.inf)
│   │   └── installer/ (scripts nạp PnP & COM register)
│   │
│   └── 🎨 assets/                  # Logo, icons, branding của DTA Studio
│
├── 📂 data/                        # [TÁCH BIỆT] Dữ liệu người dùng (Cookies, Session, Cấu hình)
│   └── tiktok_cookies.json
│
├── 📂 models/                      # [TÁCH BIỆT] Nơi chứa các Model AI GGUF (Qwen 2.5, DeepSeek...)
│   └── (User nạp model GGUF vào đây, Auto-Update không làm mất model)
│
├── 📂 logs/                        # [TÁCH BIỆT] Nhật ký chẩn đoán hệ thống
│   ├── main_process.log
│   └── backend_service.log
│
└── ⚙️ config/                      # [TÁCH BIỆT] File cấu hình ứng dụng
    └── settings.json
```

---

## 🚀 3. QUY TRÌNH ĐÓNG GÓI ỨNG DỤNG (3 BƯỚC HOÀN TOÀN TỰ ĐỘNG)

### 👉 Cách 1: Chạy Tự Động 1-Click (Khuyên Dùng)
Nhấp đúp chuột vào file:
```
build_all.bat
```
Hệ thống sẽ tự động thực hiện 3 bước:
1. Biên dịch Backend Python sang Binary Onedir (`build_backend.py`).
2. Đóng gói giao diện Electron sang thư mục `dist/win-unpacked/` (`npm run pack`).
3. Biên dịch Inno Setup Script sang bộ cài đặt `dist/installer/DTA_AutoLive_Setup_v2.3.0.exe`.

---

### 👉 Cách 2: Chạy Từng Lệnh Thủ Công Qua Terminal

```powershell
# Bước 1: Biên dịch Backend Python Onedir
python build_backend.py

# Bước 2: Đóng gói Electron Unpacked
npm run pack

# Bước 3: Biên dịch bộ cài đặt Inno Setup
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\DTA_AutoLive_Setup.iss"
```

---

## 🛡️ 4. CƠ CHẾ BẢO MẬT & AUTO-UPDATE AN TOÀN

1. **Bảo vệ mã nguồn:**
   - Mã nguồn Electron HTML/JS/CSS nằm trọn vẹn trong file nhị phân `resources/app.asar`.
   - Backend Python được dịch thành machine code / bytecode `.pyd` / `.pyc`, loại bỏ 100% file `.py`.
2. **Cập nhật tự động (OTA Update):**
   - Khi có phiên bản mới, `electron-updater` kết nối với GitHub Releases (`TruongAnh2706/DTA-LiveTik-Releases`).
   - Quá trình tải và cài đặt bản vá chỉ cập nhật các file trong `resources/`, **giữ nguyên vẹn 100% dữ liệu tài khoản trong `data/` và Model AI nặng hàng GB trong `models/`**.

---
*Tài liệu kỹ thuật được xây dựng theo tiêu chuẩn vận hành DTA Studio - Đức Trường AI.*
