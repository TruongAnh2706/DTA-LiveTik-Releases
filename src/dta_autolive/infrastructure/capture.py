import numpy as np
import win32con
import win32gui
import win32ui
from PIL import Image, ImageGrab


def find_tiktok_window(title_keyword="TikTok LIVE Studio", exclude_hwnd=None):
    """
    Tìm handle (hwnd) của cửa sổ TikTok LIVE Studio, loại trừ ứng dụng DTA AutoCaptcha.
    """
    found_hwnd = []

    def enum_windows_callback(h, l):
        if win32gui.IsWindowVisible(h):
            if exclude_hwnd and h == exclude_hwnd:
                return True
            title = win32gui.GetWindowText(h)
            if "dta autocaptcha" in title.lower() or "dta captcha solver" in title.lower():
                return True
            if title_keyword.lower() in title.lower():
                found_hwnd.append(h)
        return True

    win32gui.EnumWindows(enum_windows_callback, None)
    return found_hwnd[0] if found_hwnd else None


def capture_full_app(hwnd):
    """
    Chụp toàn bộ Client Area cửa sổ TikTok LIVE Studio hoàn toàn trong bộ nhớ RAM.
    Tự động xử lý GPU Hardware Acceleration với 3 tầng Fallback:
    1. PrintWindow PW_RENDERFULLCONTENT (cờ = 2)
    2. Screen DC BitBlt
    3. PIL ImageGrab.grab(bbox)
    Trả về: (full_app_img_np, (win_x, win_y, win_w, win_h))
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None, None

    try:
        rect = win32gui.GetWindowRect(hwnd)
        win_x, win_y = rect[0], rect[1]
        win_w, win_h = rect[2] - rect[0], rect[3] - rect[1]

        if win_w <= 0 or win_h <= 0:
            return None, None

        # 1. PrintWindow (PW_RENDERFULLCONTENT = 2)
        wDC = win32gui.GetWindowDC(hwnd)
        if wDC:
            try:
                dcObj = win32ui.CreateDCFromHandle(wDC)
                cDC = dcObj.CreateCompatibleDC()
                dataBitMap = win32ui.CreateBitmap()
                dataBitMap.CreateCompatibleBitmap(dcObj, win_w, win_h)
                cDC.SelectObject(dataBitMap)

                res = win32gui.PrintWindow(hwnd, cDC.GetSafeHdc(), 2)
                if res == 1:
                    bmpinfo = dataBitMap.GetInfo()
                    bmpstr = dataBitMap.GetBitmapBits(True)
                    full_img = Image.frombuffer(
                        "RGB",
                        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                        bmpstr,
                        "raw",
                        "BGRX",
                        0,
                        1,
                    )
                    img_np = np.array(full_img)

                    dcObj.DeleteDC()
                    cDC.DeleteDC()
                    win32gui.ReleaseDC(hwnd, wDC)
                    win32gui.DeleteObject(dataBitMap.GetHandle())

                    if np.mean(img_np) > 2.0:
                        return img_np, (win_x, win_y, win_w, win_h)
                else:
                    dcObj.DeleteDC()
                    cDC.DeleteDC()
                    win32gui.ReleaseDC(hwnd, wDC)
                    win32gui.DeleteObject(dataBitMap.GetHandle())
            except Exception:
                pass

        # 2. Screen DC BitBlt Fallback
        hdesktop = win32gui.GetDC(0)
        if hdesktop:
            try:
                desktopObj = win32ui.CreateDCFromHandle(hdesktop)
                cDC2 = desktopObj.CreateCompatibleDC()
                bm2 = win32ui.CreateBitmap()
                bm2.CreateCompatibleBitmap(desktopObj, win_w, win_h)
                cDC2.SelectObject(bm2)

                cDC2.BitBlt((0, 0), (win_w, win_h), desktopObj, (win_x, win_y), win32con.SRCCOPY)

                bmpinfo2 = bm2.GetInfo()
                bmpstr2 = bm2.GetBitmapBits(True)
                img2 = Image.frombuffer(
                    "RGB", (bmpinfo2["bmWidth"], bmpinfo2["bmHeight"]), bmpstr2, "raw", "BGRX", 0, 1
                )

                desktopObj.DeleteDC()
                cDC2.DeleteDC()
                win32gui.ReleaseDC(0, hdesktop)
                win32gui.DeleteObject(bm2.GetHandle())

                img_np2 = np.array(img2)
                if np.mean(img_np2) > 2.0:
                    return img_np2, (win_x, win_y, win_w, win_h)
            except Exception:
                pass

        # 3. Robust Fallback: PIL ImageGrab.grab(bbox)
        try:
            bbox = (max(0, win_x), max(0, win_y), win_x + win_w, win_y + win_h)
            grab_img = ImageGrab.grab(bbox=bbox)
            img_np3 = np.array(grab_img)
            if img_np3.size > 0 and np.mean(img_np3) > 2.0:
                return img_np3, (win_x, win_y, win_w, win_h)
        except Exception:
            pass

        return None, None
    except Exception:
        return None, None
