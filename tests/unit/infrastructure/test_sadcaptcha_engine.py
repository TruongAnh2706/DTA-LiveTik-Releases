from unittest.mock import MagicMock, patch

import numpy as np

from dta_autolive.infrastructure.sadcaptcha_engine import (
    CaptchaAutoScannerManager,
    check_sadcaptcha_credits,
    find_captcha_modal,
    has_slider_track,
    is_captcha_visible,
    solve_via_sadcaptcha,
)


def test_has_slider_track_empty():
    assert has_slider_track(None) is False
    assert has_slider_track(np.zeros((50, 50, 3), dtype=np.uint8)) is False


def test_has_slider_track_synthetic():
    img = np.ones((200, 300, 3), dtype=np.uint8) * 255
    # Draw slider track at bottom 25%
    img[160:175, 30:270] = 128
    assert has_slider_track(img) is True


def test_find_captcha_modal_no_img():
    modal_img, rect = find_captcha_modal(None)
    assert modal_img is None
    assert rect is None


def test_is_captcha_visible():
    assert is_captcha_visible(None) is False


@patch("requests.get")
def test_check_sadcaptcha_credits(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"credits": 50}
    mock_get.return_value = mock_resp

    res_credits = check_sadcaptcha_credits("test_key")
    assert res_credits == 50


@patch("requests.post")
def test_solve_via_sadcaptcha(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"slideXProportion": 0.5}
    mock_post.return_value = mock_resp

    sample_img = np.ones((200, 300, 3), dtype=np.uint8) * 255
    offset = solve_via_sadcaptcha(sample_img, "test_api_key")
    assert offset == 150


def test_captcha_scanner_manager_start_stop():
    logs = []
    statuses = []

    manager = CaptchaAutoScannerManager(
        log_callback=lambda tag, msg: logs.append((tag, msg)),
        status_callback=lambda st, _col: statuses.append(st),
    )

    manager.start_scan("dummy_key", interval=1.0)
    assert manager.is_scanning is True
    assert any("Đang quét" in s for s in statuses)

    manager.stop_scan()
    assert manager.is_scanning is False
