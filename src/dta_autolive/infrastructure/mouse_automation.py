import time

import pyautogui
import win32api
import win32con
import win32gui

pyautogui.PAUSE = 0.001
pyautogui.FAILSAFE = False


def execute_win32_drag(hwnd_tiktok, modal_x, modal_y, modal_w, modal_h, drag_offset_x):
    """
    Kéo thả Win32 ClientToScreen chính xác cho SadCaptcha API:
    1. Force Focus cửa sổ TikTok LIVE Studio (Bypass rào cản UIPI).
    2. Snap con trỏ chuột đến đúng vị trí Nút Slider Mũi Tên màu trắng (10% left, 88% top).
    3. Nhấn và GIỮ chuột trái 0.12s cho Electron đăng ký trạng thái kéo.
    4. Trượt mượt gia tốc Ease-Out Cubic.
    """
    try:
        # 1. Force Focus TikTok Studio Window (Bypass UIPI restriction)
        if hwnd_tiktok and win32gui.IsWindow(hwnd_tiktok):
            try:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32gui.SetForegroundWindow(hwnd_tiktok)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.12)
            except Exception:
                pass

        # 2. Hardcoded Slider Arrow Button Anchor (10% left, 88% top of modal)
        arrow_local_x = int(modal_w * 0.10)
        arrow_local_y = int(modal_h * 0.88)

        # Convert Client to Absolute Desktop Screen Coordinates
        client_x = modal_x + arrow_local_x
        client_y = modal_y + arrow_local_y
        screen_start_x, screen_start_y = win32gui.ClientToScreen(hwnd_tiktok, (client_x, client_y))
        screen_target_x = int(screen_start_x + drag_offset_x)

        print(
            f"[ACTION] Executing Win32 Drag from Screen ({screen_start_x}, {screen_start_y}) to ({screen_target_x}, {screen_start_y})"
        )

        # 3. Snap Cursor directly onto Slider Arrow Button
        try:
            win32api.SetCursorPos((screen_start_x, screen_start_y))
        except Exception:
            pyautogui.moveTo(screen_start_x, screen_start_y)

        time.sleep(0.15)

        # 4. Hold Left Mouse Button & Interpolate Drag Movement
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        except Exception:
            pyautogui.mouseDown(button="left")

        time.sleep(0.12)

        steps = 30
        for i in range(steps):
            t = (i + 1) / steps
            current_x = int(screen_start_x + (drag_offset_x * (1 - (1 - t) ** 3)))
            try:
                win32api.SetCursorPos((current_x, screen_start_y))
            except Exception:
                pyautogui.moveTo(current_x, screen_start_y)
            time.sleep(0.012)

        time.sleep(0.15)
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pyautogui.mouseUp(button="left")

        time.sleep(0.10)
        return True

    except Exception:
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            pyautogui.mouseUp(button="left")
        except Exception:
            pass
        return True
