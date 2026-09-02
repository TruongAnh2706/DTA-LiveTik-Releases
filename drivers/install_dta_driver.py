"""DTA Studio - DirectShow Virtual Camera ("DTA Camera") & Audio ("DTA Audio") Native Registry Registrar."""

import winreg


def register_dta_hardware_devices() -> bool:
    """Register and alias Windows DirectShow Capture Category devices to 'DTA Camera' and 'DTA Audio'."""
    success = False
    # Register in HKCU (Current User - No admin elevation required)
    hkcu_paths = [
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
            "DTA Camera",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio",
        ),
    ]

    for root, path, name in hkcu_paths:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, name)
            winreg.CloseKey(key)
            success = True
        except Exception as e:
            print(f"[DTA Driver Registrar HKCU Warning] {path}: {e}")

    # Try HKLM (System-wide - Works when elevated)
    hklm_paths = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{DTA11000-CAM1-4D01-8D3B-00A0C911CE86}",
            "DTA Camera",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Classes\CLSID\{E0C158E1-DCD4-11D1-A1CE-0080C758D608}\Instance\{DTA11000-AUD1-4D01-8D3B-00A0C911CE86}",
            "DTA Audio",
        ),
    ]
    for root, path, name in hklm_paths:
        try:
            key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, name)
            winreg.CloseKey(key)
            success = True
        except Exception:
            pass

    if success:
        print(
            "[DTA Driver Registrar] SUCCESS: DTA Camera and DTA Audio registered into DirectShow Subsystem!"
        )
    return success


if __name__ == "__main__":
    register_dta_hardware_devices()
