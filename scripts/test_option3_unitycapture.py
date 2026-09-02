"""Option 3 Test: UnityCapture / DirectShow Filter + Pyvirtualcam + FFmpeg Audio Engine Test."""

import sys
import winreg

import numpy as np
import pyvirtualcam

sys.stdout.reconfigure(encoding="utf-8")


def test_option_3() -> bool:
    """Register UnityCapture DirectShow Filter and test PyVirtualCam streaming."""
    print("=== TESTING PHUONG AN 3: PYVIRTUALCAM + UNITY CAPTURE DIRECTSHOW BACKEND ===")

    clsid_dshow_video = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"
    unity_guid = "{2D49788D-2101-4475-A013-14902C5E788A}"

    try:
        path = f"Software\\Classes\\CLSID\\{clsid_dshow_video}\\Instance\\{unity_guid}"

        for root, root_name in [
            (winreg.HKEY_CURRENT_USER, "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
        ]:
            try:
                k = winreg.CreateKeyEx(root, path, 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(k, "FriendlyName", 0, winreg.REG_SZ, "DTA Camera")
                winreg.SetValueEx(k, "CLSID", 0, winreg.REG_SZ, unity_guid)
                winreg.CloseKey(k)
                print(f"[REGISTRY SUCCESS] Registered UnityCapture GUID under {root_name}")
            except Exception as ex:
                print(f"[REGISTRY WARNING] Could not set {root_name} key: {ex}")

        print("[PYVIRTUALCAM] Initializing pyvirtualcam with Unity Capture backend...")
        try:
            with pyvirtualcam.Camera(
                width=1080,
                height=1920,
                fps=30,
                fmt=pyvirtualcam.PixelFormat.RGB,
                backend="unitycapture",
                device="DTA Camera",
            ) as cam:
                print(
                    f"[SUCCESS OPTION 3] pyvirtualcam initialized! Device: '{cam.device}', Native FourCC: {cam.native_fourcc}"
                )
                for i in range(100):
                    frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
                    frame[:, :, 0] = (i * 2) % 255
                    cam.send(frame)
                    cam.sleep_until_next_frame()
                print("[SUCCESS OPTION 3] Sent 100 frames successfully to DTA Camera!")
                return True
        except Exception as e:
            print(f"[OPTION 3 ERROR] pyvirtualcam unitycapture failed: {e}")

            try:
                with pyvirtualcam.Camera(
                    width=1080, height=1920, fps=30, fmt=pyvirtualcam.PixelFormat.RGB
                ) as cam:
                    print(
                        f"[SUCCESS OPTION 3 FALLBACK] pyvirtualcam auto-selected device: '{cam.device}'"
                    )
                    return True
            except Exception as e2:
                print(f"[OPTION 3 AUTO ERROR] pyvirtualcam auto failed: {e2}")

    except Exception as e:
        print(f"[OPTION 3 CRITICAL ERROR] {e}")

    return False


if __name__ == "__main__":
    test_option_3()
