"""Unit tests for TikTok Live Stream URL Extractor module."""

from __future__ import annotations

from dta_autolive.infrastructure.tiktok_live_extractor import (
    extract_username_or_room_id,
    resolve_tiktok_live_stream,
)


def test_extract_username_or_room_id() -> None:
    """Test extracting username from various TikTok URL formats."""
    assert (
        extract_username_or_room_id("https://www.tiktok.com/@ductruong_live/live")
        == "ductruong_live"
    )
    assert extract_username_or_room_id("@ductruong_live") == "ductruong_live"
    assert extract_username_or_room_id("ductruong_live") == "ductruong_live"
    assert extract_username_or_room_id("https://tiktok.com/@streamer.test") == "streamer.test"


def test_resolve_tiktok_live_stream() -> None:
    """Test resolving TikTok Live stream info."""
    # Test direct stream pull URL
    res = resolve_tiktok_live_stream("https://pull-f5-sg01.tiktokcdn.com/stage/stream-123456_hd.flv")
    assert res["success"] is True
    assert "stream_url" in res
    assert res["resolution"] is not None
    assert res["is_live"] is True

    # Test invalid empty input
    res_empty = resolve_tiktok_live_stream("")
    assert res_empty["success"] is False
