# ARCHITECTURE SPECIFICATION: AUTOMATIC FORCE UPDATE SYSTEM (OTA)
**Project / Module:** Desktop Application Auto-Update Framework  
**Author/Brand:** DTA Studio Architecture Standard  
**Document Version:** 1.0.0  
**Target Runtimes:** Electron (Node.js) / CustomTkinter / PyQt6  

---

## 1. TỔNG QUAN HỆ THỐNG (OVERVIEW)

Hệ thống cập nhật tự động (Force Update / Continuous OTA Deployment) được thiết kế nhằm mục đích **bảo mật mã nguồn tuyệt đối**, tự động hóa quy trình phân phối (CI/CD) và đảm bảo **100% người dùng cuối luôn vận hành phiên bản mới nhất** trước khi truy cập vào giao diện làm việc chính.

```
+-------------------------------------------------------------------------------+
|                                PRIVATE REPO                                   |
|   - Source Code                                                               |
|   - Build Pipelines & Secrets (DTA-Release-Token)                             |
|   - Git Tag Trigger (e.g. v1.0.5)                                             |
+---------------------------------------+---------------------------------------+
                                        |
                                        | GitHub Actions CI/CD (Build & Bundle)
                                        v
+-------------------------------------------------------------------------------+
|                                 PUBLIC REPO                                   |
|   - Release Binaries (.exe, .dmg, installer)                                  |
|   - Update Metadata (latest.yml)                                              |
+---------------------------------------+---------------------------------------+
                                        |
                                        | Fetch Version Check
                                        v
+-------------------------------------------------------------------------------+
|                              CLIENT APP LAUNCH                                |
|   1. App Start -> Show Splash Screen (Interception)                           |
|   2. Check Version vs Public Repo metadata                                    |
|   3. If New Version Available -> Force Download & Auto-Install                |
|   4. If Up-To-Date -> Dismiss Splash Screen & Load Main Dashboard             |
+-------------------------------------------------------------------------------+
```

---

## 2. KIẾN TRÚC REPOSITORY (DUAL-REPO PATTERN)

Để bảo vệ tài sản trí tuệ và ngăn chặn việc lộ source code, ứng dụng tách biệt hoàn toàn môi trường phát triển và môi trường phân phối:

1. **Private Repository (`dta-app-source`):**
   - Chứa toàn bộ mã nguồn ứng dụng, logic nghiệp vụ và file cấu hình.
   - Chứa file cấu hình GitHub Actions Workflow.
   - Được bảo vệ bằng Personal Access Token (PAT) có quyền ghi tới Public Repo (`DTA-Release-Token`).
2. **Public Repository (`dta-app-releases`):**
   - Chỉ lưu trữ các bản phát hành (Releases).
   - Chứa tệp `latest.yml` (chứa checksum, version, release notes) và tệp thực thi cài đặt (`.exe`, `.dmg`).
   - Công khai hoàn toàn để client endpoint kết nối đọc dữ liệu mà không cần xác thực API Key.

---

## 3. LỒNG MÀN HÌNH CHỜ & ÉP BUỘC CẬP NHẬT (SPLASH SCREEN INTERCEPTION)

Màn hình chờ (Splash Screen) đóng vai trò là **Gatekeeper (Người gác cổng)**, chặn toàn bộ tương tác giao diện cho đến khi xác thực phiên bản hoàn tất.

### Quy trình khởi chạy Client (Client Lifecycle):
1. **Lần khởi chạy thứ nhất (Initialization):**
   - Khởi tạo màn hình Splash Screen (Frameless Window, luôn nằm trên cùng `alwaysOnTop`).
   - Giao diện Dashboard chính được ẩn hoàn toàn (`show: false`).
2. **Xác thực phiên bản (Version Check):**
   - Splash Screen hiển thị tiến trình: *"Đang kiểm tra cập nhật..."*
   - Gọi API lấy thông tin `latest.yml` từ Public Repository.
3. **Phân nhánh xử lý (Branching Logic):**
   - **Trường hợp 1: Có phiên bản mới (`Has Update`)**
     - Vô hiệu hóa nút đóng ứng dụng hoặc ẩn nút bỏ qua.
     - Hiển thị thanh tiến trình tải (`ProgressBar`).
     - Cập nhật trạng thái realtime: *"Đang tải bản cập nhật vX.Y.Z (45%)..."*
     - Sau khi tải xong: Thực thi giải nén/cài đặt đè và tự động khởi động lại (Restart).
   - **Trường hợp 2: Đã là phiên bản mới nhất (`Up to Date`)**
     - Đổi trạng thái: *"Hệ thống đã sẵn sàng!"*
     - Đóng Splash Screen và kích hoạt `show()` cho Main Dashboard.
   - **Trường hợp 3: Mất kết nối / Lỗi mạng (`Network Error`)**
     - Tùy chọn cấu hình Strict Mode: Hiển thị thông báo *"Yêu cầu kết nối Internet để khởi động ứng dụng"* -> Nút "Thử lại" hoặc Thoát.

---

## 4. CODE MẪU BẢN CHUẨN (IMPLEMENTATION EXAMPLES)

### 4.1. Implementation trong Electron (Node.js)

