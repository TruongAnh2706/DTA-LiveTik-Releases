"""Dual Clock model implementation: VideoClock & SessionClock."""


class VideoClock:
    """Clock representing current video playback position in milliseconds. Reset for each new video."""

    def __init__(self) -> None:
        self._current_time_ms: int = 0

    @property
    def current_time_ms(self) -> int:
        """Get current video time in milliseconds."""
        return self._current_time_ms

    def update_position(self, position_ms: int) -> None:
        """Update video clock position."""
        self._current_time_ms = max(0, position_ms)

    def reset(self) -> None:
        """Reset video clock to 0 for a new video."""
        self._current_time_ms = 0


class SessionClock:
    """Clock representing cumulative live session duration in milliseconds. Never resets on loop or video change."""

    def __init__(self) -> None:
        self._accumulated_ms: int = 0
        self._paused_ms: int = 0
        self._is_running: bool = False

    @property
    def accumulated_ms(self) -> int:
        """Get total accumulated active session time in milliseconds."""
        return self._accumulated_ms

    @property
    def paused_ms(self) -> int:
        """Get total paused duration in milliseconds."""
        return self._paused_ms

    def start(self) -> None:
        """Start or resume session clock."""
        self._is_running = True

    def advance(self) -> None:
        """Advance session clock by delta milliseconds."""
        if self._is_running:
            self._accumulated_ms += 100

    def add_delta(self, delta_ms: int) -> None:
        """Add time delta to session clock."""
        if delta_ms > 0:
            self._accumulated_ms += delta_ms

    def record_pause(self, paused_delta_ms: int) -> None:
        """Record duration spent in paused state."""
        if paused_delta_ms > 0:
            self._paused_ms += paused_delta_ms

    def reset_session(self) -> None:
        """Reset session clock completely (only when starting a brand new live session)."""
        self._accumulated_ms = 0
        self._paused_ms = 0
        self._is_running = False
