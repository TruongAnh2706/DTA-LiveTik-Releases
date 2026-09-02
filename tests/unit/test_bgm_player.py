"""Unit tests for DTABackgroundMusicPlayer module.

Tests scanning, loop playback state, volume management, and event callbacks.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dta_autolive.infrastructure.dta_bgm_player import DTABackgroundMusicPlayer


def test_bgm_player_init():
    """Kiểm tra khởi tạo player với giá trị mặc định."""
    player = DTABackgroundMusicPlayer()
    assert player.is_playing is False
    assert player.volume == 0.3
    assert player.audio_files == []
    assert player.current_index == 0


def test_bgm_player_scan_folder(tmp_path: Path):
    """Kiểm tra quét thư mục nhạc nền với các định dạng khác nhau."""
    music_dir = tmp_path / "bgm"
    music_dir.mkdir()

    (music_dir / "song1.mp3").write_bytes(b"dummy mp3")
    (music_dir / "song2.wav").write_bytes(b"dummy wav")
    (music_dir / "song3.aac").write_bytes(b"dummy aac")
    (music_dir / "doc.txt").write_bytes(b"dummy text")  # Không phải audio

    player = DTABackgroundMusicPlayer()
    tracks = player.scan_music_folder(str(music_dir))

    assert len(tracks) == 3
    assert any("song1.mp3" in t for t in tracks)
    assert any("song2.wav" in t for t in tracks)
    assert any("song3.aac" in t for t in tracks)
    assert not any("doc.txt" in t for t in tracks)


def test_bgm_player_volume_adjustment():
    """Kiểm tra điều chỉnh âm lượng BGM."""
    player = DTABackgroundMusicPlayer()
    player.set_volume(0.5)
    assert player.volume == 0.5

    # Clamp min max
    player.set_volume(1.5)
    assert player.volume == 1.0
    player.set_volume(-0.5)
    assert player.volume == 0.0


def test_bgm_player_status(tmp_path: Path):
    """Kiểm tra lấy thông tin trạng thái player."""
    music_dir = tmp_path / "bgm"
    music_dir.mkdir()
    (music_dir / "track.mp3").write_bytes(b"dummy")

    player = DTABackgroundMusicPlayer()
    player.scan_music_folder(str(music_dir))

    status = player.get_status()
    assert status["is_playing"] is False
    assert status["total_tracks"] == 1
    assert status["volume"] == 0.3
    assert "track.mp3" in status["tracks"][0]


@patch("subprocess.Popen")
@patch("dta_autolive.infrastructure.dta_bgm_player.QAudioSink")
def test_bgm_player_start_stop(mock_sink_cls, mock_popen, tmp_path: Path):
    """Kiểm tra bật/tắt nhạc nền và phát event."""
    events = []
    player = DTABackgroundMusicPlayer(event_callback=events.append)

    music_dir = tmp_path / "bgm"
    music_dir.mkdir()
    (music_dir / "track.mp3").write_bytes(b"dummy")

    mock_sink_instance = MagicMock()
    mock_sink_cls.return_value = mock_sink_instance

    mock_proc_instance = MagicMock()
    mock_proc_instance.stdout.read.return_value = b""
    mock_popen.return_value = mock_proc_instance

    ok = player.start_bgm(str(music_dir), volume=0.4)
    assert ok is True
    assert player.is_playing is True
    assert player.volume == 0.4
    assert any(e.get("type") == "BGM_STATE_UPDATE" and e.get("is_playing") for e in events)

    player.stop_bgm()
    assert player.is_playing is False
    assert any(e.get("type") == "BGM_STATE_UPDATE" and not e.get("is_playing") for e in events)
