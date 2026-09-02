"""Unit tests for LiveStreamRecorder module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dta_autolive.infrastructure.stream_recorder import LiveStreamRecorder


def test_stream_recorder_init() -> None:
    """Test recorder initialization with default and custom directory."""
    rec = LiveStreamRecorder()
    assert rec.output_dir == Path.home() / "Videos" / "DTA_Live_Records"
    assert rec.is_recording is False
    assert rec.current_output_file is None

    custom_dir = Path.cwd() / "test_records"
    rec_custom = LiveStreamRecorder(default_output_dir=custom_dir)
    assert rec_custom.output_dir == custom_dir.resolve()


def test_stream_recorder_sanitize_filename() -> None:
    """Test filename sanitization removes illegal characters."""
    rec = LiveStreamRecorder()
    assert rec._sanitize_filename("@shop_vietnam:123/live?") == "shop_vietnam123live"  # noqa: SLF001
    assert rec._sanitize_filename("") == "DTA_Live"  # noqa: SLF001


def test_stream_recorder_start_and_stop(tmp_path: Path) -> None:
    """Test start_recording and stop_recording with mocked FFmpeg subprocess."""
    rec = LiveStreamRecorder(default_output_dir=tmp_path)

    mock_process = MagicMock()
    mock_process.poll.return_value = None

    with patch("subprocess.Popen", return_value=mock_process):
        output_file = rec.start_recording(
            stream_url="http://127.0.0.1:8000/live.flv",
            output_dir=tmp_path,
            channel_name="DemoStreamer",
        )

        assert rec.is_recording is True
        assert output_file.parent == tmp_path
        assert "DTA_Live_DemoStreamer_" in output_file.name
        assert output_file.suffix == ".mp4"

        stats = rec.get_stats()
        assert stats["is_recording"] is True
        assert "DTA_Live_DemoStreamer_" in stats["file_name"]

        # Stop recording
        final_file = rec.stop_recording()
        assert rec.is_recording is False
        assert final_file == output_file
        mock_process.terminate.assert_called_once()


def test_stream_recorder_stats_idle() -> None:
    """Test get_stats when no recording session is active."""
    rec = LiveStreamRecorder()
    stats = rec.get_stats()
    assert stats["is_recording"] is False
    assert stats["duration_seconds"] == 0
    assert stats["duration_formatted"] == "00:00:00"
    assert stats["bytes"] == 0
