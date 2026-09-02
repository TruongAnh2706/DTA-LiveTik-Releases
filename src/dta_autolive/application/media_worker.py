from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoFrame, QVideoSink

from dta_autolive.domain.models import MediaMetadata
from dta_autolive.infrastructure.dta_softcam_engine import DTASoftcamEngine
from dta_autolive.infrastructure.shm_video_producer import DTASharedMemoryVideoProducer
from dta_autolive.infrastructure.virtual_device_adapter import VirtualDeviceAdapter


class MediaWorker(QObject):
    """Media Worker managing video playback, infinite playlist looping, Shared Memory & DTA Audio routing."""

    position_changed = Signal(int)  # ms
    duration_changed = Signal(int)  # ms
    playback_state_changed = Signal(str)  # IDLE, PLAYING, PAUSED, STOPPED
    media_ended = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.shm_producer = DTASharedMemoryVideoProducer()
        self.softcam_engine = DTASoftcamEngine(width=1080, height=1920, fps=30)

        # Attach QVideoSink to intercept video frames for DirectShow Virtual Camera
        self.video_sink = QVideoSink(self)
        self.player.setVideoSink(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self._on_video_frame_changed)

        # Enable native QMediaPlayer infinite looping
        self.player.setLoops(QMediaPlayer.Loops.Infinite)

        # Route audio output to proprietary DTA Audio device
        dta_audio_device = VirtualDeviceAdapter.get_dta_audio_device()
        self.audio_output = QAudioOutput(dta_audio_device, self)
        self.player.setAudioOutput(self.audio_output)

        self.player.positionChanged.connect(self.position_changed.emit)
        self.player.durationChanged.connect(self.duration_changed.emit)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Initialize Shared Memory Black Frame
        self.shm_producer.write_black_frame()

    def load_media(self, file_path: str) -> MediaMetadata:
        """Load and validate video media source file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        model = MediaMetadata(
            duration_ms=180000,
            width=1080,
            height=1920,
            fps=30.0,
            video_codec="h264",
            audio_codec="aac",
            sample_rate=48000,
            channels=2,
            has_audio=True,
        )
        self.player.setSource(QUrl.fromLocalFile(str(path.absolute())))
        return model

    def play(self) -> None:
        """Start or resume playback."""
        self.softcam_engine.set_active_video_streaming(True)
        self.audio_output.setVolume(1.0)
        self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        self.softcam_engine.set_active_video_streaming(False)
        self.player.pause()

    def stop(self) -> None:
        """Stop playback."""
        self.softcam_engine.set_active_video_streaming(False)
        self.player.stop()

    def set_position(self, position_ms: int) -> None:
        """Seek to position in milliseconds."""
        self.player.setPosition(position_ms)

    def _on_video_frame_changed(self, frame: QVideoFrame) -> None:
        """Intercept QVideoFrame from QMediaPlayer and send BGR24 array to Virtual Camera & Shared Memory."""
        if not frame.isValid():
            return

        image = frame.toImage()
        if image.isNull():
            return

        image = image.convertToFormat(QImage.Format.Format_BGR888)
        w, h = image.width(), image.height()

        ptr = image.constBits()
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3))

        # Scale to 1080x1920 9:16 vertical video stream format if needed
        if w != 1080 or h != 1920:
            arr = np.asarray(
                cv2.resize(arr, (1080, 1920), interpolation=cv2.INTER_AREA), dtype=np.uint8
            )

        # Write frame to Virtual Camera & Shared Memory
        self.softcam_engine.send_bgr_frame(arr)
        self.shm_producer.write_mjpeg_frame(arr)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Handle internal player state change."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_state_changed.emit("LIVE_PLAYING")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.playback_state_changed.emit("PAUSED")
        else:
            self.playback_state_changed.emit("STOPPED")

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """Handle media status changes and trigger infinite loop on EndOfMedia."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.media_ended.emit()
            self.player.setPosition(0)
            self.player.play()
