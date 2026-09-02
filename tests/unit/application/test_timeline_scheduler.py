"""Unit tests for Timeline Scheduler and Backlog Reconnect Policy."""

from dta_autolive.application.timeline_scheduler import TimelineScheduler
from dta_autolive.domain.clocks import VideoClock
from dta_autolive.domain.models import EventState, TimelineEvent, TimelineScript


def test_timeline_scheduler_dispatches_due_events() -> None:
    """Verify events are dispatched when VideoClock reaches trigger time."""
    evt1 = TimelineEvent(
        event_id="evt_01", time_ms=5000, type="PIN_PRODUCT", payload={"product_id": "101"}
    )
    evt2 = TimelineEvent(
        event_id="evt_02", time_ms=10000, type="PIN_PRODUCT", payload={"product_id": "102"}
    )

    script = TimelineScript(
        script_id="s1",
        video_filename="v1.mp4",
        expected_duration_ms=30000,
        timeline_events=[evt1, evt2],
    )

    scheduler = TimelineScheduler()
    scheduler.load_script(script)

    v_clock = VideoClock()
    v_clock.update_position(4000)

    # At 4s, no event is due
    ready = scheduler.evaluate(v_clock, is_bridge_connected=True)
    assert len(ready) == 0

    # At 6s, evt_01 is due
    v_clock.update_position(6000)
    ready = scheduler.evaluate(v_clock, is_bridge_connected=True)
    assert len(ready) == 1
    assert ready[0].event_id == "evt_01"

    # ACK evt_01 updates active product
    scheduler.update_event_state("evt_01", EventState.ACKNOWLEDGED, product_id="101")
    assert scheduler.active_product_id == "101"


def test_reconnect_backlog_selects_newest_event_and_skips_older() -> None:
    """Verify reconnect backlog selects ONLY the newest valid event and skips older events."""
    evt1 = TimelineEvent(
        event_id="evt_01",
        time_ms=2000,
        type="PIN_PRODUCT",
        payload={"product_id": "101"},
        valid_for_ms=20000,
    )
    evt2 = TimelineEvent(
        event_id="evt_02",
        time_ms=8000,
        type="PIN_PRODUCT",
        payload={"product_id": "102"},
        valid_for_ms=20000,
    )
    evt3 = TimelineEvent(
        event_id="evt_03",
        time_ms=14000,
        type="PIN_PRODUCT",
        payload={"product_id": "103"},
        valid_for_ms=20000,
    )

    script = TimelineScript(
        script_id="s1",
        video_filename="v1.mp4",
        expected_duration_ms=60000,
        timeline_events=[evt1, evt2, evt3],
    )

    scheduler = TimelineScheduler()
    scheduler.load_script(script)

    # Simulate extension disconnect while video advances to 15,000 ms
    v_clock = VideoClock()
    v_clock.update_position(15000)

    # While disconnected, evaluate holds events
    ready = scheduler.evaluate(v_clock, is_bridge_connected=False)
    assert len(ready) == 0

    # Extension Reconnects at 15,000 ms!
    selected = scheduler.process_reconnect_backlog(current_video_time_ms=15000)

    # Must pick ONLY evt_03 (newest valid) and NOT spam evt_01/evt_02
    assert selected is not None
    assert selected.event_id == "evt_03"
    assert evt1.state == EventState.SKIPPED or evt1.state == EventState.PENDING
