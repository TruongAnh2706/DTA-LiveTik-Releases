"""DTA Studio - DirectShow Camera Cleanup & Rename Registrar.

Removes dummy DirectShow Registry keys and updates the real working Virtual Camera
FriendlyName to 'DTA Camera' across HKCU, HKLM, and WOW6432Node.
"""

import winreg

DUMMY_KEYS = [
    "{2D49788D-2101-4475-A013-14902C5E788A}",
    "{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
]
REAL_OBS_KEY = "{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"
VIDEO_CAT = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"


def clean_and_rename(new_name: str = "DTA Camera") -> None:
    """Clean up dummy keys and update real camera FriendlyName."""
    print("================================================================")
    print(f"[DTA REGISTRAR] Cleaning dummy keys & setting device name to: '{new_name}'")
    print("================================================================")

    # 1. Delete dummy keys from HKCU and HKLM
    for dummy_guid in DUMMY_KEYS:
        # HKCU
        try:
            winreg.DeleteKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{dummy_guid}",
            )
            print(f"[CLEANUP HKCU] Deleted dummy key: {dummy_guid}")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[CLEANUP HKCU NOTICE] {e}")

        # HKLM
        try:
            winreg.DeleteKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"SOFTWARE\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{dummy_guid}",
            )
            print(f"[CLEANUP HKLM] Deleted dummy key: {dummy_guid}")
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"[CLEANUP HKLM NOTICE] Admin required to delete HKLM key: {dummy_guid}")
        except Exception as e:
            print(f"[CLEANUP HKLM NOTICE] {e}")

        # HKLM WOW6432Node
        try:
            winreg.DeleteKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"SOFTWARE\\WOW6432Node\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{dummy_guid}",
            )
            print(f"[CLEANUP HKLM WOW64] Deleted dummy key: {dummy_guid}")
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # 2. Update real OBS Virtual Camera FriendlyName in HKCU & HKLM
    real_paths = [
        (
            winreg.HKEY_CURRENT_USER,
            f"Software\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{REAL_OBS_KEY}",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{REAL_OBS_KEY}",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\WOW6432Node\\Classes\\CLSID\\{VIDEO_CAT}\\Instance\\{REAL_OBS_KEY}",
        ),
    ]

    for root, rel_path in real_paths:
        root_str = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
        try:
            key = winreg.CreateKeyEx(root, rel_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, new_name)
            winreg.CloseKey(key)
            print(
                f"[SUCCESS] Updated real DirectShow camera to '{new_name}' in {root_str}\\{rel_path}"
            )
        except PermissionError:
            print(f"[NOTICE] Admin required to write {root_str}\\{rel_path}")
        except Exception as e:
            print(f"[ERROR] Could not write {root_str}: {e}")


if __name__ == "__main__":
    clean_and_rename("DTA Camera")
