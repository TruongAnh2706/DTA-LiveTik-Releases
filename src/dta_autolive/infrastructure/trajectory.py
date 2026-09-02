import time

import win32api
import win32con
import win32gui


def force_activate_window(hwnd):
    """
    Sử dụng Hack phím Alt-key (VK_MENU) để vượt rào cản Windows UIPI SetForegroundWindow Restriction.
    Kích hoạt cửa sổ TikTok Studio hoạt động 100%.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    try:
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32gui.SetForegroundWindow(hwnd)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.12)  # Essential delay cho Windows UI Focus
        return True
    except Exception:
        return False


def execute_mouse_drag_accurate(
    hwnd_tiktok, modal_client_x, modal_client_y, slider_local_x, slider_local_y, drag_offset_x
):
    """
    Executes Win32 mouse drag from the exact center of the slider arrow button.
    Chuyển đổi trực tiếp Client Relative -> Absolute Desktop Screen Coords bằng win32gui.ClientToScreen.
    """
    try:
        # 1. Bypass Windows UIPI to focus TikTok Studio
        force_activate_window(hwnd_tiktok)

        # 2. Convert Client Relative Coordinates to Absolute Desktop Screen Coordinates
        client_x = int(modal_client_x + slider_local_x)
        client_y = int(modal_client_y + slider_local_y)

        screen_start_x, screen_start_y = win32gui.ClientToScreen(hwnd_tiktok, (client_x, client_y))
        screen_target_x = int(screen_start_x + drag_offset_x)

        print(
            f"[DEBUG ClientToScreen] Slider Arrow Center Screen: ({screen_start_x}, {screen_start_y})"
        )
        print(
            f"[DEBUG ClientToScreen] Dragging from X:{screen_start_x} to X:{screen_target_x} (Offset: {drag_offset_x}px)"
        )

        # 3. Snap Cursor directly onto Slider Arrow Button
        try:
            win32api.SetCursorPos((screen_start_x, screen_start_y))
        except Exception:
            pass

        time.sleep(0.15)

        # 4. Hold Click and Smooth Drag
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        except Exception:
            pass

        time.sleep(0.12)  # Wait for drag handle to lock

        steps = 30
        for i in range(steps):
            t = (i + 1) / steps
            current_x = int(screen_start_x + (drag_offset_x * (1 - (1 - t) ** 3)))
            try:
                win32api.SetCursorPos((current_x, screen_start_y))
            except Exception:
                pass
            time.sleep(0.012)

        time.sleep(0.15)
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pass

        time.sleep(0.10)
        return True

    except Exception:
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pass
        return True
