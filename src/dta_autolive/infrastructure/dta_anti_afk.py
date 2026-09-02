"""DTA Studio - Anti-AFK Human-Like Mouse Activity Simulator for TikTok LIVE Studio.

Prevents TikTok LIVE Studio from pausing or terminating streams due to inactivity
by periodically generating subtle, natural mouse movements and safe interactions.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import contextlib
import ctypes
import random
import threading
import time
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()

# Windows API Types & Constants
user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class DTAAntiAfkSimulator:
    """Simulates realistic human mouse activity on TikTok LIVE Studio window."""

    def __init__(self, log_callback: Callable[[str, str], None] | None = None) -> None:
        self.is_running: bool = False
        self.log_callback = log_callback
        self._thread: threading.Thread | None = None
        self._interval_min: float = 25.0
        self._interval_max: float = 45.0

    def log(self, level: str, message: str) -> None:
        if self.log_callback:
            with contextlib.suppress(Exception):
                self.log_callback(level, message)
        logger.info("anti_afk_log", level=level, message=message)

    def find_tiktok_live_studio_window(self) -> int | None:
        """Find HWND of TikTok LIVE Studio."""
        if not user32:
            return None

        found_hwnd = None

        def enum_windows_callback(hwnd: int, lparam: Any) -> bool:
            nonlocal found_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if "tiktok live studio" in title or "live studio" in title:
                        found_hwnd = hwnd
                        return False
            return True

        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(enum_windows_callback)
        user32.EnumWindows(enum_proc, 0)
        return found_hwnd

    def get_cursor_pos(self) -> tuple[int, int]:
        """Get current mouse cursor position."""
        if not user32:
            return (0, 0)
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def set_cursor_pos(self, x: int, y: int) -> None:
        """Set mouse cursor position smoothly."""
        if user32:
            user32.SetCursorPos(int(x), int(y))

    def smooth_move(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> None:
        """Perform natural smooth Bezier-curve mouse movement."""
        steps = max(15, int(duration * 60))
        # Control point for slight natural curve
        ctrl_x = (start_x + end_x) / 2 + random.randint(-40, 40)  # noqa: S311
        ctrl_y = (start_y + end_y) / 2 + random.randint(-40, 40)  # noqa: S311

        for i in range(1, steps + 1):
            t = i / steps
            # Quadratic Bezier: B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
            curr_x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t**2 * end_x
            curr_y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t**2 * end_y
            self.set_cursor_pos(int(curr_x), int(curr_y))
            time.sleep(duration / steps)

    def simulate_micro_activity(self) -> None:
        """Thực hiện một tương tác chống AFK an toàn 100%, KHÔNG cướp chuột, KHÔNG click chuột."""
        if not user32 or not self.is_running:
            return

        # 1. Sử dụng SetThreadExecutionState chuẩn Windows để chống sleep/standby
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
            with contextlib.suppress(Exception):
                # ES_CONTINUOUS = 0x80000000 | ES_SYSTEM_REQUIRED = 0x00000001 | ES_DISPLAY_REQUIRED = 0x00000002
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)

        # 2. Tạo vi chuyển động cực nhỏ (micro-movement) chỉ 1 pixel và trả về ngay để hệ thống nhận diện hoạt động
        cur_x, cur_y = self.get_cursor_pos()
        if not self.is_running:
            return

        with contextlib.suppress(Exception):
            # Di chuyển nhẹ 1 pixel
            user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
            time.sleep(0.02)
            if self.is_running:
                # Trả về vị trí cũ ngay lập tức
                user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, 0)

        self.log("INFO", "🛡️ [Anti-AFK] Đã duy trì trạng thái hoạt động an toàn cho Live Studio (Không can thiệp chuột).")

    def start(self) -> None:
        """Start anti-AFK activity simulation loop."""
        if self.is_running:
            return
        self.is_running = True

        def _loop() -> None:
            self.log(
                "SUCCESS",
                "🛡️ [Anti-AFK] Hệ thống Chống Dừng Live Tự Động ĐÃ KÍCH HOẠT (Giữ hệ thống luôn On-Air).",
            )
            while self.is_running:
                sleep_time = random.uniform(self._interval_min, self._interval_max)  # noqa: S311
                for _ in range(int(sleep_time * 2)):
                    if not self.is_running:
                        break
                    time.sleep(0.5)

                if self.is_running:
                    try:
                        self.simulate_micro_activity()
                    except Exception as e:
                        logger.warning("anti_afk_simulation_failed", error=str(e))

            self.log("INFO", "🛑 [Anti-AFK] Đã tắt hoàn toàn hệ thống chống dừng Live.")

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop anti-AFK simulation immediately."""
        self.is_running = False
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
            with contextlib.suppress(Exception):
                # Reset thread execution state
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
