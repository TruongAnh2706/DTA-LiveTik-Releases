"""DTA Studio - Softcam Architecture & DirectShow Virtual Camera Engine.

Implements DirectShow System Virtual Camera streaming via pyvirtualcam with zero-latency
Shared Memory + Mutex Synchronization fallback for DTA Camera.
"""

import contextlib
import ctypes
import mmap
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import structlog

from dta_autolive.infrastructure.dta_audio_relay import DTAAudioRelay

try:
    import pyvirtualcam  # type: ignore[import-untyped]
except ImportError:
    pyvirtualcam = None

logger = structlog.get_logger()

DTA_SOFTCAM_MAGIC = 0x534F4654  # "SOFT"
DTA_SHM_GLOBAL = "Global\\DTACameraSharedMemory"
DTA_SHM_LOCAL = "Local\\DTACameraSharedMemory"
DTA_MUTEX_GLOBAL = "Global\\DTACameraMutex"
DTA_MUTEX_LOCAL = "Local\\DTACameraMutex"

kernel32 = ctypes.windll.kernel32

# Win32 Mutex Constants
SYNCHRONIZE = 0x00100000
MUTEX_ALL_ACCESS = 0x001F0001
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102


class DTASoftcamHeader(ctypes.Structure):
    """C-compatible DTA_SOFTCAM_HEADER struct."""

    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("fps", ctypes.c_uint32),
        ("format", ctypes.c_uint32),  # 0: BGR24
        ("frame_index", ctypes.c_uint64),
        ("timestamp_ms", ctypes.c_uint64),
        ("payload_size", ctypes.c_uint32),
    ]