#### `main.js` (Main Process)
```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');

let splashWindow;
let mainWindow;

// Cấu hình Updater trỏ tới Public Repo
autoUpdater.autoDownload = false;
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'YOUR_GITHUB_USERNAME',
  repo: 'dta-app-releases',
  private: false
});

function createWindows() {
  // 1. Tạo Màn hình Splash Screen
  splashWindow = new BrowserWindow({
    width: 480,
    height: 320,
    frame: false,
    alwaysOnTop: true,
    transparent: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  splashWindow.loadFile('splash.html');

  // 2. Tạo Màn hình Main Dashboard (Ẩn ban đầu)
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });
  mainWindow.loadFile('index.html');

  // 3. Tiến hành kiểm tra Cập nhật
  app.on('ready', () => {
    autoUpdater.checkForUpdates();
  });
}

app.whenReady().then(createWindows);

// Auto Updater Events
autoUpdater.on('checking-for-update', () => {
  splashWindow.webContents.send('status', 'Đang kiểm tra bản cập nhật hệ thống...');
});

autoUpdater.on('update-available', (info) => {
  splashWindow.webContents.send('status', `Phát hiện phiên bản mới (${info.version}). Đang tải về...`);
  autoUpdater.downloadUpdate();
});

autoUpdater.on('update-not-available', () => {
  splashWindow.webContents.send('status', 'Hệ thống đã sẵn sàng!');
  setTimeout(() => {
    splashWindow.close();
    mainWindow.show();
  }, 1000);
});

autoUpdater.on('download-progress', (progressObj) => {
  const percent = Math.round(progressObj.percent);
  splashWindow.webContents.send('progress', percent);
  splashWindow.webContents.send('status', `Đang tải cập nhật: ${percent}%`);
});

autoUpdater.on('update-downloaded', () => {
  splashWindow.webContents.send('status', 'Tải hoàn tất. Đang tiến hành cài đặt...');
  setTimeout(() => {
    autoUpdater.quitAndInstall(true, true);
  }, 1500);
});

autoUpdater.on('error', (err) => {
  splashWindow.webContents.send('status', 'Lỗi kiểm tra cập nhật. Vui lòng thử lại!');
  console.error('Update Error:', err);
});
```

---

### 4.2. Giao diện Splash Screen (`splash.html`)

Thừa hưởng ngôn ngữ thiết kế DTA Studio Standard (Dark Mode Modern, Accent Neon Blue `#00E5FF`, Rounded Glassmorphism):

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body {
      background: #0f172a;
      color: #f8fafc;
      width: 480px;
      height: 320px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
      user-select: none;
      overflow: hidden;
    }
    .logo-container {
      margin-bottom: 24px;
      text-align: center;
    }
    .brand-title {
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 1.5px;
      background: linear-gradient(135deg, #00E5FF 0%, #7C4DFF 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand-sub {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 2px;
    }
    .status-text {
      font-size: 13px;
      color: #cbd5e1;
      margin-bottom: 16px;
      height: 18px;
      text-align: center;
    }
    .progress-bar-container {
      width: 80%;
      height: 6px;
      background: #1e293b;
      border-radius: 3px;
      overflow: hidden;
      position: relative;
    }
    .progress-bar {
      width: 0%;
      height: 100%;
      background: linear-gradient(90deg, #00E5FF, #3B82F6);
      transition: width 0.3s ease;
      border-radius: 3px;
    }
  </style>
</head>
<body>
  <div class="logo-container">
    <div class="brand-title">DTA AUTOMATION</div>
    <div class="brand-sub">Core System Booting</div>
  </div>
  
  <div class="status-text" id="status">Đang khởi tạo hệ thống...</div>
  
  <div class="progress-bar-container">
    <div class="progress-bar" id="progress"></div>
  </div>

  <script>
    const { ipcRenderer } = require('electron');
    const statusEl = document.getElementById('status');
    const progressEl = document.getElementById('progress');

    ipcRenderer.on('status', (event, text) => {
      statusEl.innerText = text;
    });

    ipcRenderer.on('progress', (event, percent) => {
      progressEl.style.width = percent + '%';
    });
  </script>
</body>
</html>
```

---

## 5. CẤU HÌNH GITHUB ACTIONS (CI/CD WORKFLOW)

Tạo file `.github/workflows/release.yml` trong **Private Repository**:

```yaml
name: Build & Deploy OTA Release

on:
  push:
    tags:
      - 'v*' # Trigger khi push tag dạng v1.0.0, v35.5.10...

jobs:
  build-and-publish:
    runs-on: windows-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install Dependencies
        run: npm ci

      - name: Build & Publish to Public Release Repo
        env:
          GH_TOKEN: ${{ secrets.DTA_RELEASE_TOKEN }} # Personal Access Token cấp quyền ghi Public Repo
        run: |
          npx electron-builder --win --publish always             --config.publish.provider=github             --config.publish.owner=YOUR_GITHUB_USERNAME             --config.publish.repo=dta-app-releases
```

---

## 6. QUY TRÌNH PHÁT HÀNH BẢN MỚI (RELEASE WORKFLOW)

Khi cần phát hành phiên bản ứng dụng mới, thực hiện các bước sau trên máy Lập trình viên:

```bash
# 1. Cập nhật version trong package.json
npm version 1.0.1 --no-git-tag-version

# 2. Commit thay đổi
git add .
git commit -m "release: update application to v1.0.1"

# 3. Tạo Tag & Push lên Private Repo
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

**Tự động hóa hoàn tất:** GitHub Actions sẽ tự chạy, đóng gói bản build và đẩy installer kèm file `latest.yml` sang Public Repo. Lần tiếp theo người dùng mở app, Màn hình Splash Screen sẽ tự động kích hoạt tiến trình tải đè bản mới.
