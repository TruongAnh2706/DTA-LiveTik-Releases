"""DTA Studio - Create Portable Zip Archive from dist/win-unpacked.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

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
OUTPUT_ZIP = DIST_DIR / "DTA_AutoLive_v2.3.0_Portable.zip"


def create_portable_zip() -> bool:
    if not SOURCE_DIR.exists():
        print(f"❌ Thư mục {SOURCE_DIR} không tồn tại. Vui lòng build trước.")
        return False

    print(f"📦 [DTA Studio] Đang nén toàn bộ ứng dụng sang file ZIP: {OUTPUT_ZIP.name}...")
    try:
        with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(SOURCE_DIR):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        arcname = file_path.relative_to(SOURCE_DIR)
                        zipf.write(file_path, arcname)
                    except Exception as e:
                        print(f"⚠️ Bỏ qua file {file}: {e}")
        print(f"✅ [DTA Studio] Đã tạo thành công file ZIP Portable tại: {OUTPUT_ZIP}")
        print(f"📊 Dung lượng file ZIP: {OUTPUT_ZIP.stat().st_size / (1024*1024):.2f} MB")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi nén file ZIP: {e}")
        return False


if __name__ == "__main__":
    success = create_portable_zip()
    sys.exit(0 if success else 1)