class DTASoftcamEngine:
    """Manages virtual camera streaming over DirectShow System Driver & Shared Memory IPC."""

    def __init__(self, width: int = 1080, height: int = 1920, fps: int = 30) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.payload_size = width * height * 3
        self.shm_size = 64 + self.payload_size
        self.frame_counter: int = 0
        self._is_active_video_streaming: bool = False
        self._standby_running: bool = False
        self._standby_thread: threading.Thread | None = None

        self.shm: mmap.mmap | None = None
        self.h_mutex: int | None = None
        self.vcam: pyvirtualcam.Camera | None = None
        self.audio_relay = DTAAudioRelay()

        self._init_ipc()
        self._init_virtual_cam()
        self.start_standby_loop()

    def set_active_video_streaming(self, active: bool) -> None:
        """Toggle active video playback streaming vs background standby screen."""
        self._is_active_video_streaming = active

    def start_standby_loop(self) -> None:
        """Start continuous 30 FPS background thread sending DTA Standby Frame to Virtual Camera."""
        if self._standby_running:
            return
        self._standby_running = True
        self._standby_thread = threading.Thread(target=self._standby_loop, daemon=True)
        self._standby_thread.start()

    def stop_standby_loop(self) -> None:
        """Stop background standby loop."""
        self._standby_running = False
        if self._standby_thread and self._standby_thread.is_alive():
            self._standby_thread.join(timeout=1.0)
            self._standby_thread = None

    def _standby_loop(self) -> None:
        """Background thread feeding 30 FPS DTA Standby Frame continuously to pyvirtualcam."""
        interval = 1.0 / float(self.fps)
        while self._standby_running:
            if not self._is_active_video_streaming:
                start_t = time.time()
                standby_frame = self.generate_dta_standby_frame()
                self.send_bgr_frame(standby_frame)
                elapsed = time.time() - start_t
                sleep_t = max(0.005, interval - elapsed)
                time.sleep(sleep_t)
            else:
                time.sleep(0.05)

    def _init_virtual_cam(self) -> None:
        """Initialize DirectShow System Virtual Camera driver using pyvirtualcam."""
        if pyvirtualcam is None:
            logger.warning("pyvirtualcam_not_installed")
            return

        try:
            self.vcam = pyvirtualcam.Camera(
                width=self.width,
                height=self.height,
                fps=float(self.fps),
                fmt=pyvirtualcam.PixelFormat.BGR,
                device="OBS Virtual Camera",
            )
            logger.info("system_virtual_camera_initialized", device=self.vcam.device, backend=self.vcam.backend)
        except Exception as e:
            try:
                self.vcam = pyvirtualcam.Camera(
                    width=self.width,
                    height=self.height,
                    fps=float(self.fps),
                    fmt=pyvirtualcam.PixelFormat.BGR,
                )
                logger.info("system_virtual_camera_initialized_fallback", device=self.vcam.device, backend=self.vcam.backend)
            except Exception as ex:
                logger.warning("pyvirtualcam_init_failed", error=f"{e} | {ex}")
                self.vcam = None

    def _init_ipc(self) -> None:
        """Initialize Windows Shared Memory and Mutex Lock with Global/Local fallback."""
        # 1. Create/Open Mutex
        try:
            self.h_mutex = kernel32.CreateMutexW(None, False, DTA_MUTEX_GLOBAL)
            if not self.h_mutex:
                self.h_mutex = kernel32.CreateMutexW(None, False, DTA_MUTEX_LOCAL)
        except Exception:
            self.h_mutex = None

        # 2. Create Shared Memory File Mapping
        try:
            self.shm = mmap.mmap(-1, self.shm_size, tagname=DTA_SHM_GLOBAL, access=mmap.ACCESS_WRITE)
            logger.info("softcam_shm_global_initialized", tag=DTA_SHM_GLOBAL, bytes=self.shm_size)
        except PermissionError:
            try:
                self.shm = mmap.mmap(-1, self.shm_size, tagname=DTA_SHM_LOCAL, access=mmap.ACCESS_WRITE)
                logger.info("softcam_shm_local_initialized", tag=DTA_SHM_LOCAL, bytes=self.shm_size)
            except Exception as e:
                logger.error("softcam_shm_local_failed", error=str(e))
                self.shm = None
        except Exception as e:
            logger.error("softcam_shm_global_failed", error=str(e))
            self.shm = None

    def generate_dta_standby_frame(self) -> np.ndarray:
        """Generate high-tech DTA Studio Standby Screen (1080x1920 9:16)."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Background #090910 BGR: (16, 9, 9)
        frame[:] = (16, 9, 9)

        pad = max(10, min(self.width // 40, self.height // 40))
        # Draw Neon Cyan Outer Border Frame
        cv2.rectangle(frame, (pad, pad), (self.width - pad, self.height - pad), (255, 229, 0), max(2, pad // 2))

        # Render DTA Studio Logo at Center if available
        if not hasattr(self, "_cached_logo_img"):
            self._cached_logo_img = None
            logo_path = Path("src/logo.png")
            if logo_path.exists():
                try:
                    with open(logo_path, "rb") as f:
                        file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                        self._cached_logo_img = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
                except Exception:
                    self._cached_logo_img = None

        logo_img = self._cached_logo_img
        if logo_img is not None:
                lw = min(360, max(80, int(self.width * 0.4)))
                lh = min(360, max(80, int(self.height * 0.2)))

                cy, cx = self.height // 2 - int(self.height * 0.08), self.width // 2
                y1, y2 = max(0, cy - lh // 2), min(self.height, cy + lh // 2)
                x1, x2 = max(0, cx - lw // 2), min(self.width, cx + lw // 2)

                target_w = x2 - x1
                target_h = y2 - y1

                if target_w > 0 and target_h > 0:
                    logo_resized = cv2.resize(logo_img, (target_w, target_h), interpolation=cv2.INTER_AREA)

                    if logo_resized.shape[2] == 4:
                        alpha = logo_resized[:, :, 3] / 255.0
                        for c in range(3):
                            frame[y1:y2, x1:x2, c] = (1.0 - alpha) * frame[y1:y2, x1:x2, c] + alpha * logo_resized[:, :, c]
                    else:
                        frame[y1:y2, x1:x2] = logo_resized

        # Text Overlay
        cx = self.width // 2
        cy = self.height // 2 + int(self.height * 0.08)
        font_scale_title = max(0.5, self.width / 600.0)
        font_scale_sub = max(0.35, self.width / 1200.0)

        # "DTA AUTOLIVE"
        cv2.putText(frame, "DTA AUTOLIVE", (max(10, cx - int(130 * font_scale_title)), cy), cv2.FONT_HERSHEY_SIMPLEX, font_scale_title, (255, 229, 0), 2, cv2.LINE_AA)
        # "PROFESSIONAL LIVE STUDIO"
        cv2.putText(frame, "PROFESSIONAL LIVE STUDIO", (max(10, cx - int(240 * font_scale_sub)), cy + int(40 * font_scale_title)), cv2.FONT_HERSHEY_SIMPLEX, font_scale_sub, (251, 247, 244), 1, cv2.LINE_AA)

        # Pre-flip horizontally for selfie/webcam mirror mode in TikTok LIVE Studio / Zoom
        return cv2.flip(frame, 1)

    def send_standby_frame(self) -> None:
        """Send DTA Studio High-Tech Standby Screen replacing OBS default screen."""
        standby_frame = self.generate_dta_standby_frame()
        self.send_bgr_frame(standby_frame)

    def send_bgr_frame(self, bgr_array: np.ndarray) -> None:
        """Send BGR24 image numpy array (OpenCV format) to DirectShow Camera Driver & Shared Memory."""
        self.frame_counter += 1

        # 1. Push frame to System Virtual Camera Driver (Discord / TikTok Studio / Zoom)
        if self.vcam is not None:
            try:
                self.vcam.send(bgr_array)
            except Exception as e:
                logger.error("vcam_send_failed", error=str(e))

        # 2. Push frame to Shared Memory IPC
        if self.shm is not None:
            if self.h_mutex:
                kernel32.WaitForSingleObject(self.h_mutex, 50)  # Wait up to 50ms

            try:
                raw_bytes = bgr_array.tobytes()

                header = DTASoftcamHeader(
                    magic=DTA_SOFTCAM_MAGIC,
                    width=self.width,
                    height=self.height,
                    fps=self.fps,
                    format=0,  # BGR24
                    frame_index=self.frame_counter,
                    timestamp_ms=int(time.time() * 1000),
                    payload_size=min(len(raw_bytes), self.payload_size),
                )

                header_bytes = bytes(header)
                self.shm.seek(0)
                self.shm.write(header_bytes)
                self.shm.write(raw_bytes[: self.payload_size])
            finally:
                if self.h_mutex:
                    kernel32.ReleaseMutex(self.h_mutex)

    def send_black_frame(self) -> None:
        """Send blank black frame (1080x1920 BGR24)."""
        black_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.send_bgr_frame(black_frame)

    def play_playlist(
        self,
        file_paths: list[str],
        audio_sink: str | None = None,
        on_track_change: Callable[[int, str], None] | None = None,
        on_playlist_ended: Callable[[], None] | None = None,
        on_timeline_sync: Callable[[float, float, int, int], None] | None = None,
    ) -> None:
        """Phát danh sách playlist video tuần tự (phát 1 lần, không lặp lại) với chuyển đổi âm thanh tức thời."""
        self.stop_standby_loop()
        self.stop_video_file()

        valid_paths: list[str] = []
        for fp in file_paths:
            if not fp.startswith(("http://", "https://", "rtmp://", "rtsp://")):
                p = Path(fp)
                if p.exists():
                    valid_paths.append(str(p))
            else:
                valid_paths.append(fp)

        if not valid_paths:
            logger.warning("no_valid_video_in_playlist")
            return

        self._playing_video = True
        self.set_active_video_streaming(True)
        self._video_thread = threading.Thread(
            target=self._playlist_playback_loop,
            args=(valid_paths, audio_sink, on_track_change, on_playlist_ended, on_timeline_sync),
            daemon=True,
        )
        self._video_thread.start()

    def play_video_file(
        self,
        file_path: str,
        audio_sink: str | None = None,
        on_timeline_sync: Callable[[float, float, int, int], None] | None = None,
    ) -> None:
        """Play single video file or stream URL (delegating to playlist engine)."""
        self.play_playlist([file_path], audio_sink=audio_sink, on_timeline_sync=on_timeline_sync)

    def _playlist_playback_loop(
        self,
        file_paths: list[str],
        audio_sink: str | None,
        on_track_change: Callable[[int, str], None] | None,
        on_playlist_ended: Callable[[], None] | None = None,
        on_timeline_sync: Callable[[float, float, int, int], None] | None = None,
    ) -> None:
        """High-performance seamless playlist playback: plays sequentially from start to end without looping."""
        total_items = len(file_paths)
        current_idx = 0

        target_fps = float(self.fps) if self.fps > 0 else 30.0
        frame_interval = 1.0 / target_fps
        loop_frame_idx = 0

        # Start initial audio relay
        if hasattr(self, "audio_relay") and self.audio_relay:
            self.audio_relay.start_audio_relay(file_paths[0], sink_name=audio_sink)

        if on_track_change:
            with contextlib.suppress(Exception):
                on_track_change(0, file_paths[0])

        try:
            while self._playing_video and self._is_active_video_streaming:
                current_file = file_paths[current_idx]
                is_stream = current_file.startswith(("http://", "https://", "rtmp://", "rtsp://"))
                cap = cv2.VideoCapture(current_file)
                if is_stream:
                    with contextlib.suppress(Exception):
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    logger.error("cannot_open_playlist_file", file_path=current_file)
                    current_idx = (current_idx + 1) % total_items
                    time.sleep(0.5)
                    continue

                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                file_fps = cap.get(cv2.CAP_PROP_FPS) or target_fps
                total_duration = float(total_frames / file_fps) if total_frames > 0 and file_fps > 0 else 0.0

                logger.info("playlist_track_started", index=current_idx, file=current_file, duration=total_duration)
                next_frame_time = time.perf_counter()
                track_frame_idx = 0

                while self._playing_video and self._is_active_video_streaming:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    loop_frame_idx += 1
                    track_frame_idx += 1
                    h, w = frame.shape[:2]
                    if w != self.width or h != self.height:
                        frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

                    filters = getattr(self, "active_filters", None) or {}
                    frame = self.apply_anti_duplicate_filters(frame, filters, loop_frame_idx)
                    self.send_bgr_frame(frame)

                    # Master Clock Timeline Sync: Broadcast to UI every 8 frames (~260ms)
                    if on_timeline_sync and (track_frame_idx % 8 == 0):
                        current_sec = float(track_frame_idx / file_fps) if file_fps > 0 else float(track_frame_idx / target_fps)
                        with contextlib.suppress(Exception):
                            on_timeline_sync(current_sec, total_duration, track_frame_idx, current_idx)

                    if is_stream:
                        time.sleep(0.001)
                    else:
                        next_frame_time += frame_interval
                        now = time.perf_counter()
                        sleep_dur = next_frame_time - now
                        if sleep_dur > 0:
                            time.sleep(sleep_dur)
                        elif sleep_dur < -0.1:
                            next_frame_time = now

                cap.release()

                if not self._playing_video or not self._is_active_video_streaming:
                    break

                # Advance to next video
                if total_items == 1:
                    # Video đơn lẻ: phát xong 1 lần thì dừng, không lặp lại
                    break

                current_idx += 1
                if current_idx >= total_items:
                    # Đã phát hết toàn bộ playlist: dừng phát, không lặp lại
                    break

                next_file = file_paths[current_idx]
                if hasattr(self, "audio_relay") and self.audio_relay:
                    self.audio_relay.switch_audio_source(next_file)

                if on_track_change:
                    with contextlib.suppress(Exception):
                        on_track_change(current_idx, next_file)

        except Exception as e:
            logger.error("playlist_playback_loop_error", error=str(e))
        finally:
            self._playing_video = False
            self.set_active_video_streaming(False)
            logger.info("playlist_playback_loop_ended")
            if on_playlist_ended:
                with contextlib.suppress(Exception):
                    on_playlist_ended()

    def stop_video_file(self) -> None:
        """Stop video file playback and fallback to 30 FPS Standby Loop."""
        self._playing_video = False
        if hasattr(self, "_video_thread") and self._video_thread.is_alive():
            self._video_thread.join(timeout=1.0)
        self.set_active_video_streaming(False)

        # Stop audio relay
        if hasattr(self, "audio_relay") and self.audio_relay:
            self.audio_relay.stop_audio_relay()

    def update_filters(self, filter_dict: dict[str, Any]) -> None:
        """Update active anti-duplicate and anti-ban filter settings in real-time."""
        self.active_filters = filter_dict
        logger.info("softcam_engine_filters_updated", filters=filter_dict)

    def apply_anti_duplicate_filters(self, frame: np.ndarray, filters: dict[str, Any], frame_idx: int) -> np.ndarray:
        """Apply real-time multi-dimensional anti-duplicate & anti-ban video filters with studio grading."""
        flip_mirror = filters.get("flip_mirror", True)
        brightness = float(filters.get("brightness", 100.0))
        contrast = float(filters.get("contrast", 100.0))
        saturation = float(filters.get("saturation", 100.0))
        hue = float(filters.get("hue", 0.0))
        zoom = float(filters.get("zoom", 100.0))
        noise_corner = filters.get("noise_corner", True)
        dynamic_breathing = filters.get("dynamic_breathing", True)

        # 1. Horizontal Mirror Flip (Default True for TikTok Selfie / Studio Live)
        if flip_mirror:
            frame = cv2.flip(frame, 1)

        # 2. Studio Brightness & Contrast Adjustment
        if abs(contrast - 100.0) > 0.5 or abs(brightness - 100.0) > 0.5:
            alpha = contrast / 100.0
            beta = (brightness - 100.0) * 0.8
            frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        # 3. Saturation & Hue Grading (Only when user explicitly tweaks)
        if abs(saturation - 100.0) > 0.5 or abs(hue) > 0.5:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            if abs(hue) > 0.5:
                hsv[:, :, 0] = (hsv[:, :, 0] + (hue / 2.0)) % 180.0
            if abs(saturation - 100.0) > 0.5:
                hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (saturation / 100.0), 0, 255)
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 4. Micro Dynamic Zoom & Breathing Crop (Evade Content ID Fixed Frame Detection)
        effective_zoom = zoom
        if dynamic_breathing:
            # Subtle breathing oscillation ±0.8% over a smooth ~6-second cycle (180 frames)
            breathing_factor = np.sin(frame_idx * 0.035) * 0.8
            effective_zoom = max(100.5, zoom + breathing_factor)

        if effective_zoom > 100.5:
            zoom_factor = effective_zoom / 100.0
            crop_w = int(self.width / zoom_factor)
            crop_h = int(self.height / zoom_factor)
            start_x = (self.width - crop_w) // 2
            start_y = (self.height - crop_h) // 2
            cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
            frame = cv2.resize(cropped, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

        # 5. Lightweight Sub-Pixel Noise Injection
        if noise_corner:
            rng = np.random.default_rng()
            noise = rng.integers(-3, 4, size=(8, 8, 3), dtype=np.int16)
            for corner_y, corner_x in [
                (4, 4),
                (4, self.width - 12),
                (self.height - 12, 4),
                (self.height - 12, self.width - 12),
            ]:
                patch = frame[corner_y : corner_y + 8, corner_x : corner_x + 8].astype(np.int16)
                frame[corner_y : corner_y + 8, corner_x : corner_x + 8] = np.clip(patch + noise, 0, 255).astype(np.uint8)

        return frame

    def _video_playback_loop(self, file_path: str) -> None:
        """High-performance background thread reading video/stream frames and delivering to Virtual Camera with zero lag and beautiful studio colors."""
        is_stream = file_path.startswith(("http://", "https://", "rtmp://", "rtsp://"))

        cap = cv2.VideoCapture(file_path)
        if is_stream:
            with contextlib.suppress(Exception):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            logger.error("cannot_open_video_file", file_path=file_path)
            self._playing_video = False
            self.set_active_video_streaming(False)
            return

        logger.info("video_playback_loop_started", file_path=file_path, is_stream=is_stream)
        target_fps = float(self.fps) if self.fps > 0 else 30.0
        frame_interval = 1.0 / target_fps
        next_frame_time = time.perf_counter()
        loop_frame_idx = 0

        try:
            while self._playing_video and self._is_active_video_streaming:
                ret, frame = cap.read()
                if not ret or frame is None:
                    if is_stream:
                        time.sleep(0.05)
                        continue
                    # Hết video: dừng phát ngay lập tức, không lặp lại
                    break

                loop_frame_idx += 1
                h, w = frame.shape[:2]
                if w != self.width or h != self.height:
                    frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

                # Apply Real-time Anti-Duplicate & Studio Color Enhancement
                filters = getattr(self, "active_filters", None) or {}
                frame = self.apply_anti_duplicate_filters(frame, filters, loop_frame_idx)

                # Send directly to pyvirtualcam and Shared Memory
                self.send_bgr_frame(frame)

                # Frame Pacing: Avoid cumulative slow-motion
                if is_stream:
                    # For live stream, cap.read() is already real-time; only yield CPU slightly
                    time.sleep(0.001)
                else:
                    # For local files, synchronize to high-precision wall-clock
                    next_frame_time += frame_interval
                    now = time.perf_counter()
                    sleep_dur = next_frame_time - now
                    if sleep_dur > 0:
                        time.sleep(sleep_dur)
                    elif sleep_dur < -0.1:
                        # Reset clock if lag occurred to prevent catch-up burst
                        next_frame_time = now
        except Exception as e:
            logger.error("video_playback_loop_error", error=str(e))
        finally:
            cap.release()
            self._playing_video = False
            self.set_active_video_streaming(False)
            logger.info("video_playback_loop_stopped_and_reset_to_standby")

    def close(self) -> None:
        """Close Virtual Camera device stream and Shared Memory mapping."""
        self.stop_video_file()
        self.stop_standby_loop()
        if self.vcam:
            with contextlib.suppress(Exception):
                self.vcam.close()
            self.vcam = None

        if self.shm:
            self.shm.close()
            self.shm = None

        if self.h_mutex:
            kernel32.CloseHandle(self.h_mutex)
            self.h_mutex = None

