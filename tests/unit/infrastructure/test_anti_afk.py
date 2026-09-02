"""Unit tests for DTAAntiAfkSimulator.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import time

from dta_autolive.infrastructure.dta_anti_afk import DTAAntiAfkSimulator


def test_anti_afk_start_stop_lifecycle() -> None:
    logs = []
    sim = DTAAntiAfkSimulator(log_callback=lambda lvl, msg: logs.append((lvl, msg)))

    assert not sim.is_running
    sim.start()
    assert sim.is_running
    assert any("KÍCH HOẠT" in msg for _, msg in logs)

    # Trigger interaction cycle once
    sim.simulate_micro_activity()
    assert any("Anti-AFK" in msg for _, msg in logs)

    time.sleep(0.1)
    sim.stop()
    assert not sim.is_running


def test_anti_afk_cursor_helpers_and_smooth_move() -> None:
    sim = DTAAntiAfkSimulator()
    pos = sim.get_cursor_pos()
    assert isinstance(pos, tuple)
    assert len(pos) == 2

    # Test smooth move execution
    sim.smooth_move(pos[0], pos[1], pos[0], pos[1], duration=0.05)

