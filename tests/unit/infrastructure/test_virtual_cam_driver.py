"""Unit tests for DTASoftcamEngine Virtual Camera Driver integration."""

import numpy as np

from dta_autolive.infrastructure.dta_softcam_engine import DTASoftcamEngine


def test_dta_softcam_engine_init() -> None:
    """Test initialization of DTASoftcamEngine with system Virtual Camera driver."""
    engine = DTASoftcamEngine(width=1080, height=1920, fps=30)
    assert engine.width == 1080
    assert engine.height == 1920
    assert engine.fps == 30
    engine.close()


def test_dta_softcam_engine_send_bgr_frame() -> None:
    """Test sending BGR24 numpy frame to Virtual Camera."""
    engine = DTASoftcamEngine(width=640, height=480, fps=30)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Color one pixel
    frame[0, 0] = [255, 0, 0]
    engine.send_bgr_frame(frame)
    assert engine.frame_counter >= 1
    engine.close()


def test_dta_softcam_engine_send_black_frame() -> None:
    """Test sending blank black frame."""
    engine = DTASoftcamEngine(width=640, height=480, fps=30)
    engine.send_black_frame()
    assert engine.frame_counter >= 1
    engine.close()


def test_dta_softcam_engine_send_standby_frame() -> None:
    """Test generating and sending DTA Standby Frame."""
    engine = DTASoftcamEngine(width=1080, height=1920, fps=30)
    engine.send_standby_frame()
    assert engine.frame_counter >= 1
    engine.close()
