"""DTA AutoLive - Real Windows PnP & Media Capture Device Diagnostic Engine.

Generates structured diagnostics report:
- diagnostics/device_install_report.json
- diagnostics/device_install_report.txt
"""

import json
import platform
import subprocess
import sys
from pathlib import Path


def get_windows_version() -> str:
    """Return OS version string."""
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def run_powershell_cmd(cmd: str) -> str:
    """Run a PowerShell command safely and return output."""
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error executing PowerShell: {e}"


def check_test_signing() -> str:
    """Check BCD edit test signing state."""
    try:
        res = subprocess.run(["bcdedit.exe"], capture_output=True, text=True, check=False)  # noqa: S607
        output = res.stdout
        if "testsigning             Yes" in output or "testsigning             On" in output:
            return "ENABLED"
        if "testsigning             No" in output or "testsigning             Off" in output:
            return "DISABLED"
        return "UNKNOWN_OR_DEFAULT"
    except Exception as e:
        return f"Error checking bcdedit: {e}"


def check_pnp_device(friendly_name: str) -> dict[str, str]:
    """Check PnP device state in Windows Device Manager."""
    cmd = f"Get-PnpDevice | Where-Object {{ `$_.FriendlyName -like '*{friendly_name}*' }} | Select-Object InstanceId, Status, Class, Present | ConvertTo-Json"
    raw_json = run_powershell_cmd(cmd)
    if not raw_json:
        return {
            "status": "NOT_INSTALLED",
            "friendly_name": friendly_name,
            "raw": "No PnP Device Found",
        }
    try:
        data = json.loads(raw_json)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        return {
            "status": "DEVICE_CREATED" if data.get("Present") else "DEVICE_PRESENT_FALSE",
            "pnp_status": data.get("Status", "UNKNOWN"),
            "instance_id": data.get("InstanceId", ""),
            "class": data.get("Class", ""),
            "friendly_name": friendly_name,
        }
    except Exception:
        return {"status": "PARSE_ERROR", "friendly_name": friendly_name, "raw": raw_json}


def check_driver_package(driver_name: str) -> dict[str, str]:
    """Check if driver package exists in Driver Store via PnPUtil."""
    cmd = f"pnputil /enum-drivers | Select-String '{driver_name}' -Context 2,5"
    output = run_powershell_cmd(cmd)
    if output:
        return {"status": "DRIVER_PACKAGE_PRESENT", "output": output}
    return {"status": "DRIVER_PACKAGE_NOT_FOUND", "output": "Not found in Driver Store"}


def generate_full_report() -> dict[str, object]:
    """Gather all diagnostics data and write reports to disk."""
    report_dir = Path("diagnostics")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = str(
        subprocess.check_output(["powershell.exe", "Get-Date -Format s"], text=True).strip()
    )  # noqa: S607

    report_data = {
        "timestamp": timestamp_str,
        "os_version": get_windows_version(),
        "python_version": sys.version,
        "test_signing_state": check_test_signing(),
        "dta_camera_pnp": check_pnp_device("DTA Camera"),
        "dta_audio_pnp": check_pnp_device("DTA Audio"),
        "dta_camera_driver_package": check_driver_package("dta_camera"),
        "dta_audio_driver_package": check_driver_package("dta_audio"),
        "all_pnp_dta_devices": run_powershell_cmd(
            "Get-PnpDevice | Where-Object { `$_.FriendlyName -like '*DTA*' } | Format-Table -AutoSize | Out-String"
        ),
        "all_pnputil_dta_drivers": run_powershell_cmd(
            "pnputil /enum-drivers | Select-String 'DTA' -Context 3,8 | Out-String"
        ),
        "local_driver_files": [str(p) for p in Path("drivers").glob("**/*") if p.is_file()],
    }

    # Write JSON report
    json_path = report_dir / "device_install_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # Write TXT report
    txt_path = report_dir / "device_install_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("======================================================================\n")
        f.write("          DTA AUTOLIVE - REAL WINDOWS DEVICE DIAGNOSTICS REPORT        \n")
        f.write("======================================================================\n\n")
        f.write(f"Timestamp          : {report_data['timestamp']}\n")
        f.write(f"OS Version         : {report_data['os_version']}\n")
        f.write(f"Python Executable  : {sys.executable}\n")
        f.write(f"Test Signing State : {report_data['test_signing_state']}\n\n")
        f.write("--- DTA CAMERA PNP DEVICE --- \n")
        f.write(f"{json.dumps(report_data['dta_camera_pnp'], indent=2)}\n\n")
        f.write("--- DTA AUDIO PNP DEVICE --- \n")
        f.write(f"{json.dumps(report_data['dta_audio_pnp'], indent=2)}\n\n")
        f.write("--- DRIVER STORE PACKAGES --- \n")
        f.write(f"Camera Package: {report_data['dta_camera_driver_package']}\n")
        f.write(f"Audio Package : {report_data['dta_audio_driver_package']}\n\n")
        f.write("--- LOCAL DRIVER ARTIFACTS --- \n")
        f.writelines(f" - {file_path}\n" for file_path in report_data["local_driver_files"])

    print(f"[DIAGNOSTICS] Report generated at {json_path} and {txt_path}")
    return report_data


if __name__ == "__main__":
    generate_full_report()
