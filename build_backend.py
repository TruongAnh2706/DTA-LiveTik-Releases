"""DTA Studio - Professional Backend Bundler (PyInstaller Onedir Standard).

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build" / "backend"
BACKEND_DIST = DIST_DIR / "dta_backend"
ICON_PATH = ROOT_DIR / "assets" / "logo.ico"
ENTRYPOINT = SRC_DIR / "dta_autolive" / "launcher" / "main.py"


def clean_previous_builds() -> None:
    """Clean up old build artifacts for a fresh binary compilation."""
    print("🧹 [DTA Studio] Dọn dẹp các thư mục build cũ...")
    if BACKEND_DIST.exists():
        try:
            shutil.rmtree(BACKEND_DIST)
        except Exception as e:
            print(f"⚠️ Không thể xóa {BACKEND_DIST}: {e}")
    if BUILD_DIR.exists():
        try:
            shutil.rmtree(BUILD_DIR)
        except Exception as e:
            print(f"⚠️ Không thể xóa {BUILD_DIR}: {e}")


def build_backend_onedir() -> bool:
    """Build the backend using PyInstaller Onedir mode."""
    print("⚙️ [DTA Studio] Đang biên dịch mã nguồn Backend sang Binary Onedir...")

    hidden_imports = [
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        "pydantic",
        "pydantic_core",
        "asyncio",
        "json",
        "cv2",
        "numpy",
        "PIL",
        "ctypes",
        "ctypes.wintypes",
        "dta_autolive",
        "dta_autolive.launcher",
        "dta_autolive.launcher.backend_service",
        "dta_autolive.infrastructure.websocket_server",
        "dta_autolive.infrastructure.dta_softcam_engine",
        "dta_autolive.infrastructure.dta_audio_driver",
        "dta_autolive.infrastructure.product_pinner",
        "dta_autolive.infrastructure.host_live_chat_responder",
        "dta_autolive.infrastructure.satellite_seeding_manager",
        "dta_autolive.infrastructure.tiktok_cart_scraper",
        "dta_autolive.infrastructure.deepseek_engine",
        "dta_autolive.infrastructure.dta_qwen_engine",
        "dta_autolive.infrastructure.sadcaptcha_engine",
        "dta_autolive.infrastructure.solver",
        "dta_autolive.infrastructure.stream_recorder",
        "dta_autolive.infrastructure.dta_driver_setup",
        "dta_autolive.application.media_worker",
        "dta_autolive.application.timeline_scheduler",
        "dta_autolive.domain.models",
        "dta_autolive.domain.state_machine",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=dta_backend",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--paths={SRC_DIR}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
    ]

    if ICON_PATH.exists():
        cmd.append(f"--icon={ICON_PATH}")

    # Add hidden imports
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")

    # Exclude heavy unnecessary system packages (PyTorch ~2.2GB, Scipy, Pandas, Matplotlib)
    excludes = [
        "torch",
        "torchvision",
        "torchaudio",
        "scipy",
        "pandas",
        "sympy",
        "matplotlib",
        "tkinter",
        "IPython",
        "notebook",
        "paddle",
        "tensorrt",
        "pytest",
        "unittest",
        "tcl",
        "tk",
    ]
    for exc in excludes:
        cmd.append(f"--exclude-module={exc}")

    cmd.append(str(ENTRYPOINT))

    print(f"🚀 Chạy lệnh: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode == 0:
        print("✅ [DTA Studio] Biên dịch Backend hoàn tất thành công tại:", BACKEND_DIST)
        return True
    print("❌ [DTA Studio] Biên dịch thất bại với mã lỗi:", result.returncode)
    return False


if __name__ == "__main__":
    clean_previous_builds()
    success = build_backend_onedir()
    sys.exit(0 if success else 1)
