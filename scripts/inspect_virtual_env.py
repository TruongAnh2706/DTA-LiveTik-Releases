"""Inspect system for virtual camera DLLs, OBS virtualcam, and MMDevice audio endpoints."""

import json
import winreg
from pathlib import Path


def inspect_system() -> dict[str, object]:
    """Inspect installed virtual camera binaries and MMDevice capture endpoints."""
    results: dict[str, object] = {}

    # 1. Check for OBS Studio VirtualCam DLLs
    obs_paths = [
        Path("C:/Program Files/obs-studio/bin/64bit/obs-virtualcam-module64.dll"),
        Path("C:/Program Files (x86)/obs-studio/bin/64bit/obs-virtualcam-module64.dll"),
        Path("C:/Program Files/obs-studio/data/obs-plugins/win-dshow/virtualcam-module64.dll"),
    ]
    found_obs_dlls = [str(p) for p in obs_paths if p.exists()]
    results["obs_virtualcam_dlls"] = found_obs_dlls

    # 2. Check Windows MMDevice Recording Audio Endpoints (Microphones / Inputs)
    audio_endpoints = []
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        i = 0
        while True:
            try:
                sub_guid = winreg.EnumKey(key, i)
                i += 1
                try:
                    prop_key = winreg.OpenKey(key, f"{sub_guid}\\Properties")
                    # Query FriendlyName property
                    val, _ = winreg.QueryValueEx(
                        prop_key, "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
                    )
                    audio_endpoints.append({"guid": sub_guid, "friendly_name": val})
                    winreg.CloseKey(prop_key)
                except Exception:
                    pass
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception as e:
        results["mmdevice_error"] = str(e)

    results["mmdevice_capture_endpoints"] = audio_endpoints

    # 3. Check DirectShow Registered Cameras
    dshow_cameras = []
    try:
        key_path = r"Software\Classes\CLSID\{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance"
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                k = winreg.OpenKey(root, key_path)
                j = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, j)
                        j += 1
                        sub_k = winreg.OpenKey(k, sub)
                        try:
                            fname, _ = winreg.QueryValueEx(sub_k, "FriendlyName")
                            root_name = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
                            dshow_cameras.append(
                                {"root": root_name, "clsid": sub, "friendly_name": fname}
                            )
                        except Exception:
                            pass
                        winreg.CloseKey(sub_k)
                    except OSError:
                        break
                winreg.CloseKey(k)
            except Exception:
                pass
    except Exception as e:
        results["dshow_error"] = str(e)

    results["dshow_cameras"] = dshow_cameras

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    inspect_system()
