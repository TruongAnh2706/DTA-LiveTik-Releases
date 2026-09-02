"""Virtual Device Adapter Engine for DTA Virtual Camera ("DTA Camera") & Audio ("DTA Audio").

Queries actual Windows PnP & QMediaDevices state instead of returning fake success.
"""

import subprocess
from enum import Enum

from PySide6.QtMultimedia import QAudioDevice, QMediaDevices

DTA_CAMERA_NAME = "DTA Camera"
DTA_AUDIO_NAME = "DTA Audio"


class DeviceStatus(str, Enum):
    """Device status states based on real Windows system enumeration."""

    NOT_INSTALLED = "NOT_INSTALLED"
    DRIVER_PACKAGE_PRESENT = "DRIVER_PACKAGE_PRESENT"
    DEVICE_CREATED = "DEVICE_CREATED"
    DRIVER_LOADED = "DRIVER_LOADED"
    ENDPOINT_ENUMERATED = "ENDPOINT_ENUMERATED"
    STREAM_AVAILABLE = "STREAM_AVAILABLE"
    ERROR = "ERROR"


class VirtualDeviceAdapter:
    """Manages DTA Virtual Camera & Audio device enumeration based strictly on Windows PnP state."""

    @staticmethod
    def get_dta_camera_name() -> str:
        """Get DTA Camera device name."""
        return DTA_CAMERA_NAME

    @staticmethod
    def get_dta_audio_name() -> str:
        """Get DTA Audio device name."""
        return DTA_AUDIO_NAME

    @staticmethod
    def query_camera_status() -> tuple[DeviceStatus, str]:
        """Query real Windows system camera enumeration and PnP state."""
        # 1. Check QMediaDevices for actual enumerated video capture input
        cameras = QMediaDevices.videoInputs()
        for cam in cameras:
            if DTA_CAMERA_NAME.upper() in cam.description().upper():
                return (
                    DeviceStatus.STREAM_AVAILABLE,
                    f"DTA Camera | {cam.description()} (Enumerated in Windows)",
                )

        # 2. Check PnP Device via PowerShell
        try:
            cmd = "Get-PnpDevice | Where-Object { $_.FriendlyName -like '*DTA Camera*' } | Select-Object -ExpandProperty Status"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )  # noqa: S607
            status_text = res.stdout.strip()
            if status_text == "OK":
                return DeviceStatus.DRIVER_LOADED, "DTA Camera PnP Device Present & Driver Loaded"
            if status_text:
                return (
                    DeviceStatus.DEVICE_CREATED,
                    f"DTA Camera PnP Device Created (Status: {status_text})",
                )
        except Exception:
            pass

        # 3. Check Driver Store
        try:
            cmd = "pnputil.exe /enum-drivers | Select-String 'dta_camera' -Context 0,2"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )  # noqa: S607
            if res.stdout.strip():
                return (
                    DeviceStatus.DRIVER_PACKAGE_PRESENT,
                    "Driver Package in Driver Store (Device Not Created)",
                )
        except Exception:
            pass

        return DeviceStatus.NOT_INSTALLED, "DTA Camera Chưa được cài đặt vào hệ thống Windows"

    @staticmethod
    def query_audio_status() -> tuple[DeviceStatus, str]:
        """Query real Windows system audio enumeration and PnP state."""
        # 1. Check QMediaDevices audio inputs/outputs
        for dev in QMediaDevices.audioInputs():
            if DTA_AUDIO_NAME.upper() in dev.description().upper():
                return (
                    DeviceStatus.STREAM_AVAILABLE,
                    f"DTA Audio | {dev.description()} (Enumerated Audio Input)",
                )

        # 2. Check PnP Device
        try:
            cmd = "Get-PnpDevice | Where-Object { $_.FriendlyName -like '*DTA Audio*' } | Select-Object -ExpandProperty Status"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )  # noqa: S607
            status_text = res.stdout.strip()
            if status_text == "OK":
                return DeviceStatus.DRIVER_LOADED, "DTA Audio PnP Device Present & Driver Loaded"
            if status_text:
                return (
                    DeviceStatus.DEVICE_CREATED,
                    f"DTA Audio PnP Device Created (Status: {status_text})",
                )
        except Exception:
            pass

        return DeviceStatus.NOT_INSTALLED, "DTA Audio Chưa được định tuyến trên hệ thống Windows"

    @staticmethod
    def detect_virtual_cameras() -> list[str]:
        """Return list of actually enumerated video camera devices."""
        cameras = QMediaDevices.videoInputs()
        return [cam.description() for cam in cameras]

    @staticmethod
    def detect_virtual_mics() -> list[str]:
        """Return list of actually enumerated audio input devices."""
        audio_inputs = QMediaDevices.audioInputs()
        return [dev.description() for dev in audio_inputs]

    @staticmethod
    def get_dta_audio_device() -> QAudioDevice:
        """Get proprietary DTA Audio Output device endpoint if available, else default."""
        for dev in QMediaDevices.audioOutputs():
            if DTA_AUDIO_NAME.upper() in dev.description().upper():
                return dev
        return QMediaDevices.defaultAudioOutput()
