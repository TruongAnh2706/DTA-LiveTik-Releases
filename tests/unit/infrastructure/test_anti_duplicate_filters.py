"""Unit tests for Anti-Duplicate and Studio Grading OpenCV Filters."""

from __future__ import annotations

import numpy as np

from dta_autolive.infrastructure.dta_softcam_engine import DTASoftcamEngine


def test_anti_duplicate_filters_mirror() -> None:
    """Test horizontal mirror flip filter."""
    engine = DTASoftcamEngine(width=100, height=100, fps=30)
    try:
        # Create a frame with asymmetric left/right content
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        test_frame[:, :10] = 255  # Left edge white

        filters = {"flip_mirror": True}
        processed = engine.apply_anti_duplicate_filters(test_frame.copy(), filters, frame_idx=1)

        # After horizontal flip, right edge should now be white
        assert np.mean(processed[:, -10:]) > 200
        assert np.mean(processed[:, :10]) < 50
    finally:
        engine.close()


def test_anti_duplicate_filters_brightness_contrast() -> None:
    """Test studio brightness and contrast adjustments."""
    engine = DTASoftcamEngine(width=100, height=100, fps=30)
    try:
        test_frame = np.full((100, 100, 3), 100, dtype=np.uint8)

        # Increase brightness
        filters = {"flip_mirror": False, "brightness": 120.0, "contrast": 100.0}
        processed = engine.apply_anti_duplicate_filters(test_frame.copy(), filters, frame_idx=1)
        assert np.mean(processed) > np.mean(test_frame)
    finally:
        engine.close()


def test_anti_duplicate_filters_dynamic_breathing() -> None:
    """Test dynamic breathing micro-zoom evasion."""
    engine = DTASoftcamEngine(width=100, height=100, fps=30)
    try:
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        test_frame[40:60, 40:60] = 200  # Central square

        filters = {"flip_mirror": False, "zoom": 102.0, "dynamic_breathing": True}
        processed_frame1 = engine.apply_anti_duplicate_filters(test_frame.copy(), filters, frame_idx=1)
        processed_frame2 = engine.apply_anti_duplicate_filters(test_frame.copy(), filters, frame_idx=90)

        assert processed_frame1.shape == (100, 100, 3)
        assert processed_frame2.shape == (100, 100, 3)
    finally:
        engine.close()
