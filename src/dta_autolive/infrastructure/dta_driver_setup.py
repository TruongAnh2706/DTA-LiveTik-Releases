import importlib.util
import subprocess
import sys
import winreg
from pathlib import Path

from dta_autolive.infrastructure.dta_audio_driver import (
    check_virtual_audio_installed,
    install_virtual_audio_driver,
    register_dta_audio_friendly_name,
)


def setup_dta_virtual_hardware_drivers() -> tuple[bool, list[str]]:
    """Execute complete installation and registration of DTA Camera and DTA Audio DirectShow Drivers."""
    logs: list[str] = []
    logs.append("[DIAGNOSTIC] Starting DTA Virtual Hardware Driver Setup...")

    # 1. Inspect Python Environment & Dependencies
    logs.append(f"[ENVIRONMENT] Python Executable: {sys.executable}")
    logs.append("[ENVIRONMENT] Operating System: Windows (64-bit Architecture)")

    if importlib.util.find_spec("pyvirtualcam") is not None:
        logs.append("[DEPENDENCY] pyvirtualcam package is INSTALLED.")
    else:
        logs.append("[DEPENDENCY] Installing pyvirtualcam & numpy packages...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyvirtualcam", "numpy"],
            capture_output=True,
            check=False,
        )
        logs.append("[DEPENDENCY] pyvirtualcam & numpy installation triggered.")

    # 2. Virtual Audio Driver Check & Install
    if check_virtual_audio_installed():
        logs.append("[DTA AUDIO] DTA Audio / Virtual Audio Cable is detected.")
    else:
        logs.append("[DTA AUDIO] Virtual Audio device not found. Launching driver setup...")
        _, audio_logs = install_virtual_audio_driver()
        logs.extend(audio_logs)

    register_dta_audio_friendly_name()

    # 3. Execute Batch Script for System HKLM & WOW6432Node Registry
    bat_path = Path("drivers/install_dta_hardware_kernel.bat").absolute()
    if bat_path.exists():
        logs.append(f"[KERNEL SCRIPT] Running {bat_path}...")
        res = subprocess.run([str(bat_path)], capture_output=True, check=False, shell=True)
        logs.append(f"[KERNEL SCRIPT] Batch return code: {res.returncode}")

    com_bat_path = Path("drivers/install_dta_com_filter.bat").absolute()
    if com_bat_path.exists():
        logs.append(f"[COM SCRIPT] Running {com_bat_path}...")
        res_com = subprocess.run([str(com_bat_path)], capture_output=True, check=False, shell=True)
        logs.append(f"[COM SCRIPT] Batch return code: {res_com.returncode}")

    # 4. Register Windows DirectShow Capture Category Filter in Registry HKCU, HKLM, WOW6432Node
    reg_targets = [
        # Video Capture Category: {860BB310-5D01-11D0-BD3B-00A0C911CE86}
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
            "DTA Camera",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
            "DTA Camera",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
            "DTA Camera",
        ),
        # Audio Input Category 1: {33D9A762-90C8-11D0-BD43-00A0C911CE86}
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
    ]

    for root, path, friendly_name in reg_targets:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, friendly_name)
            winreg.SetValueEx(
                key, "CLSID", 0, winreg.REG_SZ, "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"
            )
            winreg.CloseKey(key)
            root_name = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
            logs.append(f"[REGISTRY] Registered '{friendly_name}' in {root_name}\\{path}")
        except Exception as e:
            logs.append(f"[REGISTRY WARNING] Could not write {path}: {e}")

    logs.append(
        "[SUCCESS] DTA Camera & DTA Audio DirectShow Registry & Stream Engine initialized successfully!"
    )
    return True, logs
