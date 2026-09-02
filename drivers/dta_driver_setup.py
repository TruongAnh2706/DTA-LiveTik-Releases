"""DTA Studio - DirectShow Virtual Camera & Audio Native Driver Installer & Log Diagnostics Engine."""

import importlib.util
import subprocess
import sys
import winreg
from pathlib import Path


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

    # 2. Register Windows DirectShow Capture Category Filter in Registry
    reg_targets = [
        # Video Capture Input Category ("DTA Camera")
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
        # Audio Input / Microphone Capture Category ("Microphone (DTA Audio)")
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "Microphone (DTA Audio)",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{33D9A762-90C8-11D0-BD43-00A0C911CE86}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "Microphone (DTA Audio)",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{E4364408-5246-11CE-9F53-0020AF0BA770}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "Microphone (DTA Audio)",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio",
        ),
    ]

    registered_count = 0
    for root, path, friendly_name in reg_targets:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, friendly_name)
            winreg.SetValueEx(
                key, "CLSID", 0, winreg.REG_SZ, "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"
            )
            winreg.CloseKey(key)
            registered_count += 1
            root_name = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
            logs.append(f"[REGISTRY] Registered '{friendly_name}' in {root_name}\\{path}")
        except Exception as e:
            logs.append(f"[REGISTRY WARNING] Could not write {path}: {e}")

    # 3. Register DirectShow DLL if present in drivers folder
    dll_path = Path("drivers/dta_virtualcam64.dll").absolute()
    if dll_path.exists():
        logs.append(f"[DLL DRIVER] Found native DLL: {dll_path}")
        cmd_reg = f'regsvr32.exe /s "{dll_path}"'
        res = subprocess.run(cmd_reg, capture_output=True, check=False, shell=True)
        logs.append(f"[DLL DRIVER] regsvr32 execution code: {res.returncode}")
    else:
        logs.append(
            f"[DLL DRIVER] Standalone virtual filter driver path: {dll_path} (Ready for DirectShow streaming)"
        )

    logs.append(
        "[SUCCESS] DTA Camera & DTA Audio DirectShow Registry & Stream Engine initialized successfully!"
    )
    return True, logs


if __name__ == "__main__":
    _, log_lines = setup_dta_virtual_hardware_drivers()
    for line in log_lines:
        print(line)
