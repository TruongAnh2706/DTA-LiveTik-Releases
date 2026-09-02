"""DTA Studio - Fast & Safe Zip Packager with Auto-Release Lock.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import json
import os
import sys
import zipfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
SOURCE_DIR = DIST_DIR / "win-unpacked"

# Read dynamic version from package.json
pkg_json = ROOT_DIR / "package.json"
version = "2.3.2"
if pkg_json.exists():
    try:
        with open(pkg_json, encoding="utf-8") as f:
            version = json.load(f).get("version", "2.3.2")
    except Exception:
        pass

FINAL_ZIP = DIST_DIR / f"DTA_AutoLive_v{version}_Portable.zip"

EXCLUDE_DIRS = {
    "cachestorage",
    "code cache",
    "gpucache",
    "dawncache",
    "shadercache",
    "blob_storage",
    "service worker",
    "__pycache__",
    ".pytest_cache",
}


def pack() -> bool:
    if not SOURCE_DIR.exists():
        print(f"❌ Không tìm thấy thư mục nguồn: {SOURCE_DIR}")
        return False

    if FINAL_ZIP.exists():
        try:
            FINAL_ZIP.unlink()
            print("🧹 Đã xóa file zip cũ.")
        except Exception as e:
            print(f"⚠️ Không thể xóa file cũ: {e}")

    print(f"📦 [DTA Studio] Đang đóng gói siêu tốc thư mục win-unpacked sang file ZIP v{version}...")

    try:
        with zipfile.ZipFile(FINAL_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for root, dirs, files in os.walk(SOURCE_DIR):
                # Bỏ qua các thư mục cache rác
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS and "cache" not in d.lower()]

                for file in files:
                    if file.lower() in ("thumbs.db", "desktop.ini"):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, SOURCE_DIR)
                    try:
                        zipf.write(file_path, arcname)
                    except Exception as err:
                        print(f"⚠️ Bỏ qua file: {arcname} ({err})")

        print("✅ [DTA Studio] ĐÃ HOÀN TẤT ĐÓNG GÓI PORTABLE ZIP THÀNH CÔNG!")
        print(f"📁 Tệp ZIP đã sẵn sàng tại: {FINAL_ZIP}")
        size_mb = FINAL_ZIP.stat().st_size / (1024 * 1024)
        print(f"📊 Dung lượng: {size_mb:.2f} MB")
        return True
    except Exception as e:
        print(f"❌ Lỗi đóng gói: {e}")
        return False


if __name__ == "__main__":
    success = pack()
    sys.exit(0 if success else 1)
