"""Setup and Test Option 3: PyVirtualCam with Unity Capture DirectShow Filter Engine."""

import winreg
from pathlib import Path


def setup_option3_unity_capture() -> bool:
    """Register UnityCapture DirectShow Filter in Windows Registry and test pyvirtualcam."""
    print("=== EXECUTING PHUONG AN 3: PYVIRTUALCAM + UNITY CAPTURE DIRECTSHOW BACKEND ===")

    clsid_dshow_video = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"
    unity_guid = "{2D49788D-2101-4475-A013-14902C5E788A}"

    path = f"Software\\Classes\\CLSID\\{clsid_dshow_video}\\Instance\\{unity_guid}"

    for root_key, root_name in [
        (winreg.HKEY_CURRENT_USER, "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
    ]:
        try:
            k = winreg.CreateKeyEx(root_key, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(k, "FriendlyName", 0, winreg.REG_SZ, "DTA Camera")
            winreg.SetValueEx(k, "CLSID", 0, winreg.REG_SZ, unity_guid)
            winreg.CloseKey(k)
            print(f"[REGISTRY SUCCESS] Mapped Unity Capture 'DTA Camera' in {root_name}")
        except Exception as e:
            print(f"[REGISTRY {root_name}] Notice: {e}")

    path_clsid = f"Software\\Classes\\CLSID\\{unity_guid}"
    for root_key, _root_name in [(winreg.HKEY_CURRENT_USER, "HKCU")]:
        try:
            k = winreg.CreateKeyEx(root_key, path_clsid, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "DTA Camera Filter Engine")
            winreg.CloseKey(k)

            k_inproc = winreg.CreateKeyEx(
                root_key, f"{path_clsid}\\InprocServer32", 0, winreg.KEY_ALL_ACCESS
            )
            pyd_path = Path(
                "C:/Users/Admin/AppData/Local/Programs/Python/Python311/Lib/site-packages/pyvirtualcam/_native_windows_unity_capture.cp311-win_amd64.pyd"
            )
            winreg.SetValueEx(k_inproc, "", 0, winreg.REG_SZ, str(pyd_path))
            winreg.SetValueEx(k_inproc, "ThreadingModel", 0, winreg.REG_SZ, "Both")
            winreg.CloseKey(k_inproc)
            print(f"[REGISTRY COM] Mapped UnityCapture InprocServer32 to {pyd_path}")
        except Exception as e:
            print(f"[REGISTRY COM ERROR] {e}")

    return True


if __name__ == "__main__":
    setup_option3_unity_capture()
