"""Unit tests for domain models."""

import pytest
from pydantic import ValidationError

from dta_autolive.domain.models import (
    MediaMetadata,
    TimelineEvent,
    TimelineScript,
)


def test_media_metadata_valid() -> None:
    """Test valid MediaMetadata parsing."""
    meta = MediaMetadata(
        duration_ms=120000,
        width=1080,
        height=1920,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        sample_rate=44100,
        channels=2,
        has_audio=True,
    )
    assert meta.duration_ms == 120000
    assert meta.has_audio is True


def test_media_metadata_rejects_no_audio() -> None:
    """Test MediaMetadata rejects video without audio stream."""
    with pytest.raises(ValidationError, match="MEDIA-002"):
        MediaMetadata(
            duration_ms=120000,
            width=1080,
            height=1920,
            fps=30.0,
            video_codec="h264",
            audio_codec="none",
            sample_rate=0,
            channels=0,
            has_audio=False,
        )


def test_timeline_script_unique_event_ids() -> None:
    """Test TimelineScript rejects duplicate event_ids."""
    evt1 = TimelineEvent(
        event_id="evt_01", time_ms=5000, type="PIN_PRODUCT", payload={"product_id": "100"}
    )
    evt2 = TimelineEvent(
        event_id="evt_01", time_ms=10000, type="PIN_PRODUCT", payload={"product_id": "200"}
    )

    with pytest.raises(ValidationError, match="Duplicate event_id detected"):
        TimelineScript(
            script_id="script_01",
            video_filename="v1.mp4",
            expected_duration_ms=60000,
            timeline_events=[evt1, evt2],
        )


def test_timeline_script_events_sorting() -> None:
    """Test TimelineScript automatically sorts events by time_ms."""
    evt1 = TimelineEvent(
        event_id="evt_01", time_ms=15000, type="PIN_PRODUCT", payload={"product_id": "100"}
    )
    evt2 = TimelineEvent(
        event_id="evt_02", time_ms=5000, type="PIN_PRODUCT", payload={"product_id": "200"}
    )

    script = TimelineScript(
        script_id="script_01",
        video_filename="v1.mp4",
        expected_duration_ms=60000,
        timeline_events=[evt1, evt2],
    )
    assert script.timeline_events[0].event_id == "evt_02"
    assert script.timeline_events[1].event_id == "evt_01"
