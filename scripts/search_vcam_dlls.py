"""Search C: drive for virtual camera DLLs."""

from pathlib import Path


def search_dlls() -> list[str]:
    """Find any virtual camera DLLs on the machine."""
    targets = [
        "unitycapturefilter64.dll",
        "softcam.dll",
        "obs-virtualcam-module64.dll",
        "virtualcam-module64.dll",
        "bestcam64.dll",
    ]
    found = []

    search_dirs = [
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/Windows/System32"),
        Path.home(),
        Path("c:/Users/Admin/Downloads"),
    ]

    for root_dir in search_dirs:
        if not root_dir.exists():
            continue
        try:
            for p in root_dir.rglob("*.dll"):
                if p.name.lower() in targets:
                    found.append(str(p.absolute()))
        except Exception:
            pass

    print("=== FOUND VIRTUAL CAMERA DLLs ===")
    for f in found:
        print(f)

    return found


if __name__ == "__main__":
    search_dlls()
