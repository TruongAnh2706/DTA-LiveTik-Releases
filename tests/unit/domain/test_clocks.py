"""Unit tests for Dual-Clock Model."""

from dta_autolive.domain.clocks import SessionClock, VideoClock


def test_video_clock_resets() -> None:
    """Verify VideoClock updates and resets to 0."""
    v_clock = VideoClock()
    assert v_clock.current_time_ms == 0

    v_clock.update_position(15400)
    assert v_clock.current_time_ms == 15400

    v_clock.reset()
    assert v_clock.current_time_ms == 0


def test_session_clock_accumulates_across_video_changes() -> None:
    """Verify SessionClock accumulates continuously without resetting when video changes."""
    s_clock = SessionClock()
    s_clock.start()

    # Video 1: 30 seconds (30,000 ms)
    s_clock.add_delta(30000)
    assert s_clock.accumulated_ms == 30000

    # Switch to Video 2 (VideoClock resets, SessionClock keeps accumulating)
    v_clock = VideoClock()
    v_clock.reset()
    s_clock.add_delta(45000)

    # Session clock total = 75,000 ms
    assert s_clock.accumulated_ms == 75000


def test_session_clock_records_paused_duration() -> None:
    """Verify SessionClock tracks paused duration separately."""
    s_clock = SessionClock()
    s_clock.start()
    s_clock.add_delta(10000)

    s_clock.record_pause(5000)
    assert s_clock.accumulated_ms == 10000
    assert s_clock.paused_ms == 5000
