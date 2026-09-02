"""Build Script to package DTA AutoLive v1.1 into standalone Executable (.EXE)."""

import subprocess
import sys


def build_exe() -> None:
    """Execute PyInstaller build command for DTA AutoLive v1.1."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=DTA_AutoLive_v1.1",
        "--add-data=src/dta_autolive;dta_autolive",
        "src/dta_autolive/launcher/main.py",
    ]
    print("[DTA Build] Packaging DTA AutoLive v1.1 Standalone EXE...")
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[DTA Build] Packaging Completed Successfully. Output in dist/DTA_AutoLive_v1.1/")


if __name__ == "__main__":
    build_exe()
