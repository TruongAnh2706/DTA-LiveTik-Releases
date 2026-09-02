"""DTA AutoLive - Technical Options Diagnostic & Probing Tool.

Probes and evaluates:
Option 1: tshino/softcam DirectShow DLL binding
Option 2: BestCam / Windows Media Foundation Shared Memory Source
Option 3: pyvirtualcam with Unity Capture / DirectShow Filter
"""

from pathlib import Path

import pyvirtualcam


def probe_options() -> dict[str, object]:
    """Probe installed backends and DLL availability for Options 1, 2, 3."""
    report: dict[str, object] = {}

    # --- Option 1: softcam DLL ---
    softcam_dll = Path("drivers/softcam.dll").absolute()
    report["opt1_softcam_dll_exists"] = softcam_dll.exists()

    # --- Option 2: BestCam / Media Foundation ---
    bestcam_dll = Path("drivers/BestCam64.dll").absolute()
    report["opt2_bestcam_dll_exists"] = bestcam_dll.exists()

    # --- Option 3: pyvirtualcam backends ---
    report["pyvirtualcam_path"] = pyvirtualcam.__file__

    # Try creating pyvirtualcam instance with different backends
    supported_backends = []
    for backend_name in ["unitycapture", "obs", "vcam"]:
        try:
            with pyvirtualcam.Camera(
                width=640,
                height=480,
                fps=30,
                fmt=pyvirtualcam.PixelFormat.RGB,
                backend=backend_name,
            ) as cam:
                supported_backends.append(
                    {"backend": backend_name, "device": cam.device, "status": "WORKING"}
                )
        except Exception as e:
            supported_backends.append({"backend": backend_name, "status": f"FAILED: {e}"})

    report["opt3_pyvirtualcam_backends"] = supported_backends

    print("=== TECHNICAL OPTIONS PROBE REPORT ===")
    for k, v in report.items():
        print(f"{k}: {v}")

    return report


if __name__ == "__main__":
    probe_options()
