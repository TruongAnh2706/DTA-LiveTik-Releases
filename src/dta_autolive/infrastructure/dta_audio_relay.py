"""DTA Studio - Direct Isolated Audio Relay Engine for TikTok Live & Video Playback.

Extracts the exact audio stream from live relay URLs or local video files using FFmpeg,
and routes the pure PCM audio directly to the DTA Virtual Audio Cable (or selected audio sink)
via PySide6 QAudioSink with zero latency, completely isolating it from PC system sounds.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import threading
import time
from pathlib import Path

import structlog
from PySide6.QtCore import QByteArray, QCoreApplication, QIODevice
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSink, QMediaDevices

try:
    import imageio_ffmpeg  # type: ignore[import-untyped]
except ImportError:
    imageio_ffmpeg = None

logger = structlog.get_logger()


class DTAAudioRelay:
    """Manages background audio extraction and isolated routing to Virtual Audio Cable."""

    def __init__(self, sample_rate: int = 44100, channels: int = 2) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_running: bool = False
        self.volume: float = 1.0

        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._sink: QAudioSink | None = None
        self._io_dev: QIODevice | None = None
        self._lock = threading.Lock()

        # Ensure Qt Application context exists for multimedia
        self._qt_app = QCoreApplication.instance() or QCoreApplication([])

    def _find_ffmpeg(self) -> str:
        """Locate FFmpeg executable binary."""
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

    def get_target_audio_device(self, sink_name: str | None = None) -> QAudioDevice:
        """Find the matching audio output device (prioritizing Virtual Cable / DTA Audio)."""
        outputs = QMediaDevices.audioOutputs()
        if not outputs:
            return QMediaDevices.defaultAudioOutput()

        if sink_name and sink_name not in ("default", "cable", "auto"):
            # Match by specific device name / ID
            for dev in outputs:
                if sink_name.lower() in dev.description().lower() or sink_name == bytes(dev.id().toHex().data()).decode("utf-8", errors="ignore"):
                    return dev

        if sink_name == "default":
            return QMediaDevices.defaultAudioOutput()

        # By default or for "cable", look for Virtual Audio Cable / DTA Audio
        for dev in outputs:
            desc = dev.description().lower()
            if "cable" in desc or "dta audio" in desc or "virtual" in desc:
                logger.info("virtual_audio_cable_device_selected", device=dev.description())
                return dev

        # Fallback to default output device
        default_dev = QMediaDevices.defaultAudioOutput()
        logger.info("default_audio_device_selected_as_fallback", device=default_dev.description())
        return default_dev

    def start_audio_relay(
        self,
        source: str,
        sink_name: str | None = None,
        volume: float = 1.0,
    ) -> bool:
        """Start streaming the pure audio track from the given URL or video file to the target audio device."""
        with self._lock:
            self.stop_audio_relay()

            if not source:
                return False

            self.is_running = True
            self.volume = max(0.0, min(1.0, volume))
            ffmpeg_bin = self._find_ffmpeg()

            target_device = self.get_target_audio_device(sink_name)

            fmt = QAudioFormat()
            fmt.setSampleRate(self.sample_rate)
            fmt.setChannelCount(self.channels)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            try:
                self._sink = QAudioSink(target_device, fmt)
                self._sink.setBufferSize(32768)  # ~180ms jitter-free solid buffer
                self._sink.setVolume(self.volume)
                self._io_dev = self._sink.start()
            except Exception as e:
                logger.error("audio_sink_init_failed", error=str(e))
                self.is_running = False
                return False

            # Build FFmpeg command to decode stream audio directly into raw PCM
            is_stream = source.startswith(("http://", "https://", "rtmp://", "rtsp://"))
            cmd = self._build_ffmpeg_cmd(ffmpeg_bin, source, is_stream)

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=1024 * 64,
                )
            except Exception as e:
                logger.error("ffmpeg_audio_spawn_failed", error=str(e))
                self.stop_audio_relay()
                return False

            def _worker() -> None:
                logger.info("dta_audio_relay_worker_started", source=source[:50])
                chunk_size = 2048
                silence_chunk = b"\x00" * 512  # Keep-alive padding to prevent WASAPI stream disconnect

                while self.is_running:
                    io_dev = self._io_dev
                    sink = self._sink
                    if not io_dev or not sink:
                        time.sleep(0.02)
                        continue

                    # Auto-recover sink if it fell into Suspended or Stopped state unexpectedly
                    with contextlib.suppress(Exception):
                        if sink.state() in (QAudioSink.State.SuspendedState, QAudioSink.State.StoppedState) and self.is_running:
                            self._io_dev = sink.start()
                            io_dev = self._io_dev

                    proc = self._process
                    if not proc or not proc.stdout:
                        # Process transition in progress: send small silence to keep WASAPI alive
                        try:
                            free_bytes = sink.bytesFree()
                            if free_bytes >= len(silence_chunk):
                                io_dev.write(QByteArray(silence_chunk))
                        except Exception:
                            pass
                        time.sleep(0.01)
                        continue

                    try:
                        free_bytes = sink.bytesFree()
                        if free_bytes < chunk_size:
                            time.sleep(0.008)
                            continue

                        chunk = proc.stdout.read(min(chunk_size, free_bytes))
                        if not chunk:
                            # Stream ended or track switching: send keep-alive silence
                            if free_bytes >= len(silence_chunk):
                                io_dev.write(QByteArray(silence_chunk))
                            time.sleep(0.01)
                            continue

                        io_dev.write(QByteArray(chunk))
                    except Exception:
                        time.sleep(0.01)

                logger.info("dta_audio_relay_worker_stopped")

            self._thread = threading.Thread(target=_worker, daemon=True)
            self._thread.start()
            return True

    def _build_ffmpeg_cmd(self, ffmpeg_bin: str, source: str, is_stream: bool) -> list[str]:
        """Tạo lệnh FFmpeg chuẩn xác cho audio decoding."""
        if is_stream:
            return [
                ffmpeg_bin,
                "-reconnect",
                "1",
                "-reconnect_streamed",
                "1",
                "-reconnect_delay_max",
                "5",
                "-i",
                source,
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
        return [
            ffmpeg_bin,
            "-re",
            "-i",
            source,
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

    def switch_audio_source(self, new_source: str) -> bool:
        """Chuyển đổi luồng âm thanh LIỀN MẠCH (GAPLESS) sang video mới mà không ngắt QAudioSink."""
        with self._lock:
            if not self.is_running or not self._sink or not self._io_dev:
                return self.start_audio_relay(new_source, volume=self.volume)

            old_proc = self._process
            self._process = None

            if old_proc:
                with contextlib.suppress(Exception):
                    old_proc.terminate()
                    old_proc.kill()

            ffmpeg_bin = self._find_ffmpeg()
            is_stream = new_source.startswith(("http://", "https://", "rtmp://", "rtsp://"))
            cmd = self._build_ffmpeg_cmd(ffmpeg_bin, new_source, is_stream)

            try:
                new_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=1024 * 64,
                )
                self._process = new_proc
                logger.info("audio_relay_source_switched_gapless", new_source=new_source[:60])
                return True
            except Exception as e:
                logger.error("audio_relay_switch_failed", error=str(e))
                return False

    def stop_audio_relay(self) -> None:
        """Stop the audio relay worker and terminate FFmpeg cleanly."""
        self.is_running = False

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

    def set_volume(self, volume: float) -> None:
        """Adjust output volume [0.0 - 1.0]."""
        self.volume = max(0.0, min(1.0, volume))
        if self._sink:
            self._sink.setVolume(self.volume)
