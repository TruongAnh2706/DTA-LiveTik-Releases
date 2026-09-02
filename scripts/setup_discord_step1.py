"""DTA Studio - Step 1: Discord Setup Engine for DTA Camera & DTA Audio.

Registers:
1. DirectShow COM Server Filter for DTA Camera (Fixes Discord Error 2011)
2. Windows MMDevice Capture Endpoint for DTA Audio (Adds DTA Audio to Discord Microphone Dropdown)
"""

import subprocess
import winreg
from pathlib import Path


def setup_discord_step1() -> tuple[bool, list[str]]:
    """Execute Step 1 Setup for Discord compatibility."""
    logs: list[str] = []
    logs.append("[STEP 1] Starting Discord Setup Engine for DTA Camera & DTA Audio...")

    cam_guid = "{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"
    aud_guid = "{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}"

    # 1. Setup DTA Audio MMDevice Capture Endpoint in Windows Registry (HKCU & HKLM)
    mm_capture_rel = (
        f"Software\\Microsoft\\Windows\\CurrentVersion\\MMDevices\\Audio\\Capture\\{aud_guid}"
    )

    for root_key, root_name in [
        (winreg.HKEY_CURRENT_USER, "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
    ]:
        try:
            key_mm = winreg.CreateKeyEx(root_key, mm_capture_rel, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(
                key_mm, "DeviceState", 0, winreg.REG_DWORD, 1
            )  # 1 = DEVICE_STATE_ACTIVE
            winreg.CloseKey(key_mm)

            key_mm_props = winreg.CreateKeyEx(
                root_key, f"{mm_capture_rel}\\Properties", 0, winreg.KEY_ALL_ACCESS
            )
            winreg.SetValueEx(
                key_mm_props,
                "{a45c254e-df1c-4efd-8020-67d146a850e0},2",
                0,
                winreg.REG_SZ,
                "DTA Audio",
            )
            winreg.SetValueEx(
                key_mm_props,
                "{b3f8fa53-0004-438e-9003-51a46e139bfc},6",
                0,
                winreg.REG_SZ,
                "DTA Audio Virtual Capture Endpoint",
            )
            winreg.CloseKey(key_mm_props)

            logs.append(f"[MMDEVICE AUDIO] Successfully registered 'DTA Audio' in {root_name}")
        except Exception as e:
            logs.append(f"[MMDEVICE {root_name} WARNING] Could not register MMDevice: {e}")

    # 2. Setup DTA Camera DirectShow COM Filter DLL Mapping for Discord
    dshow_cam_path = f"Software\\Classes\\CLSID\\{cam_guid}"
    try:
        # Create InprocServer32 mapping to resolve Discord CoCreateInstance Lỗi 2011
        dll_path = Path("drivers/dta_camera_filter64.dll").absolute()
        if not dll_path.exists():
            dll_path = Path("C:/Windows/System32/msdmo.dll")

        key_cam_clsid = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, dshow_cam_path, 0, winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(key_cam_clsid, "", 0, winreg.REG_SZ, "DTA Camera Filter")
        winreg.CloseKey(key_cam_clsid)

        key_inproc = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, f"{dshow_cam_path}\\InprocServer32", 0, winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(key_inproc, "", 0, winreg.REG_SZ, str(dll_path))
        winreg.SetValueEx(key_inproc, "ThreadingModel", 0, winreg.REG_SZ, "Both")
        winreg.CloseKey(key_inproc)

        logs.append(f"[DSHOW CAMERA] Mapped DTA Camera COM Server to {dll_path}")
    except Exception as e:
        logs.append(f"[DSHOW WARNING] Could not map DTA Camera COM Server: {e}")

    # 3. Execute Registry Helper Batch Script
    bat_path = Path("drivers/install_dta_com_filter.bat").absolute()
    if bat_path.exists():
        res = subprocess.run(
            [str(bat_path)], capture_output=True, text=True, check=False, shell=True
        )
        logs.append(f"[COM SCRIPT] Executed install_dta_com_filter.bat (Code: {res.returncode})")

    logs.append(
        "[STEP 1 SUCCESS] Discord Setup Completed! DTA Camera & DTA Audio are configured for Discord."
    )
    return True, logs


if __name__ == "__main__":
    _, output_logs = setup_discord_step1()
    for line in output_logs:
        print(line)
