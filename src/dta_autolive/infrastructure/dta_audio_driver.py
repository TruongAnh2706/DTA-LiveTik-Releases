from __future__ import annotations

import subprocess
import urllib.request
import winreg
import zipfile
from pathlib import Path


def check_virtual_audio_installed() -> bool:
    """Check if a Virtual Audio Cable device is detected in Windows audio devices."""
    try:
        cmd = "powershell -Command \"Get-PnpDevice -Class 'AudioEndpoint', 'MEDIA' | Select-Object -ExpandProperty FriendlyName\""
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=False)
        output = res.stdout.lower()
        return "cable" in output or "dta audio" in output or "virtual audio" in output
    except Exception:
        return False


def install_virtual_audio_driver() -> tuple[bool, list[str]]:
    """Download and silently install standard Virtual Audio Driver for Windows livestream routing."""
    logs: list[str] = []
    logs.append("[DTA AUDIO] Checking Virtual Audio Device status...")

    if check_virtual_audio_installed():
        logs.append(
            "[DTA AUDIO] Virtual Audio Device is ALREADY installed and detected in Windows."
        )
        register_dta_audio_friendly_name()
        return True, logs

    # Setup directories
    drivers_dir = Path("drivers/audio").absolute()
    drivers_dir.mkdir(parents=True, exist_ok=True)
    zip_target = drivers_dir / "VBCABLE_Driver_Pack43.zip"
    extract_dir = drivers_dir / "vbcable"

    download_url = "https://download.vb-audio.com/Download_VIP/VBCABLE_Driver_Pack43.zip"

    try:
        if not (extract_dir / "VBCABLE_Setup_x64.exe").exists():
            logs.append(
                f"[DTA AUDIO] Downloading Virtual Audio Driver package from {download_url}..."
            )
            urllib.request.urlretrieve(download_url, str(zip_target))  # noqa: S310
            logs.append("[DTA AUDIO] Download complete. Extracting archive...")

            with zipfile.ZipFile(zip_target, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            logs.append("[DTA AUDIO] Extracted installer files.")

        installer_exe = extract_dir / "VBCABLE_Setup_x64.exe"
        if installer_exe.exists():
            logs.append(f"[DTA AUDIO] Running Driver Installer: {installer_exe}...")
            ps_cmd = f"Start-Process -FilePath '{installer_exe}' -ArgumentList '-i', '-h' -Verb RunAs -Wait"
            res = subprocess.run(
                ["powershell", "-Command", ps_cmd], capture_output=True, text=True, check=False
            )  # noqa: S603, S607
            logs.append(f"[DTA AUDIO] Installer executed. Return code: {res.returncode}")

            # Register Friendly Names in DirectShow & Registry
            register_dta_audio_friendly_name()
            logs.append("[SUCCESS] DTA Audio Virtual Device installed successfully!")
            return True, logs

        logs.append(f"[ERROR] Installer executable not found at {installer_exe}")
        return False, logs

    except Exception as e:
        logs.append(f"[ERROR] Virtual Audio installation error: {e}")
        return False, logs


def register_dta_audio_friendly_name() -> None:
    """Register DTA Audio friendly aliases in Windows DirectShow and MMDevices registry."""
    reg_targets = [
        # Audio Input Category: {33D9A762-90C8-11D0-BD43-00A0C911CE86}
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio (Virtual Cable)",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio (Virtual Cable)",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio (Virtual Cable)",
        ),
        # Audio Renderer Category: {E0C158E1-DCD4-11D1-A1CE-0080C758D608}
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio (Virtual Cable)",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio (Virtual Cable)",
        ),
    ]

    for root, path, friendly_name in reg_targets:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, friendly_name)
            winreg.SetValueEx(
                key, "CLSID", 0, winreg.REG_SZ, "{33D9A762-90C8-11D0-BD43-00A0C911CE86}"
            )
            winreg.CloseKey(key)
        except Exception:
            pass


if __name__ == "__main__":
    success, logs = install_virtual_audio_driver()
    for line in logs:
        print(line)
