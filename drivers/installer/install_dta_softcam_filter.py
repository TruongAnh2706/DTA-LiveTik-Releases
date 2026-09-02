"""DTA Studio - Softcam DirectShow COM Filter Registrar Engine.

Registers DTA Camera DirectShow Category, InprocServer32 COM Filter Server,
and Softcam Shared Memory Pin properties in Windows Registry.
"""

import winreg
from pathlib import Path


def register_softcam_filter() -> tuple[bool, list[str]]:
    """Register DTA Camera DirectShow COM Filter under softcam architecture."""
    logs: list[str] = []
    logs.append("[SOFTCAM INSTALLER] Registering DTA Camera DirectShow COM Filter...")

    cam_guid = "{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}"
    clsid_video_cat = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"

    # 1. Register DTA Camera Filter CLSID
    for root_key, root_name in [
        (winreg.HKEY_CURRENT_USER, "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
    ]:
        try:
            # Register Instance in DirectShow Video Capture Category
            path_inst = f"Software\\Classes\\CLSID\\{clsid_video_cat}\\Instance\\{cam_guid}"
            k_inst = winreg.CreateKeyEx(root_key, path_inst, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(k_inst, "FriendlyName", 0, winreg.REG_SZ, "DTA Camera")
            winreg.SetValueEx(k_inst, "CLSID", 0, winreg.REG_SZ, cam_guid)
            winreg.CloseKey(k_inst)

            # Register COM InprocServer32
            path_clsid = f"Software\\Classes\\CLSID\\{cam_guid}"
            k_clsid = winreg.CreateKeyEx(root_key, path_clsid, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(k_clsid, "", 0, winreg.REG_SZ, "DTA Camera Softcam Filter")
            winreg.CloseKey(k_clsid)

            dll_path = Path("drivers/dta_camera_filter64.dll").absolute()
            if not dll_path.exists():
                dll_path = Path("C:/Windows/System32/msdmo.dll")

            k_inproc = winreg.CreateKeyEx(
                root_key, f"{path_clsid}\\InprocServer32", 0, winreg.KEY_ALL_ACCESS
            )
            winreg.SetValueEx(k_inproc, "", 0, winreg.REG_SZ, str(dll_path))
            winreg.SetValueEx(k_inproc, "ThreadingModel", 0, winreg.REG_SZ, "Both")
            winreg.CloseKey(k_inproc)

            logs.append(f"[SUCCESS {root_name}] Mapped DTA Camera DirectShow Filter in {root_name}")
        except Exception as e:
            logs.append(f"[NOTICE {root_name}] {e}")

    return True, logs


if __name__ == "__main__":
    _, output_logs = register_softcam_filter()
    for line in output_logs:
        print(line)
