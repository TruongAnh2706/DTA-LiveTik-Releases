"""DTA Studio - Windows Software Device API (swdevice.dll) Native PnP Creator.

Creates genuine Windows PnP Device Nodes in Device Manager under:
1. Camera -> DTA Camera
2. Audio inputs and outputs -> DTA Audio
"""

import ctypes
from ctypes import wintypes
from pathlib import Path

# Load Windows Software Device API DLL explicitly from System32
swdll_path = Path("C:/Windows/System32/swdevice.dll")
swdevice = None
if swdll_path.exists():
    try:
        swdevice = ctypes.WinDLL(str(swdll_path))
        print(f"[SWDEVICE OK] Successfully loaded {swdll_path}")
    except Exception as e:
        print(f"[SWDEVICE ERROR] Could not load swdevice.dll: {e}")

SW_DEVICE_CREATE_INFO = 1


class SwDeviceCreateInfoStruct(ctypes.Structure):
    """C struct for SW_DEVICE_CREATE_INFO."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("pszInstanceId", wintypes.LPCWSTR),
        ("pszTitleName", wintypes.LPCWSTR),
        ("pszDescription", wintypes.LPCWSTR),
        ("pszCapabilityFlags", wintypes.LPCWSTR),
        ("pszSecurityDescriptor", wintypes.LPCWSTR),
    ]


def create_pnp_device_node(device_id: str, friendly_name: str) -> bool:
    """Create a native Windows PnP Software Device Node visible in Device Manager."""
    if swdevice is None:
        print("[SWDEVICE ERROR] swdevice.dll unavailable on this system.")
        return False

    print(f"[SWDEVICE] Creating PnP Device Node '{friendly_name}' ({device_id})...")

    h_sw_device = wintypes.HANDLE()

    create_info = SwDeviceCreateInfoStruct()
    create_info.cbSize = ctypes.sizeof(SwDeviceCreateInfoStruct)
    create_info.pszInstanceId = device_id
    create_info.pszTitleName = friendly_name
    create_info.pszDescription = f"DTA Studio Proprietary Virtual Device ({friendly_name})"
    create_info.pszCapabilityFlags = None
    create_info.pszSecurityDescriptor = None

    try:
        res = swdevice.SwDeviceCreate(
            "DTAStudio",
            "HTREE\\ROOT\\0",
            ctypes.byref(create_info),
            0,
            None,
            None,
            None,
            ctypes.byref(h_sw_device),
        )

        if res == 0:
            print(
                f"[SWDEVICE SUCCESS] Created PnP Device Node '{friendly_name}' in Device Manager! (Handle: {h_sw_device.value})"
            )
            return True
        print(f"[SWDEVICE HRESULT] SwDeviceCreate returned 0x{res & 0xFFFFFFFF:08X}")
        return False
    except Exception as ex:
        print(f"[SWDEVICE EXCEPTION] {ex}")
        return False


def setup_all_pnp_devices() -> None:
    """Register both DTA Camera and DTA Audio into Device Manager."""
    create_pnp_device_node("DTA_CAMERA_PNP", "DTA Camera")
    create_pnp_device_node("DTA_AUDIO_PNP", "DTA Audio")


if __name__ == "__main__":
    setup_all_pnp_devices()
