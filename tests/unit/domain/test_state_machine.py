"""Unit tests for Session State Machine."""

import pytest

from dta_autolive.domain.models import SessionState
from dta_autolive.domain.state_machine import InvalidStateTransitionError, SessionStateMachine


def test_valid_lifecycle_transitions() -> None:
    """Test standard valid lifecycle transitions."""
    sm = SessionStateMachine()
    assert sm.current_state == SessionState.IDLE

    sm.transition_to(SessionState.VALIDATING)
    sm.transition_to(SessionState.PREPARING_DEVICES)
    sm.transition_to(SessionState.LOADING_MEDIA)
    sm.transition_to(SessionState.READY)
    sm.transition_to(SessionState.RUNNING)
    assert sm.current_state == SessionState.RUNNING

    sm.transition_to(SessionState.PAUSED)
    assert sm.current_state == SessionState.PAUSED

    sm.transition_to(SessionState.RUNNING)
    sm.transition_to(SessionState.STOPPING)
    sm.transition_to(SessionState.IDLE)
    assert sm.current_state == SessionState.IDLE


def test_invalid_state_transition_raises_error() -> None:
    """Test attempting an invalid transition raises InvalidStateTransitionError."""
    sm = SessionStateMachine()
    with pytest.raises(
        InvalidStateTransitionError, match="Invalid state transition from IDLE to RUNNING"
    ):
        sm.transition_to(SessionState.RUNNING)
