"""Inspect hardware parameters and formats of physical FHD Camera on Windows."""

import cv2
from PySide6.QtMultimedia import QMediaDevices


def inspect_camera() -> None:
    """Inspect physical FHD Camera resolutions, FPS, and Codec formats."""
    print("=== WINDOWS MEDIA DEVICES ENUMERATION ===")
    devices = QMediaDevices.videoInputs()
    for idx, dev in enumerate(devices):
        print(f"[{idx}] Name: {dev.description()}, ID: {dev.id()}")

    print("\n=== OPENCV CAPTURE PROBE (FHD Camera) ===")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Could not open OpenCV DirectShow Camera index 0")
        return

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

    print(f"Current Resolution: {int(width)}x{int(height)}")
    print(f"Current FPS       : {fps}")
    print(f"Current FourCC    : {fourcc_str} (0x{fourcc_int:08X})")
    cap.release()


if __name__ == "__main__":
    inspect_camera()
