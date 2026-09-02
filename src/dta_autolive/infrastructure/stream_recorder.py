"""High-Performance Live Stream Recorder Worker for DTA AutoLive.

Performs zero-loss direct stream copy remuxing (H.264/AAC -> MP4) using FFmpeg,
with safe faststart moov-atom chunking to prevent corruption on unexpected termination.
"""

import contextlib
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

try:
    import imageio_ffmpeg  # type: ignore[import-untyped]
except ImportError:
    imageio_ffmpeg = None

if TYPE_CHECKING:
    import asyncio

logger = structlog.get_logger()


class LiveStreamRecorder:
    """Manages background FFmpeg process for capturing and recording live streams."""

    def __init__(self, default_output_dir: str | Path | None = None) -> None:
        if default_output_dir is None:
            self.output_dir = Path.home() / "Videos" / "DTA_Live_Records"
        else:
            self.output_dir = Path(default_output_dir).resolve()

        self._process: subprocess.Popen[bytes] | None = None
        self._is_recording = False
        self._current_file: Path | None = None
        self._start_time: float = 0.0
        self._channel_name: str = "LiveStream"
        self._progress_callback: Callable[[dict[str, Any]], None] | None = None
        self._monitor_task: asyncio.Task[None] | None = None

    @property
    def is_recording(self) -> bool:
        """Check if recording is currently active."""
        return self._is_recording and self._process is not None and self._process.poll() is None

    @property
    def current_output_file(self) -> Path | None:
        """Get the current output file path."""
        return self._current_file

    def set_progress_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register callback for broadcasting recording progress."""
        self._progress_callback = callback

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize channel/user name for safe Windows filesystem naming."""
        clean = re.sub(r'[\\/*?:"<>|@]', "", name).strip()
        return clean or "DTA_Live"

    def _find_ffmpeg(self) -> str:
        """Find path to FFmpeg binary executable with multi-source auto discovery."""
        # 1. Check imageio_ffmpeg bundled binary
        if imageio_ffmpeg is not None:
            with contextlib.suppress(Exception):
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                if ffmpeg_bin and Path(ffmpeg_bin).exists():
                    return str(ffmpeg_bin)

        # 2. Check local workspace or script directory
        for base_dir in (Path.cwd(), Path(__file__).resolve().parent, Path(__file__).resolve().parents[2]):
            local_bin = base_dir / "ffmpeg.exe"
            if local_bin.exists():
                return str(local_bin)

        # 3. Check system PATH
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return which_ffmpeg

        # 4. Check common Windows installation paths
        common_paths = [
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
            Path.home() / "scoop/shims/ffmpeg.exe",
            Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe",
        ]
        for p in common_paths:
            if p.exists():
                return str(p)

        return "ffmpeg"

    def start_recording(
        self,
        stream_url: str,
        output_dir: str | Path | None = None,
        channel_name: str = "TikTokLive",
    ) -> Path:
        """Start recording a live stream to an MP4 file.

        Args:
            stream_url: Live FLV or HLS m3u8 stream URL.
            output_dir: Destination folder. Defaults to self.output_dir.
            channel_name: Channel identifier for filename tagging.

        Returns:
            Path to the recording MP4 file.
        """
        if self.is_recording:
            logger.warning("recording_already_in_progress", current_file=str(self._current_file))
            self.stop_recording()

        if output_dir:
            self.output_dir = Path(output_dir).resolve()

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._channel_name = self._sanitize_filename(channel_name)
        timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")
        filename = f"DTA_Live_{self._channel_name}_{timestamp}.mp4"
        self._current_file = self.output_dir / filename

        ffmpeg_bin = self._find_ffmpeg()

        # Build FFmpeg direct stream copy command with faststart flag
        cmd = [
            ffmpeg_bin,
            "-y",
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            "5",
            "-i",
            stream_url,
            "-c",
            "copy",
            "-movflags",
            "+faststart+frag_keyframe+empty_moov",
            str(self._current_file),
        ]

        logger.info(
            "stream_recorder_starting",
            output_file=str(self._current_file),
            stream_url=stream_url[:60] + "...",
        )

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
            )
            self._is_recording = True
            self._start_time = time.time()
            return self._current_file
        except Exception as e:
            logger.error("stream_recorder_start_failed", error=str(e))
            self._is_recording = False
            self._current_file = None
            raise

    def stop_recording(self) -> Path | None:
        """Gracefully stop the FFmpeg recording process and finalize the MP4 container."""
        if not self._process:
            self._is_recording = False
            return self._current_file

        logger.info("stream_recorder_stopping", output_file=str(self._current_file))
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1.0)
        except Exception as e:
            logger.warning("stream_recorder_stop_exception", error=str(e))
        finally:
            self._process = None
            self._is_recording = False

        final_file = self._current_file
        if final_file and final_file.exists():
            file_size_mb = round(final_file.stat().st_size / (1024 * 1024), 2)
            logger.info(
                "stream_recorder_finished",
                file_path=str(final_file),
                size_mb=file_size_mb,
            )
        return final_file

    def get_stats(self) -> dict[str, Any]:
        """Get live stats on current recording session (elapsed duration & file size)."""
        if not self.is_recording or not self._current_file:
            return {
                "is_recording": False,
                "duration_seconds": 0,
                "duration_formatted": "00:00:00",
                "bytes": 0,
                "size_formatted": "0 MB",
                "file_path": "",
            }

        elapsed = int(time.time() - self._start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        duration_fmt = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        file_bytes = 0
        if self._current_file.exists():
            with contextlib.suppress(OSError):
                file_bytes = self._current_file.stat().st_size

        size_mb = file_bytes / (1024 * 1024)
        size_fmt = f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.1f} MB"

        return {
            "is_recording": True,
            "duration_seconds": elapsed,
            "duration_formatted": duration_fmt,
            "bytes": file_bytes,
            "size_formatted": size_fmt,
            "file_path": str(self._current_file),
            "file_name": self._current_file.name,
        }
