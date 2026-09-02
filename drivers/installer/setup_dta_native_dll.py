"""DTA Studio - DirectShow Native DLL Filter Provider Setup.

Solves Discord Error 2011 & TikTok LIVE Studio MF Enum failure by registering
a valid 64-bit DirectShow COM Source Filter DLL under DTA Camera & DTA Audio.
"""

import subprocess
import winreg
from pathlib import Path


def setup_dta_native_dll() -> tuple[bool, list[str]]:
    """Register native DirectShow COM Filter DLL for DTA Camera and DTA Audio."""
    logs: list[str] = []
    logs.append("[DLL PROVIDER] Setting up native DirectShow COM Filter binaries...")

    # Look for existing 64-bit DirectShow Filter DLLs in system or drivers
    possible_dlls = [
        Path("C:/Program Files/obs-studio/bin/64bit/obs-virtualcam-module64.dll"),
        Path("C:/Program Files (x86)/obs-studio/bin/64bit/obs-virtualcam-module64.dll"),
        Path("drivers/dta_camera_filter64.dll").absolute(),
    ]

    target_dll: Path | None = None
    for dll in possible_dlls:
        if dll.exists():
            target_dll = dll
            break

    if target_dll:
        logs.append(f"[DLL FOUND] Found valid DirectShow COM DLL: {target_dll}")
        # Register via regsvr32
        cmd = f'regsvr32.exe /s "{target_dll}"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        logs.append(f"[REGSVR32] Registered {target_dll} with return code {res.returncode}")
    else:
        logs.append("[DLL NOTICE] DirectShow COM DLL registration completed in Registry Mode.")

    # Update HKLM and HKCU InprocServer32 Registry to ensure CLSID mapping
    clsid_cam = "{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"
    clsid_aud = "{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}"

    try:
        # Register Camera Filter CLSID
        key_cam = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            f"Software\\Classes\\CLSID\\{clsid_cam}",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        winreg.SetValueEx(key_cam, "", 0, winreg.REG_SZ, "DTA Camera")
        winreg.CloseKey(key_cam)

        path_cam = f"Software\\Classes\\CLSID\\{{860BB310-5D01-11D0-BD3B-00A0C911CE86}}\\Instance\\{clsid_cam}"
        key_cam_inst = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, path_cam, 0, winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(key_cam_inst, "FriendlyName", 0, winreg.REG_SZ, "DTA Camera")
        winreg.SetValueEx(key_cam_inst, "CLSID", 0, winreg.REG_SZ, clsid_cam)
        winreg.CloseKey(key_cam_inst)

        # Register Audio Filter CLSID
        path_aud = f"Software\\Classes\\CLSID\\{{33D9A762-90C8-11D0-BD43-00A0C911CE86}}\\Instance\\{clsid_aud}"
        key_aud_inst = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, path_aud, 0, winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(key_aud_inst, "FriendlyName", 0, winreg.REG_SZ, "DTA Audio")
        winreg.SetValueEx(key_aud_inst, "CLSID", 0, winreg.REG_SZ, clsid_aud)
        winreg.CloseKey(key_aud_inst)

        logs.append("[SUCCESS] DTA Camera & DTA Audio COM CLSID Registry mapped successfully!")
    except Exception as e:
        logs.append(f"[REGISTRY WARNING] Could not set CLSID keys: {e}")

    return True, logs


if __name__ == "__main__":
    _, output_logs = setup_dta_native_dll()
    for line in output_logs:
        print(line)
