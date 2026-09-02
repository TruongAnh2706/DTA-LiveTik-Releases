"""Session state machine implementing 13 states transition logic."""

from dta_autolive.domain.models import SessionState


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current_state: SessionState, target_state: SessionState) -> None:
        super().__init__(
            f"Invalid state transition from {current_state.value} to {target_state.value}"
        )
        self.current_state = current_state
        self.target_state = target_state


class SessionStateMachine:
    """State machine managing 13 session lifecycle states."""

    # Explicit allowed state transitions lookup table
    _ALLOWED_TRANSITIONS: dict[SessionState, set[SessionState]] = {
        SessionState.IDLE: {SessionState.VALIDATING, SessionState.STOPPING, SessionState.FAILED},
        SessionState.VALIDATING: {
            SessionState.PREPARING_DEVICES,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.PREPARING_DEVICES: {
            SessionState.LOADING_MEDIA,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.LOADING_MEDIA: {
            SessionState.READY,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.READY: {SessionState.RUNNING, SessionState.STOPPING, SessionState.FAILED},
        SessionState.RUNNING: {
            SessionState.PAUSED,
            SessionState.SEEKING,
            SessionState.SWITCHING_ITEM,
            SessionState.RECOVERING,
            SessionState.STOPPING,
            SessionState.COMPLETED,
            SessionState.FAILED,
        },
        SessionState.PAUSED: {
            SessionState.RUNNING,
            SessionState.SEEKING,
            SessionState.STOPPING,
            SessionState.FAILED,
        },
        SessionState.SEEKING: {
            SessionState.RUNNING,
            SessionState.PAUSED,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.SWITCHING_ITEM: {
            SessionState.LOADING_MEDIA,
            SessionState.RUNNING,
            SessionState.COMPLETED,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.RECOVERING: {
            SessionState.RUNNING,
            SessionState.PAUSED,
            SessionState.FAILED,
            SessionState.STOPPING,
        },
        SessionState.STOPPING: {SessionState.IDLE, SessionState.FAILED},
        SessionState.COMPLETED: {SessionState.IDLE},
        SessionState.FAILED: {SessionState.IDLE},
    }

    def __init__(self, initial_state: SessionState = SessionState.IDLE) -> None:
        self._current_state = initial_state

    @property
    def current_state(self) -> SessionState:
        """Get the current session state."""
        return self._current_state

    def transition_to(self, target_state: SessionState) -> None:
        """Attempt to transition to a target state."""
        allowed = self._ALLOWED_TRANSITIONS.get(self._current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(self._current_state, target_state)
        self._current_state = target_state

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self._current_state = SessionState.IDLE
