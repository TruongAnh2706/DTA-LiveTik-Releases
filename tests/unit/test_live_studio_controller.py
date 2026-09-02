"""Unit tests for DTALiveStudioController (TikTok LIVE Studio Auto-Stop Automation & Calibration).

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from dta_autolive.infrastructure.dta_live_studio_controller import RECT, DTALiveStudioController


def test_live_studio_controller_initialization():
    """Kiểm tra khởi tạo controller với log callback."""
    logs = []
    controller = DTALiveStudioController(log_callback=lambda lvl, msg: logs.append((lvl, msg)))
    assert controller.is_busy is False

    controller.log("INFO", "Test message")
    assert len(logs) == 1
    assert logs[0] == ("INFO", "Test message")


def test_live_studio_controller_stop_live_when_window_not_found():
    """Kiểm tra xử lý an toàn khi không tìm thấy cửa sổ TikTok LIVE Studio."""
    logs = []
    controller = DTALiveStudioController(log_callback=lambda lvl, msg: logs.append((lvl, msg)))

    with patch.object(controller, "find_tiktok_live_studio_window", return_value=None):
        result = controller.stop_live_stream_now()
        assert result is False
        assert any("Không tìm thấy cửa sổ TikTok LIVE Studio" in msg for _, msg in logs)


def test_live_studio_controller_custom_coords_persistence():
    """Kiểm tra lưu trữ, tải và xóa bộ tọa độ hiệu chỉnh 3 bước."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "test_coords.json"
        events = []
        controller = DTALiveStudioController(
            config_file=config_file,
            event_callback=events.append,
        )

        assert controller.custom_points == {}

        sample_coords = {
            "is_calibrated": True,
            "p1": {"abs_x": 1000, "abs_y": 800, "rel_x": 900, "rel_y": 700},
            "p2": {"abs_x": 980, "abs_y": 720, "rel_x": 880, "rel_y": 620},
            "p3": {"abs_x": 500, "abs_y": 500, "rel_x": 400, "rel_y": 400},
        }

        assert controller.save_custom_coordinates(sample_coords) is True
        assert config_file.exists()

        # Khởi tạo instance mới đọc từ file
        new_controller = DTALiveStudioController(config_file=config_file)
        assert new_controller.custom_points["is_calibrated"] is True
        assert new_controller.custom_points["p1"]["rel_x"] == 900

        # Xóa tọa độ
        new_controller.clear_custom_coordinates()
        assert new_controller.custom_points == {}
        assert not config_file.exists()


def test_live_studio_controller_stop_with_calibrated_coords():
    """Kiểm tra quy trình click tắt live sử dụng chính xác bộ tọa độ hiệu chỉnh của người dùng."""
    logs = []
    controller = DTALiveStudioController(log_callback=lambda lvl, msg: logs.append((lvl, msg)))

    # Nạp tọa độ hiệu chỉnh mẫu
    controller.custom_points = {
        "is_calibrated": True,
        "p1": {"abs_x": 1000, "abs_y": 800, "rel_x": 920, "rel_y": 750},
        "p2": {"abs_x": 980, "abs_y": 720, "rel_x": 900, "rel_y": 670},
        "p3": {"abs_x": 500, "abs_y": 500, "rel_x": 520, "rel_y": 460},
    }

    clicked_points = []

    def mock_click_at(x, y, hold_time=0.06):
        clicked_points.append((x, y))

    fake_rect = RECT(left=200, top=100, right=1400, bottom=900)  # w=1200, h=800

    with (
        patch.object(controller, "find_tiktok_live_studio_window", return_value=123456),
        patch("dta_autolive.infrastructure.dta_live_studio_controller.user32") as mock_user32,
        patch.object(controller, "get_cursor_pos", return_value=(300, 300)),
        patch.object(controller, "smooth_move") as mock_move,
        patch.object(controller, "click_at", side_effect=mock_click_at),
        patch("time.sleep", return_value=None),
    ):
        mock_user32.GetWindowRect.side_effect = lambda _hwnd, byref_rect: setattr(
            byref_rect._obj, "left", fake_rect.left  # noqa: SLF001
        ) or setattr(
            byref_rect._obj, "top", fake_rect.top  # noqa: SLF001
        ) or setattr(
            byref_rect._obj, "right", fake_rect.right  # noqa: SLF001
        ) or setattr(
            byref_rect._obj, "bottom", fake_rect.bottom  # noqa: SLF001
        )

        success = controller.stop_live_stream_now()

        assert success is True
        assert len(clicked_points) == 3

        # Điểm 1: 200 + 920 = 1120, 100 + 750 = 850
        # Điểm 2: 200 + 900 = 1100, 100 + 670 = 770
        # Điểm 3: 200 + 520 = 720, 100 + 460 = 560
        assert clicked_points[0] == (1120, 850)
        assert clicked_points[1] == (1100, 770)
        assert clicked_points[2] == (720, 560)

        # Kiểm tra trả lại vị trí chuột ban đầu (300, 300)
        last_move_call = mock_move.call_args_list[-1]
        assert last_move_call[0][2] == 300
        assert last_move_call[0][3] == 300
        assert any("BỘ TỌA ĐỘ ĐÃ HIỆU CHỈNH" in msg for _, msg in logs)


def test_live_studio_controller_cancel_calibration():
    """Kiểm tra hủy chế độ bắt tọa độ."""
    events = []
    controller = DTALiveStudioController(event_callback=events.append)
    controller.is_calibrating = True
    controller.cancel_coordinate_calibration()
    assert controller.is_calibrating is False
    assert any(e.get("type") == "CALIBRATION_CANCELLED" for e in events)

