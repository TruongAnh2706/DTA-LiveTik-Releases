"""SadCaptcha Cloud API & Template Solver Engine for DTA AutoLive v1.2.

Integrates SadCaptcha credits verification, slider track verification, and TikTok Live Studio background scanning.
"""

import base64
import threading
import time
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np
import requests
import structlog

from dta_autolive.infrastructure.capture import capture_full_app, find_tiktok_window
from dta_autolive.infrastructure.mouse_automation import execute_win32_drag

logger = structlog.get_logger()

SADCAPTCHA_BASE_URL = "https://www.sadcaptcha.com/api/v1"


def check_sadcaptcha_credits(api_key: str) -> int | None:
    """Check remaining SadCaptcha Credits via OpenAPI spec endpoint.

    GET https://www.sadcaptcha.com/api/v1/license/credits?licenseKey={key}
    """
    if not api_key or not api_key.strip():
        return None
    try:
        url = f"{SADCAPTCHA_BASE_URL}/license/credits?licenseKey={api_key.strip()}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return int(data.get("credits", 0))
    except Exception as e:
        logger.warning("check_sadcaptcha_credits_error", error=str(e))
    return None


def has_slider_track(modal_img: np.ndarray) -> bool:
    """Kiểm tra xem một khung ảnh có chứa Thanh Trượt Slider Captcha thật hay không.

    Bằng cách kiểm tra 30% vùng đáy của Modal xem có thanh track trượt xám/nút trượt hay không.
    Giúp loại bỏ 100% các ô thẻ trắng thông thường của TikTok LIVE Studio.
    """
    if modal_img is None or modal_img.size == 0:
        return False

    mh, mw, _ = modal_img.shape
    if mh < 100 or mw < 150:
        return False

    bottom_crop = modal_img[int(mh * 0.70) : mh, 0 : mw]
    bh, bw, _ = bottom_crop.shape

    if bh < 10 or bw < 50:
        return False

    gray_bottom = cv2.cvtColor(bottom_crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_bottom, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w >= int(mw * 0.50) and 10 <= h <= 60:
            return True
        if 20 <= w <= 70 and 20 <= h <= 70 and abs(w - h) < 20:
            return True

    return False


def find_captcha_modal(full_app_img: np.ndarray) -> tuple[np.ndarray | None, tuple[int, int, int, int] | None]:
    """Tự động quét và khoét Khung Captcha Modal thực sự (Có chứa thanh trượt Slider).

    Loại bỏ 100% các ô thẻ trắng thông thường của giao diện TikTok LIVE Studio.
    Trả về: (captcha_modal_img, (modal_x, modal_y, modal_w, modal_h)) hoặc (None, None)
    """
    if full_app_img is None or full_app_img.size == 0:
        return None, None

    try:
        h, w, _ = full_app_img.shape

        lower_white = np.array([225, 225, 225], dtype=np.uint8)
        upper_white = np.array([255, 255, 255], dtype=np.uint8)
        white_mask = cv2.inRange(full_app_img, lower_white, upper_white)

        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_modals = []
        if contours:
            for c in contours:
                bx, by, bw, bh = cv2.boundingRect(c)
                if 200 <= bw <= 520 and 140 <= bh <= 440:
                    aspect_ratio = bw / float(bh)
                    if 0.95 <= aspect_ratio <= 1.65:
                        candidate_img = full_app_img[by : by + bh, bx : bx + bw]
                        if has_slider_track(candidate_img):
                            center_dist = abs((bx + bw // 2) - w // 2) + abs((by + bh // 2) - h // 2)
                            valid_modals.append((center_dist, bx, by, bw, bh, candidate_img))

        if valid_modals:
            valid_modals.sort(key=lambda x: x[0])
            _, mx, my, mw, mh, m_img = valid_modals[0]
            return m_img, (mx, my, mw, mh)

        return None, None
    except Exception as e:
        logger.error("find_captcha_modal_error", error=str(e))
        return None, None


def is_captcha_visible(full_app_img: np.ndarray) -> bool:
    """Kiểm tra xem Captcha Modal thật có đang xuất hiện trên màn hình hay không."""
    modal_img, _ = find_captcha_modal(full_app_img)
    return modal_img is not None


def solve_via_sadcaptcha(captcha_modal_img_np: np.ndarray, api_key: str) -> int:
    """Solve TikTok Slider Captcha via SadCaptcha Cloud API."""
    if not api_key or not api_key.strip():
        raise ValueError("Chưa nhập SadCaptcha API Key!")

    clean_key = api_key.strip()
    success, buffer = cv2.imencode(".jpg", captcha_modal_img_np)
    if not success:
        raise ValueError("Không thể nén khung Captcha sang JPEG!")

    base64_image = base64.b64encode(buffer.tobytes()).decode("utf-8")

    # Gửi API REST trực tiếp chuẩn OpenAPI Spec 1.1.0
    url = f"{SADCAPTCHA_BASE_URL}/puzzle?licenseKey={clean_key}"
    payload = {"puzzleImageB64": base64_image, "pieceImageB64": base64_image}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if "slideXProportion" in data:
            proportion = float(data["slideXProportion"])
            _, modal_w, _ = captcha_modal_img_np.shape
            return int(proportion * modal_w)
        if "slide_x" in data:
            return int(data["slide_x"])
        if "offset_x" in data:
            return int(data["offset_x"])
        raise RuntimeError(f"SadCaptcha response format: {data}")

    raise RuntimeError(f"SadCaptcha API HTTP {response.status_code}: {response.text}")


class CaptchaAutoScannerManager:
    """Quản lý luồng quét và giải Captcha tự động cho TikTok LIVE Studio."""

    def __init__(
        self,
        log_callback: Callable[[str, str], None] | None = None,
        status_callback: Callable[[str, str], None] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.event_callback = event_callback
        self.is_scanning = False
        self.is_solving = False
        self.worker_thread: threading.Thread | None = None
        self.api_key = ""
        self.scan_interval = 2.0

    def log(self, tag: str, text: str) -> None:
        if self.log_callback:
            self.log_callback(tag, text)

    def set_status(self, text: str, color: str = "#00FF66") -> None:
        if self.status_callback:
            self.status_callback(text, color)

    def start_scan(self, api_key: str, interval: float = 2.0) -> None:
        if self.is_scanning:
            self.log("WARNING", "⚠️ Tiến trình quét Captcha đang hoạt động!")
            return

        self.api_key = api_key.strip()
        self.scan_interval = max(1.0, float(interval))
        self.is_scanning = True

        self.set_status("● Đang quét Captcha", "#00FF66")
        self.log("INFO", "🧩 Kích hoạt chế độ Tự Động Quét & Giải Captcha TikTok LIVE Studio (SadCaptcha Engine).")
        self.worker_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.worker_thread.start()

    def stop_scan(self) -> None:
        if self.is_scanning:
            self.is_scanning = False
            self.set_status("Đã dừng quét", "#FFCC00")
            self.log("INFO", "🛑 Đã dừng quét Captcha.")

    def solve_manual(self, api_key: str) -> bool:
        """Giải thử 1 lần ngay lập tức để kiểm tra."""
        key = api_key.strip() or self.api_key
        if not key:
            self.log("ERROR", "❌ Chưa cấu hình SadCaptcha API Key!")
            return False

        self.log("INFO", "⚡ Đang tìm cửa sổ TikTok LIVE Studio và quét Captcha thủ công...")
        return self._do_solve(key, is_manual=True)

    def _do_solve(self, api_key: str, is_manual: bool = False) -> bool:
        if self.is_solving:
            return False

        self.is_solving = True
        success = False
        try:
            hwnd = find_tiktok_window("TikTok LIVE Studio")
            if not hwnd:
                if is_manual:
                    self.log("WARNING", "⚠️ Không tìm thấy cửa sổ TikTok LIVE Studio đang mở trên màn hình!")
                return False

            full_app_img, _ = capture_full_app(hwnd)
            if full_app_img is None:
                if is_manual:
                    self.log("ERROR", "❌ Không thể chụp ảnh cửa sổ TikTok LIVE Studio!")
                return False

            modal_img, modal_rect = find_captcha_modal(full_app_img)
            if modal_img is None or modal_rect is None:
                if is_manual:
                    self.log("WARNING", "⚠️ Không phát hiện Khung Captcha Slider trong cửa sổ TikTok LIVE Studio.")
                return False

            self.set_status("🟡 Đang giải Captcha...", "#FFFF00")
            self.log("INFO", "⚡ Phát hiện Captcha Slider! Đang gửi ảnh sang SadCaptcha Solver...")

            mx, my, mw, mh = modal_rect
            drag_x = solve_via_sadcaptcha(modal_img, api_key)
            if drag_x > 0:
                self.log("SUCCESS", f"✅ SadCaptcha giải thành công! Khoảng cách kéo slider: {drag_x}px")
                self.log("ACTION", f"🖱️ Đang thực hiện thao tác kéo Win32 (Cửa sổ: {hwnd}, Modal: {modal_rect})...")
                ok = execute_win32_drag(hwnd, mx, my, mw, mh, drag_x)
                if ok:
                    self.log("SUCCESS", "🎉 Đã kéo trượt Captcha thành công 100%!")
                    self.set_status("🟢 Đã giải Captcha xong", "#00FF66")
                    if self.event_callback:
                        self.event_callback({"type": "CAPTCHA_SOLVED", "drag_x": drag_x, "success": True})
                    time.sleep(1.5)
                    success = True
                else:
                    self.log("ERROR", "❌ Lỗi khi gửi sự kiện kéo chuột Win32!")
            else:
                self.log("ERROR", "❌ SadCaptcha trả về tọa độ không hợp lệ!")

        except Exception as err:
            self.log("ERROR", f"❌ Lỗi xử lý Captcha: {err}")
        finally:
            self.is_solving = False
            if self.is_scanning:
                self.set_status("● Đang quét Captcha", "#00FF66")

        return success

    def _scan_loop(self) -> None:
        while self.is_scanning:
            try:
                if self.api_key:
                    hwnd = find_tiktok_window("TikTok LIVE Studio")
                    if hwnd:
                        full_img, _ = capture_full_app(hwnd)
                        if full_img is not None and is_captcha_visible(full_img):
                            self._do_solve(self.api_key, is_manual=False)
            except Exception as e:
                logger.warning("captcha_scanner_tick_error", error=str(e))

            time.sleep(self.scan_interval)

