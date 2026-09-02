"""Python Shared Memory Frame Producer for DTA Camera WDM Kernel Driver."""

import ctypes
import mmap
import time

import cv2
import numpy as np

DTA_SHM_MAGIC = 0x534F4654  # "SOFT" - Unified Softcam Architecture
DTA_SHM_GLOBAL_NAME = "Global\\DTACameraSharedMemory"
DTA_SHM_LOCAL_NAME = "Local\\DTACameraSharedMemory"
WIDTH = 1080
HEIGHT = 1920
FPS = 30
PAYLOAD_SIZE = WIDTH * HEIGHT * 3  # Max buffer BGR24
SHM_TOTAL_SIZE = 64 + PAYLOAD_SIZE


class DTAFrameHeader(ctypes.Structure):
    """C-compatible DTA_SOFTCAM_HEADER struct matching DTA Camera DirectShow & Kernel driver."""

    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("fps", ctypes.c_uint32),
        ("format", ctypes.c_uint32),  # 0: BGR24
        ("frame_index", ctypes.c_uint64),
        ("timestamp_ms", ctypes.c_uint64),
        ("payload_size", ctypes.c_uint32),
    ]


class DTASharedMemoryVideoProducer:
    """Manages Windows Shared Memory mapping for DTA Camera Driver matching FHD Camera."""

    def __init__(self) -> None:
        self.shm: mmap.mmap | None = None
        self.frame_counter = 0
        self._init_shm()

    def _init_shm(self) -> None:
        """Initialize Windows Named Shared Memory block with graceful Global/Local fallback."""
        try:
            self.shm = mmap.mmap(-1, SHM_TOTAL_SIZE, tagname=DTA_SHM_GLOBAL_NAME, access=mmap.ACCESS_WRITE)
            print(f"[DTA SHM Producer] Successfully initialized Shared Memory '{DTA_SHM_GLOBAL_NAME}' ({SHM_TOTAL_SIZE} bytes)")
        except PermissionError:
            try:
                self.shm = mmap.mmap(-1, SHM_TOTAL_SIZE, tagname=DTA_SHM_LOCAL_NAME, access=mmap.ACCESS_WRITE)
                print(f"[DTA SHM Producer] Fallback to Local Shared Memory '{DTA_SHM_LOCAL_NAME}' ({SHM_TOTAL_SIZE} bytes)")
            except Exception as ex:
                print(f"[DTA SHM Producer Error] Local SHM failed: {ex}")
                self.shm = None
        except Exception as e:
            print(f"[DTA SHM Producer Error] SHM failed: {e}")
            self.shm = None

    def write_mjpeg_frame(self, bgr_image_array: np.ndarray) -> None:
        """Encode BGR image array into MJPEG (Motion JPEG) format matching physical FHD Camera."""
        if self.shm is None:
            return

        success, encoded_jpg = cv2.imencode(".jpg", bgr_image_array, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not success:
            return

        jpg_bytes = encoded_jpg.tobytes()
        self.frame_counter += 1

        header = DTAFrameHeader(
            magic=DTA_SHM_MAGIC,
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            format=3,  # MJPEG
            frame_index=self.frame_counter,
            timestamp_ms=int(time.time() * 1000),
            payload_size=len(jpg_bytes),
        )

        header_bytes = bytes(header)
        self.shm.seek(0)
        self.shm.write(header_bytes)
        self.shm.write(jpg_bytes)

    def write_frame_bytes(self, raw_rgb_bytes: bytes) -> None:
        """Write RGB24 image byte buffer directly into Shared Memory."""
        if self.shm is None:
            return

        self.frame_counter += 1
        header = DTAFrameHeader(
            magic=DTA_SHM_MAGIC,
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            format=0,  # RGB24 / BGR24
            frame_index=self.frame_counter,
            timestamp_ms=int(time.time() * 1000),
            payload_size=PAYLOAD_SIZE,
        )

        header_bytes = bytes(header)
        self.shm.seek(0)
        self.shm.write(header_bytes)
        self.shm.write(raw_rgb_bytes[:PAYLOAD_SIZE])

    def write_black_frame(self) -> None:
        """Write blank black MJPEG frame (1920x1080) into Shared Memory."""
        black_array = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        self.write_mjpeg_frame(black_array)

    def close(self) -> None:
        """Close Shared Memory mapping."""
        if self.shm:
            self.shm.close()
            self.shm = None
