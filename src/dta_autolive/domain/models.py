"""Domain entities and Pydantic v2 schemas for DTA AutoLive."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventState(str, Enum):
    """Timeline event lifecycle state."""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class SessionState(str, Enum):
    """App Session state machine states."""

    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    PREPARING_DEVICES = "PREPARING_DEVICES"
    LOADING_MEDIA = "LOADING_MEDIA"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SEEKING = "SEEKING"
    SWITCHING_ITEM = "SWITCHING_ITEM"
    RECOVERING = "RECOVERING"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MediaMetadata(BaseModel):
    """Metadata extracted from FFprobe."""

    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    width: int = Field(..., ge=0)
    height: int = Field(..., ge=0)
    fps: float = Field(..., gt=0)
    video_codec: str
    audio_codec: str
    sample_rate: int = Field(..., ge=0)
    channels: int = Field(..., ge=0)
    has_audio: bool = Field(...)

    @field_validator("has_audio")
    @classmethod
    def validate_audio(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Video without audio stream is rejected (MEDIA-002)")
        return v


class PlaylistItem(BaseModel):
    """Individual item inside a Playlist."""

    item_id: str = Field(...)
    video_path: str = Field(...)
    json_path: str = Field(...)
    order_index: int = Field(..., ge=0)
    enabled: bool = Field(default=True)
    title: str = Field(default="")
    media_metadata: MediaMetadata | None = None
    validation_status: bool = Field(default=False)
    last_error: str | None = None


class Playlist(BaseModel):
    """Playlist entity holding multiple PlaylistItems."""

    playlist_id: str = Field(...)
    name: str = Field(default="Default Playlist")
    items: list[PlaylistItem] = Field(default_factory=list)
    loop_enabled: bool = Field(default=True)
    current_index: int = Field(default=0, ge=0)


class RetryPolicy(BaseModel):
    """Retry policy configuration for timeline event dispatch."""

    max_attempts: int = Field(default=2, ge=1)
    timeout_ms: int = Field(default=5000, ge=500)


class TimelineEvent(BaseModel):
    """Event entity loaded from Video JSON Script."""

    event_id: str = Field(...)
    time_ms: int = Field(..., ge=0, description="Trigger time in Video Clock (ms)")
    type: str = Field(..., description="Command type (e.g., PIN_PRODUCT)")
    payload: dict[str, Any] = Field(default_factory=dict)
    valid_for_ms: int = Field(default=10000, ge=1000)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    state: EventState = Field(default=EventState.PENDING)

    @field_validator("payload")
    @classmethod
    def validate_product_id(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        # Product ID validation for PIN_PRODUCT type
        return v


class TimelineScript(BaseModel):
    """Timeline JSON script schema for a single video."""

    schema_version: str = Field(default="1.0")
    script_id: str = Field(...)
    video_filename: str = Field(...)
    expected_duration_ms: int = Field(..., ge=0)
    loop_mode: str = Field(default="inherit_playlist")
    timeline_events: list[TimelineEvent] = Field(default_factory=list)

    @field_validator("timeline_events")
    @classmethod
    def validate_unique_event_ids(cls, events: list[TimelineEvent]) -> list[TimelineEvent]:
        seen_ids = set()
        for evt in events:
            if evt.event_id in seen_ids:
                raise ValueError(f"Duplicate event_id detected: {evt.event_id}")
            seen_ids.add(evt.event_id)
        # Ensure events are sorted by time_ms
        return sorted(events, key=lambda x: x.time_ms)


class Session(BaseModel):
    """Active Live Session Domain Entity."""

    session_id: str = Field(...)
    state: SessionState = Field(default=SessionState.IDLE)
    started_at: str | None = None
    session_clock_ms: int = Field(default=0, ge=0)
    paused_total_ms: int = Field(default=0, ge=0)
    active_item_id: str | None = None
    active_product_id: str | None = None


class BridgeConnection(BaseModel):
    """WebSocket Extension Connection Status."""

    connection_id: str | None = None
    status: str = Field(default="DISCONNECTED")
    paired: bool = Field(default=False)
    last_heartbeat_ms: int = Field(default=0, ge=0)
    bound_tab_id: str | None = None
