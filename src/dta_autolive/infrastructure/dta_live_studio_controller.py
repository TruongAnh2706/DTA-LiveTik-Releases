"""DTA Studio - TikTok LIVE Studio Automation Controller.

Tự động nhận diện cửa sổ, hỗ trợ bắt tọa độ thông minh 3 bước (Calibrate Coordinates)
và điều khiển chuột click chính xác 100% để tắt Livestream TikTok LIVE Studio khi hết video.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import contextlib
import ctypes
import json
import os
import random
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Đảm bảo tiến trình DPI Aware để tọa độ chuột trên màn hình 125%/150% khớp 100% với pixel thực tế
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    with contextlib.suppress(Exception):
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
            ctypes.windll.user32.SetProcessDPIAware()

user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
kernel32 = ctypes.windll.kernel32 if hasattr(ctypes, "windll") else None

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
SW_RESTORE = 9
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_SPACE = 0x20
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class DTALiveStudioController:
    """Điều khiển tự động tắt livestream trên TikTok LIVE Studio với chế độ học tọa độ 3 bước."""

    def __init__(
        self,
        log_callback: Callable[[str, str], None] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
        config_file: str | Path | None = None,
    ) -> None:
        self.log_callback = log_callback
        self.event_callback = event_callback
        self.is_busy: bool = False
        self.is_calibrating: bool = False
        self._calibration_thread: threading.Thread | None = None

        # Tọa độ 3 bước được lưu
        self.custom_points: dict[str, Any] = {}

        if config_file:
            self.config_path = Path(config_file)
        else:
            self.config_path = Path.home() / ".dta_autolive_live_studio_coords.json"

        self.load_custom_coordinates()

    def log(self, level: str, message: str) -> None:
        if self.log_callback:
            with contextlib.suppress(Exception):
                self.log_callback(level, message)
        logger.info("live_studio_controller", level=level, message=message)

    def emit_event(self, event: dict[str, Any]) -> None:
        if self.event_callback:
            with contextlib.suppress(Exception):
                self.event_callback(event)

    def load_custom_coordinates(self) -> dict[str, Any]:
        """Tải tọa độ đã lưu từ file cấu hình."""
        try:
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    self.custom_points = json.load(f)
                    logger.info("loaded_live_studio_custom_coords", coords=self.custom_points)
                    return self.custom_points
        except Exception as e:
            logger.warning("failed_to_load_custom_coords", error=str(e))
        self.custom_points = {}
        return {}

    def save_custom_coordinates(self, coords: dict[str, Any]) -> bool:
        """Lưu tọa độ 3 bước vào file cấu hình bền vững."""
        try:
            self.custom_points = coords
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(coords, f, indent=2, ensure_ascii=False)
            logger.info("saved_live_studio_custom_coords", coords=coords)
            return True
        except Exception as e:
            logger.error("failed_to_save_custom_coords", error=str(e))
            return False

    def clear_custom_coordinates(self) -> bool:
        """Xóa tọa độ tùy chỉnh, quay về chế độ tính toán tự động."""
        self.custom_points = {}
        with contextlib.suppress(Exception):
            if self.config_path.exists():
                os.remove(self.config_path)
        self.log("INFO", "🔄 Đã xóa tọa độ tùy chỉnh, Live Studio sẽ dùng chế độ tính toán tự động mặc định.")
        self.emit_event({"type": "LIVE_STUDIO_COORDS_CLEARED"})
        return True

    def find_tiktok_live_studio_window(self) -> int | None:
        """Tìm HWND cửa sổ TikTok LIVE Studio đang mở."""
        if not user32:
            return None

        found_hwnd = None
        max_area = 0

        def enum_windows_callback(hwnd: int, lparam: Any) -> bool:
            nonlocal found_hwnd, max_area
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if "tiktok live studio" in title or "live studio" in title:
                        rect = RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        area = (rect.right - rect.left) * (rect.bottom - rect.top)
                        # Chọn cửa sổ chính có diện tích lớn nhất (tránh các popup nhỏ)
                        if area > max_area:
                            max_area = area
                            found_hwnd = hwnd
            return True

        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(enum_windows_callback)
        user32.EnumWindows(enum_proc, 0)
        return found_hwnd

    def force_foreground_window(self, hwnd: int) -> bool:
        """Kích hoạt và ép cửa sổ lên Foreground chuẩn xác, vượt qua Windows Foreground Lockout."""
        if not user32 or not hwnd:
            return False
        try:
            # 1. Khôi phục nếu cửa sổ đang bị Minimize
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.08)

            # 2. Vượt qua Windows Foreground Lockout bằng AttachThreadInput
            current_thread = kernel32.GetCurrentThreadId() if kernel32 else 0
            remote_thread = user32.GetWindowThreadProcessId(hwnd, None)

            if current_thread and remote_thread and current_thread != remote_thread:
                user32.AttachThreadInput(current_thread, remote_thread, True)
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(current_thread, remote_thread, False)
            else:
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)

            time.sleep(0.15)
            return True
        except Exception as e:
            logger.warning("force_foreground_failed", error=str(e))
            return False

    def get_cursor_pos(self) -> tuple[int, int]:
        """Lấy tọa độ con trỏ chuột hiện tại."""
        if not user32:
            return (0, 0)
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def set_cursor_pos(self, x: int, y: int) -> None:
        """Đặt vị trí con trỏ chuột."""
        if user32:
            user32.SetCursorPos(int(x), int(y))

    def smooth_move(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.25) -> None:
        """Di chuyển chuột mượt mà kiểu Bezier curve tự nhiên."""
        steps = max(12, int(duration * 60))
        ctrl_x = (start_x + end_x) / 2 + random.randint(-15, 15)  # noqa: S311
        ctrl_y = (start_y + end_y) / 2 + random.randint(-15, 15)  # noqa: S311

        for i in range(1, steps + 1):
            t = i / steps
            curr_x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * end_x
            curr_y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * end_y
            self.set_cursor_pos(int(curr_x), int(curr_y))
            time.sleep(duration / steps)

    def click_at(self, x: int, y: int, hold_time: float = 0.1) -> None:
        """Click chuột trái dứt khoát tại tọa độ chỉ định với kích hoạt hover state đầy đủ."""
        if not user32:
            return
        # 1. Đặt vị trí chuột
        self.set_cursor_pos(x, y)
        time.sleep(0.04)

        # 2. Gửi sự kiện di chuột nhẹ để giao diện Chromium/TikTok Studio kích hoạt hiệu ứng Hover trên nút
        user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.04)

        # 3. Nhấn chuột trái (Mouse Down)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(max(0.08, hold_time))

        # 4. Nhả chuột trái (Mouse Up)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.04)

    def start_coordinate_calibration(self) -> None:
        """Kích hoạt tiến trình bắt tọa độ 3 bước tương tác (CHỈ nhận diện bằng Phím F8)."""
        if not user32:
            self.log("ERROR", "❌ Không hỗ trợ bắt tọa độ trên hệ thống này.")
            return

        if self.is_calibrating:
            self.log("WARNING", "⚠️ Đang trong tiến trình bắt tọa độ. Hãy rê chuột vào nút và nhấn Phím F8...")
            return

        self.is_calibrating = True

        def _calib_worker() -> None:
            try:
                self.log("ACTION", "🎯 [Bắt Tọa Độ An Toàn] BẮT ĐẦU HIỆU CHỈNH 3 BƯỚC.")
                self.log("TIP", "💡 Hãy rê chuột đến vị trí từng nút trên TikTok Live Studio và nhấn PHÍM F8!")
                self.log("INFO", "👉 [Bước 1/3]: Rê chuột vào Nút Đếm Giờ / Nút Live -> Nhấn Phím F8.")
                self.emit_event({
                    "type": "CALIBRATION_STEP_PROMPT",
                    "step": 1,
                    "total_steps": 3,
                    "title": "Bước 1: Nút Thời Gian Live",
                    "guide": "Rê chuột vào nút đếm thời gian Live trên TikTok Live Studio -> Nhấn Phím F8.",
                })

                steps_data = []

                # Đợi nhả phím F8 nếu người dùng vừa nhấn
                while user32 and (user32.GetAsyncKeyState(VK_F8) & 0x8000):
                    time.sleep(0.05)
                time.sleep(0.2)

                last_pos_emit = 0.0

                for step_idx, step_desc in enumerate([
                    "Nút Đếm Thời Gian Live (hoặc nút Live)",
                    "Nút 'Kết Thúc LIVE' (trên menu popup)",
                    "Nút 'Xác Nhận / Dừng' (trên hộp thoại xác nhận)",
                ], start=1):
                    if not self.is_calibrating:
                        self.log("INFO", "🛑 [Bắt Tọa Độ] Đã hủy chế độ bắt tọa độ.")
                        return

                    captured = False
                    trigger_type = "Phím F8"
                    click_pos = (0, 0)

                    while self.is_calibrating and not captured:
                        # Broadcast tọa độ chuột hiện tại theo thời gian thực (50ms)
                        now = time.time()
                        cur_x, cur_y = self.get_cursor_pos()
                        if now - last_pos_emit > 0.06:
                            last_pos_emit = now
                            self.emit_event({
                                "type": "CALIBRATION_REALTIME_POS",
                                "x": cur_x,
                                "y": cur_y,
                                "step": step_idx,
                            })

                        # CHỈ NHẬN DIỆN BẰNG PHÍM F8
                        if user32.GetAsyncKeyState(VK_F8) & 0x8000:
                            click_pos = (cur_x, cur_y)
                            captured = True
                            trigger_type = "Phím F8"
                            while user32.GetAsyncKeyState(VK_F8) & 0x8000:
                                time.sleep(0.03)
                            break

                        time.sleep(0.02)

                    if not self.is_calibrating:
                        return

                    # Tìm cửa sổ TikTok LIVE Studio tại thời điểm bắt để tính relative offset
                    hwnd = self.find_tiktok_live_studio_window()
                    win_rect = {"left": 0, "top": 0, "width": 0, "height": 0}
                    rel_x, rel_y = click_pos[0], click_pos[1]

                    if hwnd:
                        rect = RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        win_rect = {
                            "left": rect.left,
                            "top": rect.top,
                            "width": rect.right - rect.left,
                            "height": rect.bottom - rect.top,
                        }
                        rel_x = click_pos[0] - rect.left
                        rel_y = click_pos[1] - rect.top

                    step_info = {
                        "step": step_idx,
                        "desc": step_desc,
                        "trigger": trigger_type,
                        "abs_x": click_pos[0],
                        "abs_y": click_pos[1],
                        "rel_x": rel_x,
                        "rel_y": rel_y,
                        "window_rect": win_rect,
                    }
                    steps_data.append(step_info)

                    self.log(
                        "SUCCESS",
                        f"✅ [Bước {step_idx}/3 - Phím F8] Đã chụp tọa độ: ({click_pos[0]}, {click_pos[1]}) - Offset cửa sổ: (+{rel_x}, +{rel_y}).",
                    )
                    self.emit_event({
                        "type": "CALIBRATION_STEP_SAVED",
                        "step": step_idx,
                        "total_steps": 3,
                        "coords": step_info,
                    })

                    # Nếu chưa phải bước cuối, thông báo bước tiếp theo
                    if step_idx == 1:
                        self.log("INFO", "👉 [Bước 2/3]: Rê chuột vào vị trí nút 'Kết Thúc LIVE' -> Nhấn Phím F8.")
                        self.emit_event({
                            "type": "CALIBRATION_STEP_PROMPT",
                            "step": 2,
                            "total_steps": 3,
                            "title": "Bước 2: Nút 'Kết Thúc LIVE'",
                            "guide": "Rê chuột vào vị trí nút 'Kết Thúc LIVE' -> Nhấn Phím F8.",
                        })
                    elif step_idx == 2:
                        self.log("INFO", "👉 [Bước 3/3]: Rê chuột vào vị trí nút 'Xác Nhận / Dừng' (màu đỏ) -> Nhấn Phím F8.")
                        self.emit_event({
                            "type": "CALIBRATION_STEP_PROMPT",
                            "step": 3,
                            "total_steps": 3,
                            "title": "Bước 3: Nút 'Xác Nhận Dừng'",
                            "guide": "Rê chuột vào vị trí nút 'Xác Nhận' -> Nhấn Phím F8 để hoàn tất.",
                        })

                    time.sleep(0.35)

                # Lưu toàn bộ 3 bước vào cấu hình kèm window_rect
                win_rect_root = steps_data[0].get("window_rect", {}) if steps_data else {}
                calib_payload = {
                    "is_calibrated": True,
                    "timestamp": time.time(),
                    "win_rect": win_rect_root,
                    "steps": steps_data,
                    "p1": {"abs_x": steps_data[0]["abs_x"], "abs_y": steps_data[0]["abs_y"], "rel_x": steps_data[0]["rel_x"], "rel_y": steps_data[0]["rel_y"]},
                    "p2": {"abs_x": steps_data[1]["abs_x"], "abs_y": steps_data[1]["abs_y"], "rel_x": steps_data[1]["rel_x"], "rel_y": steps_data[1]["rel_y"]},
                    "p3": {"abs_x": steps_data[2]["abs_x"], "abs_y": steps_data[2]["abs_y"], "rel_x": steps_data[2]["rel_x"], "rel_y": steps_data[2]["rel_y"]},
                }
                self.save_custom_coordinates(calib_payload)

                self.log("SUCCESS", "🎉 [Hoàn Tất] ĐÃ LƯU BỘ 3 TỌA ĐỘ AN TOÀN THÀNH CÔNG VÀ CHUẨN XÁC 100%!")
                self.emit_event({
                    "type": "CALIBRATION_COMPLETED",
                    "success": True,
                    "data": calib_payload,
                })

            except Exception as e:
                self.log("ERROR", f"❌ Lỗi trong quá trình bắt tọa độ: {e}")
                logger.error("calibration_worker_exception", error=str(e))
            finally:
                self.is_calibrating = False

        self._calibration_thread = threading.Thread(target=_calib_worker, daemon=True)
        self._calibration_thread.start()

    def cancel_coordinate_calibration(self) -> None:
        """Hủy tiến trình bắt tọa độ."""
        self.is_calibrating = False
        self.log("INFO", "🛑 Đã hủy chế độ bắt tọa độ.")
        self.emit_event({"type": "CALIBRATION_CANCELLED"})

    def stop_live_stream_now(self) -> bool:
        """Thực hiện toàn bộ quy trình click tắt livestream trên TikTok LIVE Studio (Hỗ trợ tọa độ Calibrate)."""
        if not user32:
            self.log("ERROR", "❌ Không thể điều khiển Windows API trên hệ điều hành này.")
            return False

        if self.is_busy:
            self.log("WARNING", "⚠️ Đang trong quá trình tắt livestream, vui lòng chờ...")
            return False

        self.is_busy = True
        try:
            self.log("ACTION", "🔍 [Live Studio] Đang tìm kiếm cửa sổ TikTok LIVE Studio...")
            hwnd = self.find_tiktok_live_studio_window()

            if not hwnd:
                self.log("ERROR", "❌ [Live Studio] Không tìm thấy cửa sổ TikTok LIVE Studio đang mở! Hãy chắc chắn bạn đã bật TikTok LIVE Studio.")
                return False

            # Đưa cửa sổ TikTok LIVE Studio lên Foreground với cơ chế vượt Lockout
            self.force_foreground_window(hwnd)

            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top

            if w < 300 or h < 200:
                self.log("ERROR", f"❌ Kích thước cửa sổ TikTok LIVE Studio quá nhỏ ({w}x{h}), không thể xác định vị trí.")
                return False

            self.log("INFO", f"🖥️ [Live Studio] Đã kích hoạt cửa sổ (Kích thước: {w}x{h}, Tọa độ: X:{rect.left}, Y:{rect.top})")

            # Lưu lại vị trí chuột ban đầu của người dùng
            orig_x, orig_y = self.get_cursor_pos()

            # KIỂM TRA XEM ĐÃ CÓ BỘ TỌA ĐỘ HIỆU CHỈNH CHƯA
            calib = self.custom_points
            if calib and calib.get("is_calibrated") and "p1" in calib and "p2" in calib and "p3" in calib:
                self.log("INFO", "🎯 [Live Studio] Sử dụng BỘ TỌA ĐỘ ĐÃ HIỆU CHỈNH của người dùng (Chính xác 100%).")

                saved_rect = calib.get("win_rect") or (calib.get("steps", [{}])[0].get("window_rect", {}) if calib.get("steps") else {})
                if saved_rect and saved_rect.get("left") is not None and saved_rect.get("top") is not None and saved_rect.get("width", 0) > 0:
                    delta_x = rect.left - int(saved_rect.get("left", rect.left))
                    delta_y = rect.top - int(saved_rect.get("top", rect.top))
                    p1_x = int(calib["p1"]["abs_x"]) + delta_x
                    p1_y = int(calib["p1"]["abs_y"]) + delta_y
                    p2_x = int(calib["p2"]["abs_x"]) + delta_x
                    p2_y = int(calib["p2"]["abs_y"]) + delta_y
                    p3_x = int(calib["p3"]["abs_x"]) + delta_x
                    p3_y = int(calib["p3"]["abs_y"]) + delta_y
                else:
                    p1_x = rect.left + int(calib["p1"].get("rel_x", calib["p1"].get("abs_x", 0)))
                    p1_y = rect.top + int(calib["p1"].get("rel_y", calib["p1"].get("abs_y", 0)))
                    p2_x = rect.left + int(calib["p2"].get("rel_x", calib["p2"].get("abs_x", 0)))
                    p2_y = rect.top + int(calib["p2"].get("rel_y", calib["p2"].get("abs_y", 0)))
                    p3_x = rect.left + int(calib["p3"].get("rel_x", calib["p3"].get("abs_x", 0)))
                    p3_y = rect.top + int(calib["p3"].get("rel_y", calib["p3"].get("abs_y", 0)))
            else:
                self.log("INFO", "📐 [Live Studio] Chưa hiệu chỉnh tọa độ riêng -> Sử dụng thuật toán tính toán tự động.")
                # Tọa độ mặc định theo tỉ lệ cửa sổ TikTok Studio
                p1_x = rect.left + int(w * 0.90)  # Góc dưới phải
                p1_y = rect.top + int(h * 0.92)

                p2_x = rect.left + int(w * 0.88)
                p2_y = rect.top + int(h * 0.83)

                p3_x = rect.left + int(w * 0.54)
                p3_y = rect.top + int(h * 0.58)

            # -------------------------------------------------------------
            # BƯỚC 1: Click vào Nút Báo Thời Gian Live
            # -------------------------------------------------------------
            self.log("ACTION", f"🖱️ [Bước 1/3] Click Nút Thời Gian Live tại ({p1_x}, {p1_y})...")
            self.smooth_move(orig_x, orig_y, p1_x, p1_y, duration=0.2)
            self.click_at(p1_x, p1_y, hold_time=0.12)

            # Chờ 650ms để menu popup bung ra hoàn toàn
            time.sleep(0.65)

            # -------------------------------------------------------------
            # BƯỚC 2: Click vào Lựa Chọn "Kết Thúc LIVE"
            # -------------------------------------------------------------
            self.log("ACTION", f"🖱️ [Bước 2/3] Click lựa chọn 'Kết Thúc LIVE' tại ({p2_x}, {p2_y})...")
            self.smooth_move(p1_x, p1_y, p2_x, p2_y, duration=0.18)
            self.click_at(p2_x, p2_y, hold_time=0.12)

            # Chờ 750ms để Modal xác nhận hiện ra
            time.sleep(0.75)

            # -------------------------------------------------------------
            # BƯỚC 3: Click vào Nút "Xác Nhận Kết Thúc" trên Modal Popup
            # -------------------------------------------------------------
            self.log("ACTION", f"🖱️ [Bước 3/3] Click nút 'Xác nhận Kết thúc' tại ({p3_x}, {p3_y})...")
            self.smooth_move(p2_x, p2_y, p3_x, p3_y, duration=0.18)
            self.click_at(p3_x, p3_y, hold_time=0.12)

            time.sleep(0.35)

            # Khôi phục lại vị trí chuột ban đầu cho người dùng
            self.smooth_move(p3_x, p3_y, orig_x, orig_y, duration=0.2)

            self.log("SUCCESS", "🛑 [Live Studio] ĐÃ TỰ ĐỘNG TẮT LIVESTREAM TRÊN TIKTOK LIVE STUDIO THÀNH CÔNG VÀ AN TOÀN!")
            return True

        except Exception as e:
            self.log("ERROR", f"❌ Ngoại lệ khi tự động tắt Live Studio: {e}")
            logger.error("stop_live_studio_exception", error=str(e))
            return False
        finally:
            self.is_busy = False

    def trigger_async_stop_live(self) -> None:
        """Chạy quy trình tắt live trong một luồng riêng để không chặn WebSocket."""
        t = threading.Thread(target=self.stop_live_stream_now, daemon=True)
        t.start()

