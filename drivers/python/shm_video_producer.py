"""Python Shared Memory Frame Producer for DTA Camera WDM Kernel Driver."""

import ctypes
import mmap
import time

import numpy as np

DTA_SHM_MAGIC = 0x44544143  # "DTAC"
DTA_SHM_NAME = "Global\\DTACameraSharedMemory"
WIDTH = 1080
HEIGHT = 1920
FPS = 30
PAYLOAD_SIZE = WIDTH * HEIGHT * 3  # 6,220,800 bytes for RGB24
SHM_TOTAL_SIZE = 64 + PAYLOAD_SIZE


class DTAFrameHeader(ctypes.Structure):
    """C-compatible DTA_FRAME_HEADER struct."""

    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("fps", ctypes.c_uint32),
        ("format", ctypes.c_uint32),
        ("frame_index", ctypes.c_uint64),
        ("timestamp_ms", ctypes.c_uint64),
        ("payload_size", ctypes.c_uint32),
    ]


class DTASharedMemoryVideoProducer:
    """Manages Windows Shared Memory mapping for DTA Camera Driver."""

    def __init__(self) -> None:
        self.shm: mmap.mmap | None = None
        self.frame_counter = 0
        self._init_shm()

    def _init_shm(self) -> None:
        """Initialize Windows Named Shared Memory block."""
        try:
            self.shm = mmap.mmap(-1, SHM_TOTAL_SIZE, tagname=DTA_SHM_NAME, access=mmap.ACCESS_WRITE)
            print(
                f"[DTA SHM Producer] Successfully initialized Shared Memory '{DTA_SHM_NAME}' ({SHM_TOTAL_SIZE} bytes)"
            )
        except Exception as e:
            print(f"[DTA SHM Producer Warning] Local SHM fallback: {e}")
            self.shm = None

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
            format=0,  # RGB24
            frame_index=self.frame_counter,
            timestamp_ms=int(time.time() * 1000),
            payload_size=PAYLOAD_SIZE,
        )

        header_bytes = bytes(header)
        self.shm.seek(0)
        self.shm.write(header_bytes)
        self.shm.write(raw_rgb_bytes[:PAYLOAD_SIZE])

    def write_black_frame(self) -> None:
        """Write blank black frame (1080x1920) into Shared Memory."""
        black_array = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        self.write_frame_bytes(black_array.tobytes())

    def close(self) -> None:
        """Close Shared Memory mapping."""
        if self.shm:
            self.shm.close()
            self.shm = None
