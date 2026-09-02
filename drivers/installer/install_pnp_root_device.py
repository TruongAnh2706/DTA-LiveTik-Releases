"""DTA Studio - Windows Root PnP Device Manager Node Installer.

Installs Root PnP hardware device nodes into Windows Device Manager using SetupAPI matching dta_camera.inf:
1. Device Manager -> Camera -> DTA Camera
2. Device Manager -> Sound, video and game controllers -> DTA Audio
"""

import ctypes
import winreg
from ctypes import wintypes

setupapi = ctypes.windll.setupapi

DICD_GENERATE_ID = 0x00000001
SPDRP_FRIENDLYNAME = 0x0000000C
SPDRP_HARDWAREID = 0x00000001
SPDRP_DEVICEDESC = 0x00000000


class GUID(ctypes.Structure):
    """C struct GUID."""

    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SpDevinfoData(ctypes.Structure):
    """C struct SP_DEVINFO_DATA."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


# Function prototypes
setupapi.SetupDiCreateDeviceInfoList.argtypes = [ctypes.POINTER(GUID), wintypes.HWND]
setupapi.SetupDiCreateDeviceInfoList.restype = wintypes.HANDLE

setupapi.SetupDiCreateDeviceInfoW.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    ctypes.POINTER(GUID),
    wintypes.LPCWSTR,
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.POINTER(SpDevinfoData),
]
setupapi.SetupDiCreateDeviceInfoW.restype = wintypes.BOOL

setupapi.SetupDiSetDeviceRegistryPropertyW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(SpDevinfoData),
    wintypes.DWORD,
    ctypes.c_char_p,
    wintypes.DWORD,
]
setupapi.SetupDiSetDeviceRegistryPropertyW.restype = wintypes.BOOL

setupapi.SetupDiCallClassInstaller.argtypes = [
    wintypes.DWORD,
    wintypes.HANDLE,
    ctypes.POINTER(SpDevinfoData),
]
setupapi.SetupDiCallClassInstaller.restype = wintypes.BOOL

setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

# Official Camera Class GUID from dta_camera.inf: {ca3e7044-db67-4672-b465-4584056ad142}
GUID_CAMERA_INF_CLASS = GUID(
    0xCA3E7044,
    0xDB67,
    0x4672,
    (ctypes.c_ubyte * 8)(0xB4, 0x65, 0x45, 0x84, 0x05, 0x6A, 0xD1, 0x42),
)

# KSCATEGORY_VIDEO Class GUID: {e5323777-f976-4f5b-9b55-b94699c46e44}
GUID_KSCATEGORY_VIDEO = GUID(
    0xE5323777,
    0xF976,
    0x4F5B,
    (ctypes.c_ubyte * 8)(0x9B, 0x55, 0xB9, 0x46, 0x99, 0xC4, 0x6E, 0x44),
)

# Media / Sound Class GUID: {4d36e96c-e325-11ce-bfc1-08002be10318}
GUID_SOUND_CLASS = GUID(
    0x4D36E96C,
    0xE325,
    0x11CE,
    (ctypes.c_ubyte * 8)(0xBF, 0xC1, 0x08, 0x00, 0x2B, 0xE1, 0x03, 0x18),
)


def install_root_pnp_node(hardware_id: str, friendly_name: str, class_guid: GUID) -> bool:
    """Create a Root PnP Hardware Device Node in Device Manager using SetupAPI."""
    print(
        f"[PNP INSTALLER] Creating Device Manager Root PnP Node for '{friendly_name}' ({hardware_id})..."
    )

    h_dev_info = setupapi.SetupDiCreateDeviceInfoList(ctypes.byref(class_guid), None)
    if h_dev_info == wintypes.HANDLE(-1).value or not h_dev_info:
        print(f"[PNP ERROR] SetupDiCreateDeviceInfoList failed (Err: {ctypes.GetLastError()})")
        return False

    dev_info_data = SpDevinfoData()
    dev_info_data.cbSize = ctypes.sizeof(SpDevinfoData)

    res = setupapi.SetupDiCreateDeviceInfoW(
        h_dev_info,
        friendly_name,
        ctypes.byref(class_guid),
        friendly_name,
        None,
        DICD_GENERATE_ID,
        ctypes.byref(dev_info_data),
    )

    if not res:
        err = ctypes.GetLastError()
        print(f"[PNP ERROR] SetupDiCreateDeviceInfoW failed (Err: {err})")
        setupapi.SetupDiDestroyDeviceInfoList(h_dev_info)
        return False

    hwid_bytes = (hardware_id + "\0\0").encode("utf-16le")
    setupapi.SetupDiSetDeviceRegistryPropertyW(
        h_dev_info,
        ctypes.byref(dev_info_data),
        SPDRP_HARDWAREID,
        hwid_bytes,
        len(hwid_bytes),
    )

    fname_bytes = (friendly_name + "\0").encode("utf-16le")
    setupapi.SetupDiSetDeviceRegistryPropertyW(
        h_dev_info,
        ctypes.byref(dev_info_data),
        SPDRP_FRIENDLYNAME,
        fname_bytes,
        len(fname_bytes),
    )

    dif_registerdevice = 0x00000019
    res_reg = setupapi.SetupDiCallClassInstaller(
        dif_registerdevice, h_dev_info, ctypes.byref(dev_info_data)
    )

    setupapi.SetupDiDestroyDeviceInfoList(h_dev_info)

    if res_reg:
        print(f"[PNP SUCCESS] Successfully created '{friendly_name}' in Device Manager!")
        return True
    print(f"[PNP WARNING] SetupDiCallClassInstaller status: {ctypes.GetLastError()}")
    return False


def setup_device_manager_nodes() -> None:
    """Setup Device Manager PnP Nodes for DTA Camera and DTA Audio."""
    install_root_pnp_node("Root\\DTA_Camera", "DTA Camera", GUID_CAMERA_INF_CLASS)
    install_root_pnp_node("Root\\DTA_VirtualCamera", "DTA Camera", GUID_KSCATEGORY_VIDEO)
    install_root_pnp_node("Root\\DTA_VirtualAudio", "DTA Audio", GUID_SOUND_CLASS)

    try:
        k_cam = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Enum\Root\DTA_Camera\0000",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        winreg.SetValueEx(k_cam, "DeviceDesc", 0, winreg.REG_SZ, "DTA Camera")
        winreg.SetValueEx(k_cam, "FriendlyName", 0, winreg.REG_SZ, "DTA Camera")
        winreg.SetValueEx(k_cam, "Class", 0, winreg.REG_SZ, "Camera")
        winreg.SetValueEx(
            k_cam, "ClassGUID", 0, winreg.REG_SZ, "{ca3e7044-db67-4672-b465-4584056ad142}"
        )
        winreg.CloseKey(k_cam)

        print("[REGISTRY PNP] Enum Root PnP Registry Keys Created for DTA Camera!")
    except Exception as e:
        print(f"[REGISTRY PNP NOTICE] {e}")


if __name__ == "__main__":
    setup_device_manager_nodes()
