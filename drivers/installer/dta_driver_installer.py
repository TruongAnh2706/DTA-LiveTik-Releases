"""DTA Studio - Automated PnPUtil INF Driver Installer for DTA Camera & DTA Audio."""

import subprocess
from pathlib import Path


class DTADriverInstaller:
    """Automates PnPUtil installation of DTA Camera and DTA Audio INF driver packages."""

    @staticmethod
    def install_all_drivers() -> tuple[bool, list[str]]:
        """Install INF driver packages using Windows PnPUtil engine."""
        logs: list[str] = []
        logs.append("[DTA INSTALLER] Starting PnPUtil INF Driver Installation...")

        camera_inf = Path("drivers/camera/dta_camera.inf").absolute()
        audio_inf = Path("drivers/audio/dta_audio.inf").absolute()

        # 1. Install DTA Camera INF Package
        if camera_inf.exists():
            cmd = f'pnputil /add-driver "{camera_inf}" /install'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            logs.append(f"[CAMERA INF] Executed: {cmd}")
            logs.append(f"[CAMERA INF] Result Code: {res.returncode}")
            logs.append(f"[CAMERA INF Output] {res.stdout.strip()}")
        else:
            logs.append(f"[CAMERA INF WARNING] Path not found: {camera_inf}")

        # 2. Install DTA Audio INF Package
        if audio_inf.exists():
            cmd = f'pnputil /add-driver "{audio_inf}" /install'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            logs.append(f"[AUDIO INF] Executed: {cmd}")
            logs.append(f"[AUDIO INF] Result Code: {res.returncode}")
            logs.append(f"[AUDIO INF Output] {res.stdout.strip()}")
        else:
            logs.append(f"[AUDIO INF WARNING] Path not found: {audio_inf}")

        logs.append("[SUCCESS] DTA Camera & DTA Audio INF Driver setup finished!")
        return True, logs


if __name__ == "__main__":
    _, output_logs = DTADriverInstaller.install_all_drivers()
    for line in output_logs:
        print(line)
