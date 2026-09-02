"""DTA Studio - Background Music (BGM) Player & Dual Audio Mixer Engine.

Manages background music playlist scanning, continuous loop playback, and independent volume
control routed directly to the Virtual Audio Cable (CABLE Input / DTA Audio) alongside video audio.

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

from __future__ import annotations

import contextlib
import os
import random
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import structlog
from PySide6.QtCore import QByteArray, QCoreApplication, QIODevice
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSink, QMediaDevices

try:
    import imageio_ffmpeg  # type: ignore[import-untyped]
except ImportError:
    imageio_ffmpeg = None

logger = structlog.get_logger()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma"}


class DTABackgroundMusicPlayer:
    """Manages background music playback from a folder in an infinite loop with volume mixing."""

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 2,
        log_callback: Callable[[str, str], None] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.log_callback = log_callback
        self.event_callback = event_callback

        self.is_playing: bool = False
        self.volume: float = 0.3  # Mặc định 30% âm lượng để không lấn át tiếng nói video
        self.current_folder: str = ""
        self.audio_files: list[str] = []
        self.current_index: int = 0
        self.sink_name: str | None = None

        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._sink: QAudioSink | None = None
        self._io_dev: QIODevice | None = None
        self._lock = threading.Lock()

        self._qt_app = QCoreApplication.instance() or QCoreApplication([])

    def log(self, level: str, message: str) -> None:
        if self.log_callback:
            with contextlib.suppress(Exception):
                self.log_callback(level, message)
        logger.info("dta_bgm_log", level=level, message=message)

    def emit_event(self, event: dict[str, Any]) -> None:
        if self.event_callback:
            with contextlib.suppress(Exception):
                self.event_callback(event)

    def _find_ffmpeg(self) -> str:
        """Locate FFmpeg binary."""
        if imageio_ffmpeg is not None:
            with contextlib.suppress(Exception):
                bin_path = imageio_ffmpeg.get_ffmpeg_exe()
                if bin_path and Path(bin_path).exists():
                    return str(bin_path)

        for candidate in [
            shutil.which("ffmpeg"),
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
            Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe",
        ]:
            if candidate and Path(candidate).exists():
                return str(candidate)

        return "ffmpeg"

    def scan_music_folder(self, folder_path: str) -> list[str]:
        """Scan directory recursively or shallowly for audio files."""
        if not folder_path or not os.path.exists(folder_path):
            return []

        folder = Path(folder_path)
        tracks: list[str] = []
        try:
            for root, _, files in os.walk(folder):
                for f in sorted(files):
                    ext = Path(f).suffix.lower()
                    if ext in AUDIO_EXTENSIONS:
                        tracks.append(os.path.join(root, f))
        except Exception as e:
            logger.warning("scan_music_folder_error", error=str(e))

        self.audio_files = tracks
        self.current_folder = folder_path
        logger.info("scanned_bgm_folder", count=len(tracks), folder=folder_path)
        return tracks

    def get_target_audio_device(self, sink_name: str | None = None) -> QAudioDevice:
        """Find matching output audio device (prioritizing Virtual Cable / DTA Audio)."""
        outputs = QMediaDevices.audioOutputs()
        if not outputs:
            return QMediaDevices.defaultAudioOutput()

        if sink_name and sink_name not in ("default", "cable", "auto"):
            for dev in outputs:
                if sink_name.lower() in dev.description().lower():
                    return dev

        if sink_name == "default":
            return QMediaDevices.defaultAudioOutput()

        # Prioritize CABLE / DTA Audio
        for dev in outputs:
            desc = dev.description().lower()
            if "cable" in desc or "dta audio" in desc or "virtual" in desc:
                return dev

        return QMediaDevices.defaultAudioOutput()

    def start_bgm(
        self,
        folder_path: str | None = None,
        volume: float | None = None,
        sink_name: str | None = None,
        shuffle: bool = False,
    ) -> bool:
        """Start playing background music playlist in an infinite continuous loop."""
        with self._lock:
            self.stop_bgm()

            if folder_path:
                self.scan_music_folder(folder_path)

            if not self.audio_files:
                self.log("WARNING", "⚠️ Thư mục nhạc nền không có tệp âm thanh hợp lệ (.mp3, .wav, .aac, .m4a,...)")
                return False

            if volume is not None:
                self.volume = max(0.0, min(1.0, volume))
            if sink_name is not None:
                self.sink_name = sink_name

            if shuffle:
                random.shuffle(self.audio_files)

            self.is_playing = True
            self.current_index = 0

            target_device = self.get_target_audio_device(self.sink_name)

            fmt = QAudioFormat()
            fmt.setSampleRate(self.sample_rate)
            fmt.setChannelCount(self.channels)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            try:
                self._sink = QAudioSink(target_device, fmt)
                self._sink.setBufferSize(16384)
                self._sink.setVolume(self.volume)
                self._io_dev = self._sink.start()
            except Exception as e:
                logger.error("bgm_audio_sink_init_failed", error=str(e))
                self.is_playing = False
                return False

            self._thread = threading.Thread(target=self._bgm_loop, daemon=True)
            self._thread.start()

            track_name = Path(self.audio_files[0]).name
            self.log("SUCCESS", f"🎶 [Nhạc Nền] Đã bật nhạc nền ({len(self.audio_files)} bài) - Đang phát: {track_name}")
            self.emit_event({
                "type": "BGM_STATE_UPDATE",
                "is_playing": True,
                "folder": self.current_folder,
                "current_track": track_name,
                "current_index": 0,
                "total_tracks": len(self.audio_files),
                "volume": self.volume,
            })
            return True

    def _bgm_loop(self) -> None:
        """Background continuous playlist playback loop."""
        ffmpeg_bin = self._find_ffmpeg()
        chunk_size = 2048

        while self.is_playing:
            if not self.audio_files:
                break

            current_track = self.audio_files[self.current_index]
            track_name = Path(current_track).name

            logger.info("bgm_playing_track", index=self.current_index, track=track_name)
            self.emit_event({
                "type": "BGM_TRACK_CHANGED",
                "current_track": track_name,
                "current_index": self.current_index,
                "total_tracks": len(self.audio_files),
            })

            cmd = [
                ffmpeg_bin,
                "-re",
                "-i",
                current_track,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(self.sample_rate),
                "-ac",
                str(self.channels),
                "-f",
                "s16le",
                "-",
            ]

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=1024 * 64,
                )
            except Exception as e:
                logger.error("bgm_ffmpeg_spawn_failed", error=str(e))
                self.current_index = (self.current_index + 1) % len(self.audio_files)
                time.sleep(0.5)
                continue

            while self.is_playing:
                proc = self._process
                sink = self._sink
                io_dev = self._io_dev

                if not proc or not proc.stdout or not sink or not io_dev:
                    time.sleep(0.02)
                    continue

                try:
                    free_bytes = sink.bytesFree()
                    if free_bytes < chunk_size:
                        time.sleep(0.01)
                        continue

                    chunk = proc.stdout.read(min(chunk_size, free_bytes))
                    if not chunk:
                        # Kết thúc bài nhạc hiện tại -> Chuyển bài tiếp theo trong loop
                        break

                    io_dev.write(QByteArray(chunk))
                except Exception:
                    time.sleep(0.02)

            if self._process:
                with contextlib.suppress(Exception):
                    self._process.terminate()
                    self._process.kill()
                self._process = None

            if not self.is_playing:
                break

            # Tự động chuyển sang bài kế tiếp khi bài hát hiện tại chạy hết tự nhiên
            with self._lock:
                self.current_index = (self.current_index + 1) % len(self.audio_files)
            time.sleep(0.05)

    def next_track(self) -> None:
        """Skip to next music track smoothly and update UI immediately."""
        if not self.audio_files:
            return
        with self._lock:
            if not self.is_playing:
                # Nếu đang không phát nhạc: chuyển index và bắn event cập nhật giao diện
                self.current_index = (self.current_index + 1) % len(self.audio_files)
                track_name = Path(self.audio_files[self.current_index]).name
                self.emit_event({
                    "type": "BGM_TRACK_CHANGED",
                    "current_track": track_name,
                    "current_index": self.current_index,
                    "total_tracks": len(self.audio_files),
                })
                self.log("INFO", f"🎶 [Nhạc Nền] Đã chọn bài: {track_name} ({self.current_index + 1}/{len(self.audio_files)})")
                return

            # Nếu đang phát: Chuyển sang bài kế tiếp ngay và hủy process cũ để loop phát ngay bài mới
            self.current_index = (self.current_index + 1) % len(self.audio_files)
            track_name = Path(self.audio_files[self.current_index]).name
            if self._process:
                with contextlib.suppress(Exception):
                    self._process.terminate()
                    self._process.kill()
                self._process = None

            # Bắn event thông báo chuyển bài mới ngay lập tức
            self.emit_event({
                "type": "BGM_TRACK_CHANGED",
                "current_track": track_name,
                "current_index": self.current_index,
                "total_tracks": len(self.audio_files),
            })
            self.log("INFO", f"⏭ [Nhạc Nền] Next bài: {track_name} ({self.current_index + 1}/{len(self.audio_files)})")

    def stop_bgm(self) -> None:
        """Stop background music playback."""
        self.is_playing = False

        if self._process:
            with contextlib.suppress(Exception):
                self._process.terminate()
                self._process.kill()
            self._process = None

        if self._sink:
            with contextlib.suppress(Exception):
                self._sink.stop()
            self._sink = None
            self._io_dev = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
            self._thread = None

        self.emit_event({
            "type": "BGM_STATE_UPDATE",
            "is_playing": False,
            "folder": self.current_folder,
            "current_track": "",
            "volume": self.volume,
        })
        logger.info("bgm_player_stopped")

    def set_volume(self, volume: float) -> None:
        """Adjust BGM volume [0.0 - 1.0]."""
        self.volume = max(0.0, min(1.0, volume))
        if self._sink:
            self._sink.setVolume(self.volume)
        logger.info("bgm_volume_adjusted", volume=self.volume)

    def get_status(self) -> dict[str, Any]:
        """Get current player state."""
        current_track_name = ""
        if self.audio_files and 0 <= self.current_index < len(self.audio_files):
            current_track_name = Path(self.audio_files[self.current_index]).name

        return {
            "is_playing": self.is_playing,
            "folder": self.current_folder,
            "current_track": current_track_name,
            "current_index": self.current_index,
            "total_tracks": len(self.audio_files),
            "volume": self.volume,
            "tracks": [Path(p).name for p in self.audio_files[:50]],
        }
