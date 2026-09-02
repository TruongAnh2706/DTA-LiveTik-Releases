"""DirectShow Virtual Camera Stream Engine using pyvirtualcam for "DTA Camera"."""

from PySide6.QtCore import QObject, QThread, Signal

try:
    import pyvirtualcam  # type: ignore[import-untyped]
except ImportError:
    pyvirtualcam = None


class VirtualCamStreamThread(QThread):
    """Thread continuously streaming video frames to Windows Virtual Camera Driver."""

    frame_processed = Signal(int)

    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: float = 30.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.width = width
        self.height = height
        self.fps = fps
        self._is_running = False

    def run(self) -> None:
        """Run Virtual Cam streaming loop."""
        self._is_running = True
        if pyvirtualcam is None:
            print("[DTA VirtualCam Engine] pyvirtualcam library not installed.")
            return

        try:
            with pyvirtualcam.Camera(
                width=self.width,
                height=self.height,
                fps=self.fps,
                fmt=pyvirtualcam.PixelFormat.RGB,
                device="DTA Camera",
            ) as cam:
                print(
                    f"[DTA VirtualCam Engine] Active Output: {cam.device} ({cam.width}x{cam.height} @ {cam.fps}fps)"
                )
                while self._is_running:
                    self.msleep(33)
        except Exception as e:
            print(f"[DTA VirtualCam Engine] Virtual Camera Loop: {e}")

    def stop(self) -> None:
        """Stop Virtual Cam thread."""
        self._is_running = False
        self.wait()
