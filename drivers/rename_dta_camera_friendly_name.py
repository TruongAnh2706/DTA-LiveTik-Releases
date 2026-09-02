"""DTA Studio - DirectShow Camera FriendlyName Registrar.

Renames Windows DirectShow Camera Device FriendlyName from 'OBS Virtual Camera'
to 'DTA Camera' across HKCU and HKLM registry trees.
"""

import sys
import winreg


def rename_directshow_camera(new_name: str = "DTA Camera") -> bool:
    """Update DirectShow Video Capture Category FriendlyName in Windows Registry."""
    obs_clsid = "{A3FCE0F5-3493-419F-958A-ABA1250EC20B}"
    video_cat = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"

    paths = [
        (winreg.HKEY_CURRENT_USER, f"Software\\Classes\\CLSID\\{video_cat}\\Instance\\{obs_clsid}"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\Classes\\CLSID\\{video_cat}\\Instance\\{obs_clsid}",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\WOW6432Node\\Classes\\CLSID\\{video_cat}\\Instance\\{obs_clsid}",
        ),
    ]

    updated = False
    for root, rel_path in paths:
        root_str = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
        try:
            key = winreg.CreateKeyEx(root, rel_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, new_name)
            winreg.CloseKey(key)
            print(f"[SUCCESS] Updated camera name to '{new_name}' in {root_str}\\{rel_path}")
            updated = True
        except PermissionError:
            print(f"[NOTICE] Administrator privileges required for {root_str}\\{rel_path}")
        except Exception as e:
            print(f"[ERROR] Could not write {root_str}: {e}")

    return updated


if __name__ == "__main__":
    target_name = sys.argv[1] if len(sys.argv) > 1 else "DTA Camera"
    print(f"[DTA REGISTRAR] Updating DirectShow Camera FriendlyName to: '{target_name}'...")
    rename_directshow_camera(target_name)
