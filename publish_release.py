"""DTA Studio - Publish Release to GitHub Releases.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "TruongAnh2706"
REPO = "DTA-LiveTik-Releases"

# Read dynamic version from package.json
pkg_json = ROOT_DIR / "package.json"
version = "2.3.1"
if pkg_json.exists():
    try:
        with open(pkg_json, encoding="utf-8") as f:
            version = json.load(f).get("version", "2.3.1")
    except Exception:
        pass

TAG = f"v{version}"
RELEASE_TITLE = f"DTA AutoLive v{version} - Smart AI Keyword Pinning & Anti-AFK Live Protection"
RELEASE_NOTES = f"""# 🚀 DTA AutoLive v{version} - Smart AI Keyword Pinning & Anti-AFK Live Protection
**Phát triển bởi DTA Studio - Chủ quản: Đức Trường AI**
- Hotline / Zalo: 0962.775.506
- Website: https://dta-studio.vercel.app/

### 🌟 Cập nhật đột phá trong bản v{version}:
- 🧠 **AI Chatbot Thông Minh & Tự Nhiên Hơn:** AI tư vấn linh hoạt theo ngữ cảnh, tính năng, giá bán và mở rộng độ dài câu trả lời đến 180 ký tự. Không còn bị giới hạn cứng nhắc.
- 🎯 **Tự Động Nhận Diện & Ghim Sản Phẩm Theo Từ Khóa:** Khách comment tự nhiên (*"lên mã phao", "cho xem áo phao", "son môi", "tai nghe"...*) -> App tự động quét danh mục, tìm đúng sản phẩm và **Ghim ngay lên màn hình Live**!
- 🛡️ **Watchdog Auto-Heal & Chống Treo Chatbot:** Khắc phục triệt để lỗi Chatbot dừng hoạt động sau 10-15 phút live bằng luồng giám sát và tự động hồi sinh.
- 🔊 **Chống Lặp Tiếng & Triệt Tiêu Echo Live:** Nâng cấp bộ đệm âm thanh `QAudioSink` và FFmpeg Rate-Limiter, tự động giải phóng buffer khi loop/chuyển video.
- 🖱️ **Chống Dừng Live Studio Tự Động (Anti-AFK Mouse Simulator):** Tự động mô phỏng di chuyển chuột tự nhiên theo đường cong Bezier trên TikTok LIVE Studio mỗi 30s, giữ luồng live luôn hoạt động liên tục.
- 🔄 **Direct OTA Updater:** Tự động kết nối GitHub Releases tải bản cập nhật mới nhất mượt mà.
"""


def api_request(url: str, method: str = "GET", data: bytes | None = None, content_type: str = "application/json") -> dict:
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "DTA-Studio-Release-Bot",
        "Accept": "application/vnd.github.v3+json",
    }
    if content_type:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        res_data = resp.read()
        return json.loads(res_data.decode("utf-8")) if res_data else {}


def get_or_create_release() -> dict:
    print(f"🔍 Kiểm tra Release {TAG} trên repo {OWNER}/{REPO}...")
    try:
        release = api_request(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}")
        print(f"ℹ️ Đã tìm thấy Release {TAG} hiện có (ID: {release['id']}).")
        return release
    except Exception:
        print(f"✨ Tạo mới Release {TAG}...")
        payload = json.dumps({
            "tag_name": TAG,
            "target_commitish": "main",
            "name": RELEASE_TITLE,
            "body": RELEASE_NOTES,
            "draft": False,
            "prerelease": False,
        }).encode("utf-8")
        return api_request(f"https://api.github.com/repos/{OWNER}/{REPO}/releases", method="POST", data=payload)


def upload_asset(upload_url: str, file_path: Path, asset_name: str) -> None:
    if not file_path.exists():
        print(f"⚠️ Không tìm thấy file: {file_path}")
        return

    clean_url = upload_url.split("{", maxsplit=1)[0]
    encoded_name = urllib.parse.quote(asset_name)
    target_url = f"{clean_url}?name={encoded_name}"

    print(f"📤 Đang tải lên: {asset_name} ({file_path.stat().st_size / (1024*1024):.2f} MB)...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    try:
        api_request(target_url, method="POST", data=file_bytes, content_type="application/octet-stream")
        print(f"✅ Đã tải lên thành công: {asset_name}")
    except Exception as e:
        print(f"⚠️ Lỗi khi tải lên {asset_name}: {e}")


def main() -> None:
    release = get_or_create_release()
    upload_url = release.get("upload_url", "")
    if not upload_url:
        print("❌ Không lấy được upload_url từ release.")
        sys.exit(1)

    # Lấy danh sách assets hiện có để xóa đè nếu đã tồn tại
    existing_assets = release.get("assets", [])
    for ast in existing_assets:
        ast_id = ast.get("id")
        ast_name = ast.get("name")
        try:
            print(f"🗑️ Đang xóa asset cũ trên Release: {ast_name} (ID: {ast_id})...")
            api_request(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{ast_id}", method="DELETE")
        except Exception as del_err:
            print(f"⚠️ Bỏ qua xóa {ast_name}: {del_err}")

    # 1. Upload latest.yml
    latest_yml = DIST_DIR / "latest.yml"
    if latest_yml.exists():
        upload_asset(upload_url, latest_yml, "latest.yml")

    # 2. Upload Setup.exe
    setup_exe = DIST_DIR / f"DTA AutoLive Setup {version}.exe"
    if setup_exe.exists():
        upload_asset(upload_url, setup_exe, f"DTA-AutoLive-Setup-{version}.exe")
        upload_asset(upload_url, setup_exe, f"DTA AutoLive Setup {version}.exe")

    # 3. Upload Blockmap
    blockmap = DIST_DIR / f"DTA AutoLive Setup {version}.exe.blockmap"
    if blockmap.exists():
        upload_asset(upload_url, blockmap, f"DTA-AutoLive-Setup-{version}.exe.blockmap")

    # 4. Upload Portable ZIP
    portable_zip = DIST_DIR / f"DTA_AutoLive_v{version}_Portable.zip"
    if portable_zip.exists():
        upload_asset(upload_url, portable_zip, f"DTA_AutoLive_v{version}_Portable.zip")

    print(f"\n🎉 [DTA Studio] PHÁT HÀNH BẢN RELEASE {TAG} LÊN GITHUB THÀNH CÔNG RỰC RỠ!")
    print(f"🔗 Xem bản phát hành tại: https://github.com/{OWNER}/{REPO}/releases/tag/{TAG}")


if __name__ == "__main__":
    main()
