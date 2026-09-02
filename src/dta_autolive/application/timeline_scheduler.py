"""Timeline Scheduler evaluating JSON events against Video Clock with resilient reconnect backlog handling."""

import structlog

from dta_autolive.domain.clocks import VideoClock
from dta_autolive.domain.models import EventState, TimelineEvent, TimelineScript

logger = structlog.get_logger()


class TimelineScheduler:
    """Evaluates Timeline Script events and schedules dispatch based on Video Clock."""

    def __init__(self) -> None:
        self._current_script: TimelineScript | None = None
        self._active_product_id: str | None = None
        self._pending_queue: list[TimelineEvent] = []

    @property
    def active_product_id(self) -> str | None:
        """Get the currently active product ID (One Active Product Invariant)."""
        return self._active_product_id

    def load_script(self, script: TimelineScript) -> None:
        """Load a new Video JSON script and prepare event queue."""
        self._current_script = script
        # Clone events so we don't mutate original fixture
        self._pending_queue = [evt.model_copy(deep=True) for evt in script.timeline_events]
        logger.info(
            "timeline_script_loaded",
            script_id=script.script_id,
            event_count=len(self._pending_queue),
        )

    def evaluate(self, video_clock: VideoClock, is_bridge_connected: bool) -> list[TimelineEvent]:
        """Evaluate pending events against current video time and bridge status.

        Returns list of events ready to be dispatched immediately.
        """
        if not self._current_script or not self._pending_queue:
            return []

        current_time_ms = video_clock.current_time_ms
        ready_events: list[TimelineEvent] = []

        for evt in list(self._pending_queue):
            if evt.state == EventState.PENDING and current_time_ms >= evt.time_ms:
                # Check if event has expired based on valid_for_ms
                if current_time_ms > (evt.time_ms + evt.valid_for_ms):
                    evt.state = EventState.EXPIRED
                    self._pending_queue.remove(evt)
                    logger.info("event_expired", event_id=evt.event_id, time_ms=evt.time_ms)
                    continue

                if is_bridge_connected:
                    evt.state = EventState.DISPATCHED
                    ready_events.append(evt)
                    self._pending_queue.remove(evt)
                else:
                    logger.debug("event_held_bridge_disconnected", event_id=evt.event_id)

        return ready_events

    def process_reconnect_backlog(self, current_video_time_ms: int) -> TimelineEvent | None:
        """Resilient Backlog Policy on Extension Reconnect: Select ONLY the newest valid event, skip/expire older events.

        Never spam or replay multiple old product pin events.
        """
        if not self._pending_queue:
            return None

        due_events: list[TimelineEvent] = []

        # Find all pending events whose time_ms has passed
        for evt in list(self._pending_queue):
            if evt.state == EventState.PENDING and current_video_time_ms >= evt.time_ms:
                due_events.append(evt)

        if not due_events:
            return None

        # Filter out expired events
        valid_due_events = [
            evt for evt in due_events if current_video_time_ms <= (evt.time_ms + evt.valid_for_ms)
        ]

        # Expire older invalid due events
        for evt in due_events:
            if evt not in valid_due_events:
                evt.state = EventState.EXPIRED
                if evt in self._pending_queue:
                    self._pending_queue.remove(evt)

        if not valid_due_events:
            return None

        # Select the single latest valid event (sorted by time_ms)
        valid_due_events.sort(key=lambda x: x.time_ms)
        newest_event = valid_due_events[-1]

        # Mark older valid due events as SKIPPED
        for evt in valid_due_events[:-1]:
            evt.state = EventState.SKIPPED
            if evt in self._pending_queue:
                self._pending_queue.remove(evt)
            logger.info("older_backlog_event_skipped", event_id=evt.event_id)

        # Dispatch the newest event
        newest_event.state = EventState.DISPATCHED
        if newest_event in self._pending_queue:
            self._pending_queue.remove(newest_event)

        logger.info("reconnect_selected_newest_event", event_id=newest_event.event_id)
        return newest_event

    def update_event_state(
        self, event_id: str, new_state: EventState, product_id: str | None = None
    ) -> None:
        """Update event lifecycle state upon receiving Extension ACK."""
        if new_state == EventState.ACKNOWLEDGED and product_id:
            # Enforce One Active Product Invariant
            self._active_product_id = product_id
            logger.info("active_product_updated", product_id=product_id)
