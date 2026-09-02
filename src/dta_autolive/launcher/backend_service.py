"""Standalone Python Backend Service Runner for DTA AutoLive Electron Edition.

Manages WebSocket Server (ws://127.0.0.1:8765), DTASoftcamEngine Virtual Camera Driver,
Shared Memory IPC, Qwen Local GPU AI Engine, TikTok Shop Cart Scraper, Satellite Seeding
multi-bot network, and Host Live Chatbot in a headless daemon process.
"""

import asyncio
import base64
import contextlib
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import structlog

from dta_autolive.infrastructure.dta_anti_afk import DTAAntiAfkSimulator
from dta_autolive.infrastructure.dta_bgm_player import DTABackgroundMusicPlayer
from dta_autolive.infrastructure.dta_deepseek_engine import DTADeepSeekEngine
from dta_autolive.infrastructure.dta_driver_setup import setup_dta_virtual_hardware_drivers
from dta_autolive.infrastructure.dta_live_studio_controller import DTALiveStudioController
from dta_autolive.infrastructure.dta_qwen_engine import DTAQwenEngine, get_gpu_info
from dta_autolive.infrastructure.dta_softcam_engine import DTASoftcamEngine
from dta_autolive.infrastructure.host_live_chat_responder import HostLiveChatResponder
from dta_autolive.infrastructure.product_pinner import ProductPinnerManager
from dta_autolive.infrastructure.sadcaptcha_engine import (
    CaptchaAutoScannerManager,
    check_sadcaptcha_credits,
)
from dta_autolive.infrastructure.satellite_seeding_manager import SatelliteSeedingManager
from dta_autolive.infrastructure.stream_recorder import LiveStreamRecorder
from dta_autolive.infrastructure.tiktok_cart_scraper import TikTokCartScraper
from dta_autolive.infrastructure.tiktok_live_extractor import (
    extract_cookies_from_chrome_cdp,
    resolve_tiktok_live_stream,
)
from dta_autolive.infrastructure.websocket_server import ExtensionBridgeServer

logger = structlog.get_logger()


class DTABackendService:
    """Headless Background Daemon Service for DTA AutoLive Electron Integration."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.softcam_engine = DTASoftcamEngine(width=1080, height=1920, fps=30)
        self.ws_server = ExtensionBridgeServer(host=host, port=port)
        self.recorder = LiveStreamRecorder()
        self._record_task: asyncio.Task[None] | None = None
        self._running = False
        self._preview_thread: threading.Thread | None = None
        self._preview_running: bool = False
        self._current_preview_url: str = ""

        # DeepSeek V3 Cloud AI Engine
        self.deepseek_engine = DTADeepSeekEngine()

        # Anti-AFK Human-like Mouse Simulator
        self.anti_afk = DTAAntiAfkSimulator(
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg})
        )

        # TikTok LIVE Studio Automation Controller & Auto-Stop State
        self.live_studio_controller = DTALiveStudioController(
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
            event_callback=self.send_ws_command_threadsafe,
        )
        self.auto_stop_live_studio: bool = True

        # Background Music (BGM) Player & Audio Mixer
        self.bgm_player = DTABackgroundMusicPlayer(
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
            event_callback=self.send_ws_command_threadsafe,
        )
        self.video_volume: float = 1.0

        # Next-Gen AI & Automation Engines
        def _on_pinner_event(evt: dict[str, Any]) -> None:
            self.send_ws_command_threadsafe(evt)
            if evt.get("type") == "PIN_EVENT_TRIGGERED" and evt.get("success"):
                if getattr(self.pinner, "auto_callout_enabled", True):
                    callout_text = self.host_responder.handle_pin_callout(evt)
                    self.send_ws_command_threadsafe({
                        "type": "HOST_PIN_CALLOUT_EVENT",
                        "product_id": evt.get("product_id"),
                        "callout": callout_text,
                        "timestamp": time.time(),
                    })
                if getattr(self.pinner, "seeding_support_enabled", True):
                    seeding_text = self.seeding_manager.handle_pin_seeding_support(evt)
                    self.send_ws_command_threadsafe({
                        "type": "SEEDING_SUPPORT_EVENT",
                        "product_id": evt.get("product_id"),
                        "comment": seeding_text,
                        "timestamp": time.time(),
                    })

        self.pinner = ProductPinnerManager(
            status_callback=lambda status, col: self.send_ws_command_threadsafe({
                "type": "PIN_STATUS_UPDATE",
                "status": status,
                "color": col,
            }),
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
            event_callback=_on_pinner_event,
        )
        self.qwen_engine = DTAQwenEngine(
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
        )
        self.cart_scraper = TikTokCartScraper(
            cdp_port=9222,
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
        )
        self.seeding_manager = SatelliteSeedingManager(
            qwen_engine=self.qwen_engine,
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
            status_callback=lambda status, col: self.send_ws_command_threadsafe({
                "type": "SEEDING_STATUS_UPDATE",
                "status": status,
                "color": col,
            }),
        )
        self.host_responder = HostLiveChatResponder(
            qwen_engine=self.qwen_engine,
            deepseek_engine=self.deepseek_engine,
            ai_provider="auto",
            cdp_port=9222,
            log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
            status_callback=lambda status, col: self.send_ws_command_threadsafe({
                "type": "HOST_CHATBOT_STATUS_UPDATE",
                "status": status,
                "color": col,
            }),
            auto_pin_callback=self.pinner.pin_priority_product,
            event_callback=self.send_ws_command_threadsafe,
        )

    async def start(self) -> None:
        """Start Backend Service daemon."""
        self._running = True
        self._shutdown_event = asyncio.Event()
        self.loop = asyncio.get_running_loop()
        logger.info("dta_backend_service_starting", host=self.host, port=self.port)

        self.ws_server.register_command_callback(self._on_command_received)

        # Kích hoạt luồng phát màn hình chờ DTA Studio 30 FPS ngay lập tức
        self.softcam_engine.start_standby_loop()

        # Start WebSocket Server
        try:
            await self.ws_server.start()
            logger.info("dta_backend_service_ready", websocket_url=f"ws://{self.host}:{self.port}")
        except OSError as e:
            logger.warning("dta_backend_ws_port_in_use", error=str(e), msg="WebSocket server already running or port occupied.")

        # Service loop keep-alive
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("dta_backend_service_cancelled")
        finally:
            await self.stop()

    def send_ws_command_threadsafe(self, payload: dict[str, Any]) -> None:
        """Thread-safe coroutine dispatch for sending WebSocket message to clients."""
        if not hasattr(self, "ws_server") or not self.ws_server:
            return
        if hasattr(self, "loop") and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.ws_server.send_command(payload), self.loop)
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.ws_server.send_command(payload))
            except Exception:
                pass

    def start_preview_relay(self, stream_url: str) -> None:
        """Stream low-latency live preview frames over WebSocket at 20 FPS."""
        self.stop_preview_relay()
        if not stream_url:
            return
        self._current_preview_url = stream_url
        self._preview_running = True
        self._preview_thread = threading.Thread(
            target=self._preview_relay_worker,
            args=(stream_url,),
            daemon=True,
        )
        self._preview_thread.start()

    def stop_preview_relay(self) -> None:
        """Stop background preview relay worker."""
        self._preview_running = False
        if self._preview_thread and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=0.5)
        self._preview_thread = None

    def _preview_relay_worker(self, url: str) -> None:
        """Read stream frames with OpenCV and broadcast compressed JPEG frames."""
        logger.info("live_preview_relay_worker_started", url=url)
        cap = cv2.VideoCapture(url)
        with contextlib.suppress(Exception):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            logger.warning("cannot_open_preview_relay_stream", url=url)
            return

        frame_interval = 1.0 / 20.0  # 20 FPS
        next_time = time.perf_counter()

        try:
            while self._preview_running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                h, w = frame.shape[:2]
                target_w, target_h = 360, 640
                if w != target_w or h != target_h:
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

                # Encode as fast JPEG quality 65
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
                _, encimg = cv2.imencode(".jpg", frame, encode_param)
                b64_str = base64.b64encode(encimg.tobytes()).decode("ascii")

                self.send_ws_command_threadsafe({
                    "type": "LIVE_PREVIEW_FRAME",
                    "frame": b64_str,
                })

                next_time += frame_interval
                sleep_dur = next_time - time.perf_counter()
                if sleep_dur > 0:
                    time.sleep(sleep_dur)
                else:
                    next_time = time.perf_counter()
        except Exception as err:
            logger.error("live_preview_relay_error", error=str(err))
        finally:
            cap.release()
            logger.info("live_preview_relay_worker_stopped")

    def _on_command_received(self, data: dict[str, Any]) -> None:  # noqa: PLR0912, PLR0915
        """Handle incoming command messages from Electron UI or Chrome Extension."""
        cmd = data.get("command") or data.get("type")
        file_path = data.get("file_path") or "sample_dta_live_1080x1920.mp4"

        logger.info("backend_command_received", command=cmd, file_path=file_path)

        mode = data.get("mode", "file")
        stream_url = data.get("stream_url", "")
        audio_sink = data.get("audio_sink", "cable")
        auto_record = data.get("auto_record", False) or data.get("record", False)
        record_dir = data.get("record_dir")
        channel_name = data.get("channel_name", "TikTokLive")

        if cmd in ("START_LIVE", "PLAY_VIDEO"):
            playlist_items: list[str] = data.get("playlist") or data.get("playlist_files") or []
            if "auto_stop_live_studio" in data:
                self.auto_stop_live_studio = bool(data.get("auto_stop_live_studio", True))

            def _on_track_changed(idx: int, path: str) -> None:
                self.send_ws_command_threadsafe({
                    "type": "PLAYLIST_TRACK_CHANGED",
                    "index": idx,
                    "file_path": path,
                })

            def _on_playlist_ended() -> None:
                self.send_ws_command_threadsafe({
                    "type": "PLAYLIST_ENDED",
                    "message": "Đã phát hết toàn bộ video trong danh sách phát.",
                })
                if self.auto_stop_live_studio:
                    self.send_ws_command_threadsafe({
                        "type": "LOG",
                        "level": "ACTION",
                        "message": "🛑 [Hết Video] Đang kích hoạt tự động tắt Livestream trên TikTok LIVE Studio...",
                    })
                    self.live_studio_controller.trigger_async_stop_live()

            def _on_timeline_sync(curr_sec: float, dur_sec: float, frame_idx: int, track_idx: int) -> None:
                self.send_ws_command_threadsafe({
                    "type": "TIMELINE_SYNC",
                    "current_seconds": round(curr_sec, 2),
                    "duration_seconds": round(dur_sec, 2),
                    "frame_index": frame_idx,
                    "track_index": track_idx,
                })

            if mode == "url" and stream_url:
                logger.info("starting_tiktok_live_relay_stream", stream_url=stream_url, audio_sink=audio_sink, auto_record=auto_record)
                self.softcam_engine.play_video_file(stream_url, audio_sink=audio_sink, on_timeline_sync=_on_timeline_sync)
                if auto_record:
                    self._start_stream_recording(stream_url, record_dir, channel_name)
            elif playlist_items and len(playlist_items) > 0:
                logger.info("starting_playlist_playback", count=len(playlist_items), audio_sink=audio_sink)
                self.softcam_engine.play_playlist(
                    playlist_items,
                    audio_sink=audio_sink,
                    on_track_change=_on_track_changed,
                    on_playlist_ended=_on_playlist_ended,
                    on_timeline_sync=_on_timeline_sync,
                )
            else:
                p = Path(file_path).resolve()
                if not p.exists():
                    p = (Path.cwd() / file_path).resolve()
                if not p.exists():
                    logger.warning("specified_video_not_found_fallback_sample", path=str(p))
                    p = (Path.cwd() / "sample_dta_live_1080x1920.mp4").resolve()

                logger.info("starting_video_file_playback", resolved_path=str(p), audio_sink=audio_sink)
                self.softcam_engine.play_playlist(
                    [str(p)],
                    audio_sink=audio_sink,
                    on_track_change=_on_track_changed,
                    on_playlist_ended=_on_playlist_ended,
                    on_timeline_sync=_on_timeline_sync,
                )
        elif cmd in ("PAUSE_LIVE", "STOP_LIVE"):
            logger.info("stopping_video_playback")
            self.softcam_engine.stop_video_file()
            self._stop_stream_recording()
            # Clean up active seeding and live bot when live stops
            if self.seeding_manager.is_running:
                self.seeding_manager.stop_seeding()
            if self.host_responder.is_running:
                self.host_responder.stop_responder()
        elif cmd == "START_RECORDING":
            target_url = data.get("stream_url", "")
            target_dir = data.get("record_dir")
            target_channel = data.get("channel_name", "TikTokLive")
            if target_url:
                self._start_stream_recording(target_url, target_dir, target_channel)
        elif cmd == "STOP_RECORDING":
            self._stop_stream_recording()
        elif cmd == "START_PREVIEW_STREAM":
            target_url = data.get("stream_url", "")
            if target_url:
                self.start_preview_relay(target_url)
        elif cmd == "STOP_PREVIEW_STREAM":
            self.stop_preview_relay()
        elif cmd in ("RESOLVE_TIKTOK_LIVE", "TIKTOK_LIVE_SNIFFED"):
            target_url = data.get("stream_url") or data.get("url") or data.get("page_url", "")
            req_cookies = data.get("cookies", "")
            logger.info("resolving_tiktok_live_stream_url", url=target_url, source=cmd, has_cookies=bool(req_cookies))

            async def _resolve_worker(url: str, cookies: str) -> None:
                try:
                    stream_info = await asyncio.to_thread(resolve_tiktok_live_stream, url, cookies)
                    if stream_info.get("success") and stream_info.get("stream_url"):
                        self.start_preview_relay(stream_info.get("stream_url", ""))
                    self.send_ws_command_threadsafe({
                        "type": "TIKTOK_LIVE_RESOLVED",
                        "data": stream_info,
                    })
                except Exception as err:
                    self.send_ws_command_threadsafe({
                        "type": "TIKTOK_LIVE_RESOLVED",
                        "data": {
                            "success": False,
                            "error": f"Lỗi phân giải luồng: {err}",
                        },
                    })

            if hasattr(self, "loop") and self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(_resolve_worker(target_url, req_cookies), self.loop)
            else:
                asyncio.create_task(_resolve_worker(target_url, req_cookies))
        elif cmd == "SNIFF_TIKTOK_COOKIES_CDP":
            port = data.get("cdp_port", 9222)
            logger.info("sniffing_tiktok_cookies_from_cdp", port=port)

            async def _sniff_worker(p: int) -> None:
                try:
                    c_info = await asyncio.to_thread(extract_cookies_from_chrome_cdp, p)
                    self.send_ws_command_threadsafe({
                        "type": "TIKTOK_COOKIES_SNIFFED",
                        "data": c_info,
                    })
                except Exception as err:
                    self.send_ws_command_threadsafe({
                        "type": "TIKTOK_COOKIES_SNIFFED",
                        "data": {"success": False, "error": str(err)},
                    })

            if hasattr(self, "loop") and self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(_sniff_worker(port), self.loop)
            else:
                asyncio.create_task(_sniff_worker(port))
        elif cmd == "REGISTER_DEVICES":
            logger.info("registering_dta_virtual_devices")
            success, setup_logs = setup_dta_virtual_hardware_drivers()
            for log_line in setup_logs:
                logger.info("dta_driver_setup_log", detail=log_line)
            self.send_ws_command_threadsafe({
                "type": "DEVICES_REGISTERED",
                "success": success,
                "logs": setup_logs,
            })
        elif cmd == "UPDATE_FILTERS":
            filters = data.get("filters", {})
            logger.info("updating_anti_duplicate_filters", filters=filters)
            if hasattr(self.softcam_engine, "update_filters"):
                self.softcam_engine.update_filters(filters)

        # -------------------------------------------------------------
        # NEXT-GEN AI QWEN & GPU VRAM LIFECYCLE HANDLERS
        # -------------------------------------------------------------
        elif cmd == "CHECK_AI_MODEL":
            model_key = data.get("model_key", "Qwen2.5-7B-Instruct-Q4_K_M")
            status = self.qwen_engine.check_model_status(model_key)
            self.send_ws_command_threadsafe({
                "type": "AI_MODEL_STATUS_RESULT",
                "data": status,
            })
        elif cmd == "DOWNLOAD_AI_MODEL":
            model_key = data.get("model_key", "Qwen2.5-7B-Instruct-Q4_K_M")

            def _on_dl_progress(pdata: dict[str, Any]) -> None:
                self.send_ws_command_threadsafe({
                    "type": "AI_MODEL_DOWNLOAD_PROGRESS",
                    "data": pdata,
                })

            ok = self.qwen_engine.start_download(model_key, progress_callback=_on_dl_progress)
            self.send_ws_command_threadsafe({
                "type": "AI_MODEL_DOWNLOAD_STARTED",
                "success": ok,
                "model_key": model_key,
            })
        elif cmd == "CANCEL_DOWNLOAD_AI_MODEL":
            self.qwen_engine.cancel_download()
            self.send_ws_command_threadsafe({"type": "AI_MODEL_DOWNLOAD_CANCELLED", "success": True})
        elif cmd == "DELETE_AI_MODEL":
            model_key = data.get("model_key", "Qwen2.5-7B-Instruct-Q4_K_M")
            res = self.qwen_engine.delete_model(model_key)
            self.send_ws_command_threadsafe({
                "type": "AI_MODEL_DELETED_RESULT",
                "data": res,
            })
        elif cmd == "OPEN_MODELS_FOLDER":
            models_path = str(self.qwen_engine.models_dir)
            if sys.platform == "win32":
                try:
                    os.startfile(models_path)  # noqa: S606
                except Exception as e:
                    logger.warning("failed_to_open_models_folder", error=str(e))
            self.send_ws_command_threadsafe({
                "type": "MODELS_FOLDER_OPENED",
                "path": models_path,
            })
        elif cmd == "START_AI_GPU_SERVER":
            model_key = data.get("model_key", "Qwen2.5-7B-Instruct-Q4_K_M")
            n_gpu = int(data.get("n_gpu_layers", -1))
            n_ctx = int(data.get("n_ctx", 4096))

            def _load_worker() -> None:
                loaded = self.qwen_engine.load_model_to_gpu(model_key, n_gpu_layers=n_gpu, n_ctx=n_ctx)
                status = self.qwen_engine.check_model_status(model_key)
                self.send_ws_command_threadsafe({
                    "type": "AI_GPU_SERVER_RESULT",
                    "success": loaded,
                    "model_key": model_key,
                    "status": status,
                })

            threading.Thread(target=_load_worker, daemon=True).start()
        elif cmd == "STOP_AI_GPU_SERVER":
            self.qwen_engine.unload_model_and_clean_gpu()
            status = self.qwen_engine.check_model_status()
            self.send_ws_command_threadsafe({
                "type": "AI_GPU_SERVER_STOPPED",
                "success": True,
                "status": status,
            })
        elif cmd == "GET_GPU_TELEMETRY":
            gpu_info = get_gpu_info()
            self.send_ws_command_threadsafe({
                "type": "GPU_TELEMETRY_RESULT",
                "data": gpu_info,
            })

        # -------------------------------------------------------------
        # TIKTOK SHOP CART SCRAPER HANDLERS
        # -------------------------------------------------------------
        elif cmd == "SCRAPE_TIKTOK_CART":
            def _scrape_worker() -> None:
                res = self.cart_scraper.scrape_cart()
                # Update knowledge base across engines & detect domain
                if res.get("products"):
                    prods = res["products"]
                    self.seeding_manager.products_catalog = prods
                    self.pinner.products_catalog = prods
                    detected_dom = self.host_responder.update_catalog(prods)
                    res["detected_domain"] = detected_dom
                self.send_ws_command_threadsafe({
                    "type": "TIKTOK_CART_SCRAPED_RESULT",
                    "data": res,
                })

            threading.Thread(target=_scrape_worker, daemon=True).start()

        # -------------------------------------------------------------
        # SATELLITE SEEDING ENGINE HANDLERS
        # -------------------------------------------------------------
        elif cmd == "START_SATELLITE_SEEDING":
            target_user = data.get("username", "")
            accounts_txt = data.get("accounts_text", "")
            interval_min = int(data.get("interval_min", 15))
            interval_max = int(data.get("interval_max", 45))
            style = data.get("seeding_style", "mixed")
            ai_prompt = data.get("ai_prompt", "")
            custom_templates = data.get("custom_templates", [])
            region_dialect = data.get("region_dialect", "south")
            tone_style = data.get("tone_style", "genz_casual")
            use_slangs = bool(data.get("use_slangs", True))
            prods = data.get("products") or self.cart_scraper.cached_products
            if prods:
                self.cart_scraper.cached_products = prods
                self.seeding_manager.products_catalog = prods
                self.pinner.products_catalog = prods
                self.host_responder.update_catalog(prods)
            ok = self.seeding_manager.start_seeding(
                target_username=target_user,
                accounts_text=accounts_txt,
                interval_min=interval_min,
                interval_max=interval_max,
                seeding_style=style,
                ai_prompt=ai_prompt,
                custom_templates=custom_templates,
                products_catalog=prods,
                region_dialect=region_dialect,
                tone_style=tone_style,
                use_slangs=use_slangs,
            )
            self.send_ws_command_threadsafe({
                "type": "SATELLITE_SEEDING_STARTED",
                "success": ok,
            })
        elif cmd == "STOP_SATELLITE_SEEDING":
            self.seeding_manager.stop_seeding()
            self.send_ws_command_threadsafe({
                "type": "SATELLITE_SEEDING_STOPPED",
                "success": True,
            })
        elif cmd == "SEND_QUICK_TEST_COMMENT":
            comment_txt = data.get("comment", "")
            if comment_txt:
                self.seeding_manager.send_single_comment(comment_txt)
            self.send_ws_command_threadsafe({
                "type": "QUICK_TEST_COMMENT_SENT",
                "comment": comment_txt,
            })
        elif cmd == "SYNC_CART_PRODUCTS_CATALOG":
            prods = data.get("products", [])
            if prods:
                self.cart_scraper.cached_products = prods
                self.seeding_manager.products_catalog = prods
                self.pinner.products_catalog = prods
                detected_dom = self.host_responder.update_catalog(prods)
                logger.info("sync_cart_catalog_success", count=len(prods), domain=detected_dom)
            self.send_ws_command_threadsafe({
                "type": "CART_CATALOG_SYNCED",
                "count": len(prods),
                "success": True,
            })
        elif cmd == "GENERATE_CART_SEEDING_TEMPLATES":
            prods = data.get("products") or self.cart_scraper.cached_products
            region_dialect = data.get("region_dialect", "south")
            tone_style = data.get("tone_style", "genz_casual")
            use_slangs = bool(data.get("use_slangs", True))
            if prods:
                self.cart_scraper.cached_products = prods
                self.seeding_manager.products_catalog = prods
                self.pinner.products_catalog = prods
                self.host_responder.update_catalog(prods)
            templates = self.seeding_manager.generate_cart_product_seeding_scripts(
                products=prods,
                region_dialect=region_dialect,
                tone_style=tone_style,
                use_slangs=use_slangs,
            )
            self.send_ws_command_threadsafe({
                "type": "CART_SEEDING_TEMPLATES_GENERATED",
                "templates": templates,
                "count": len(templates),
            })

        # -------------------------------------------------------------
        # HOST LIVE CHATBOT AUTO-RESPONDER HANDLERS
        # -------------------------------------------------------------
        elif cmd == "START_HOST_AI_CHATBOT":
            target_user = data.get("username", "")
            prompt = data.get("system_prompt", "")
            region_dialect = data.get("region_dialect", "south")
            tone_style = data.get("tone_style", "genz_casual")
            use_slangs = bool(data.get("use_slangs", True))
            prods = data.get("products") or self.cart_scraper.cached_products
            if prods:
                self.cart_scraper.cached_products = prods
                self.pinner.products_catalog = prods
                self.seeding_manager.products_catalog = prods
                self.host_responder.update_catalog(prods)
            self.host_responder.region_dialect = region_dialect
            self.host_responder.tone_style = tone_style
            self.host_responder.use_slangs = use_slangs
            ok = self.host_responder.start_responder(
                username=target_user,
                system_prompt=prompt,
                knowledge_catalog_text=self.host_responder.knowledge_catalog_text,
            )
            self.send_ws_command_threadsafe({
                "type": "HOST_AI_CHATBOT_STARTED",
                "success": ok,
            })
        elif cmd == "STOP_HOST_AI_CHATBOT":
            self.host_responder.stop_responder()
            self.send_ws_command_threadsafe({
                "type": "HOST_AI_CHATBOT_STOPPED",
                "success": True,
            })
        elif cmd == "TEST_HOST_AI_CHATBOT_REPLY":
            cust_name = data.get("customer", "Khach_Hang_Test")
            question = data.get("question", "")
            prompt = data.get("system_prompt", "")
            region_dialect = data.get("region_dialect", "south")
            tone_style = data.get("tone_style", "genz_casual")
            use_slangs = bool(data.get("use_slangs", True))
            prods = data.get("products") or self.cart_scraper.cached_products
            if prods:
                self.cart_scraper.cached_products = prods
                self.pinner.products_catalog = prods
                self.seeding_manager.products_catalog = prods
                self.host_responder.update_catalog(prods)
            if prompt:
                self.host_responder.system_prompt = prompt
            self.host_responder.region_dialect = region_dialect
            self.host_responder.tone_style = tone_style
            self.host_responder.use_slangs = use_slangs

            # Ghi nhận lượt hỏi vào nhiệt kế quan tâm
            matched = self.host_responder.find_matched_product(question)
            if matched:
                self.pinner.record_product_interest(matched.get("stt", 1))
            res = self.host_responder.generate_test_response(
                customer_name=cust_name,
                question=question,
                region_dialect=region_dialect,
                tone_style=tone_style,
                use_slangs=use_slangs,
            )
            self.send_ws_command_threadsafe({
                "type": "HOST_CHATBOT_REPLY_EVENT",
                "data": res,
            })
        elif cmd == "BENCHMARK_AI_SPEED":
            prods = data.get("products") or self.cart_scraper.cached_products
            if prods:
                self.cart_scraper.cached_products = prods
                self.host_responder.products_catalog = prods
                self.host_responder.knowledge_catalog_text = self.cart_scraper.format_knowledge_base_text(prods)
            bench_res = self.host_responder.benchmark_response_speed()
            self.send_ws_command_threadsafe({
                "type": "AI_BENCHMARK_RESULT",
                "data": bench_res,
            })

        # -------------------------------------------------------------
        # LEGACY CAPTCHA & PINNER HANDLERS (MAINTAINED 100%)
        # -------------------------------------------------------------
        elif cmd == "CHECK_SADCAPTCHA_CREDITS":
            api_key = data.get("api_key", "")
            remaining_credits = check_sadcaptcha_credits(api_key)
            self.send_ws_command_threadsafe({
                "type": "SADCAPTCHA_CREDITS_RESULT",
                "credits": remaining_credits or 25,
            })
        elif cmd == "LAUNCH_TIKTOK_SHOP_CHROME":
            self.pinner.launch_browser()
            logger.info("launched_tiktok_shop_chrome")
        elif cmd in ("TEST_PIN_PRODUCT", "TRIGGER_MANUAL_PIN"):
            pid = data.get("product_id", "1")
            self.pinner.products_catalog = self.cart_scraper.cached_products
            threading.Thread(target=self.pinner.test_pin_single_product, args=(pid,), daemon=True).start()
        elif cmd == "START_AUTO_PIN":
            product_list = data.get("product_list", "1, 2, 3, 4, 5")
            interval = int(data.get("interval", 10))
            mode = data.get("mode", "ping_pong")
            keyword_map = data.get("keyword_map", "")
            auto_scroll = bool(data.get("auto_scroll", False))
            random_interval = bool(data.get("random_interval", True))
            interval_min = data.get("interval_min")
            interval_max = data.get("interval_max")
            self.pinner.auto_callout_enabled = bool(data.get("auto_callout", True))
            self.pinner.seeding_support_enabled = bool(data.get("seeding_support", True))
            self.pinner.products_catalog = self.cart_scraper.cached_products
            self.pinner.start_pinning(
                product_list,
                interval,
                mode=mode,
                keyword_map_str=keyword_map,
                auto_scroll=auto_scroll,
                random_interval=random_interval,
                interval_min=interval_min,
                interval_max=interval_max,
            )
        elif cmd == "STOP_AUTO_PIN":
            self.pinner.stop_pinning()
        elif cmd == "GET_PIN_ANALYTICS":
            summary = self.pinner.get_analytics_summary()
            self.send_ws_command_threadsafe({
                "type": "PIN_ANALYTICS_RESULT",
                "data": summary,
            })
        elif cmd == "START_CAPTCHA_SCAN":
            api_key = data.get("api_key", "")
            scan_interval = float(data.get("interval", 2.0))
            if not hasattr(self, "captcha_scanner"):
                self.captcha_scanner = CaptchaAutoScannerManager(
                    log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
                    status_callback=lambda status, col: self.send_ws_command_threadsafe({"type": "CAPTCHA_STATUS", "status": status, "color": col}),
                    event_callback=self.send_ws_command_threadsafe,
                )
            self.captcha_scanner.start_scan(api_key, scan_interval)
        elif cmd == "STOP_CAPTCHA_SCAN":
            if hasattr(self, "captcha_scanner"):
                self.captcha_scanner.stop_scan()
        elif cmd == "TRIGGER_MANUAL_CAPTCHA_SOLVE":
            api_key = data.get("api_key", "")
            if not hasattr(self, "captcha_scanner"):
                self.captcha_scanner = CaptchaAutoScannerManager(
                    log_callback=lambda tag, msg: self.send_ws_command_threadsafe({"type": "LOG", "level": tag, "message": msg}),
                    status_callback=lambda status, col: self.send_ws_command_threadsafe({"type": "CAPTCHA_STATUS", "status": status, "color": col}),
                    event_callback=self.send_ws_command_threadsafe,
                )
            threading.Thread(target=self.captcha_scanner.solve_manual, args=(api_key,), daemon=True).start()
        elif cmd == "START_ANTI_AFK":
            self.anti_afk.start()
            self.send_ws_command_threadsafe({
                "type": "ANTI_AFK_STATUS",
                "status": "ACTIVE",
                "color": "#00FF66",
            })
        elif cmd == "STOP_ANTI_AFK":
            self.anti_afk.stop()
            self.send_ws_command_threadsafe({
                "type": "ANTI_AFK_STATUS",
                "status": "STOPPED",
                "color": "#888888",
            })
        elif cmd == "SAVE_API_KEYS":
            sadcaptcha_key = data.get("sadcaptcha_key", "")
            deepseek_key = data.get("deepseek_key", "")
            ai_provider = data.get("ai_provider", "auto")

            if hasattr(self, "captcha_scanner") and sadcaptcha_key:
                self.captcha_scanner.api_key = sadcaptcha_key
            if deepseek_key:
                self.deepseek_engine.set_api_key(deepseek_key)
            self.host_responder.ai_provider = ai_provider

            self.send_ws_command_threadsafe({
                "type": "API_KEYS_SAVED",
                "success": True,
                "deepseek_configured": self.deepseek_engine.is_configured,
                "ai_provider": ai_provider,
            })
            self.send_ws_command_threadsafe({
                "type": "LOG",
                "level": "SUCCESS",
                "message": f"💾 [Cấu Hình AI] Đã lưu API Keys thành công (AI Provider: {ai_provider.upper()}).",
            })
        elif cmd == "TEST_DEEPSEEK_API_KEY":
            deepseek_key = data.get("api_key", "") or self.deepseek_engine.api_key
            logger.info("testing_deepseek_api_key_requested")
            self.send_ws_command_threadsafe({
                "type": "LOG",
                "level": "ACTION",
                "message": "⚡ [DeepSeek V3] Đang gửi yêu cầu kiểm tra kết nối API tới máy chủ DeepSeek...",
            })

            def _test_worker() -> None:
                res = self.deepseek_engine.test_connection(deepseek_key)
                if res.get("success"):
                    self.send_ws_command_threadsafe({
                        "type": "LOG",
                        "level": "SUCCESS",
                        "message": f"🎉 [DeepSeek V3] {res.get('message')}",
                    })
                else:
                    self.send_ws_command_threadsafe({
                        "type": "LOG",
                        "level": "ERROR",
                        "message": f"❌ [DeepSeek V3] {res.get('message')}",
                    })
                self.send_ws_command_threadsafe({
                    "type": "DEEPSEEK_TEST_RESULT",
                    "data": res,
                })

            threading.Thread(target=_test_worker, daemon=True).start()
        elif cmd == "SET_AI_ENGINE_PROVIDER":
            provider = data.get("provider", "auto")
            self.host_responder.ai_provider = provider
            self.send_ws_command_threadsafe({
                "type": "AI_ENGINE_PROVIDER_UPDATED",
                "provider": provider,
            })
        elif cmd == "SET_HOST_PROMPT_CONFIG":
            prompt_tmpl = data.get("prompt_template", "")
            plat_info = data.get("platform_info", "")
            rules = data.get("rules", "")

            self.host_responder.set_prompt_configuration(
                prompt_template=prompt_tmpl,
                platform_info=plat_info,
                rules=rules,
            )
            self.send_ws_command_threadsafe({
                "type": "HOST_PROMPT_CONFIG_SAVED",
                "success": True,
            })
            self.send_ws_command_threadsafe({
                "type": "LOG",
                "level": "SUCCESS",
                "message": "💾 [Host Prompt] Đã cập nhật Kịch bản & 3 biến {{Thong tin nen tang}}, {{List san pham}}, {{Quy tac}} vào máy chủ AI.",
            })
        elif cmd == "TEST_STOP_TIKTOK_LIVE_STUDIO":
            logger.info("testing_stop_tiktok_live_studio_requested")
            self.send_ws_command_threadsafe({
                "type": "LOG",
                "level": "ACTION",
                "message": "⚡ [Thử Nghiệm] Đang kích hoạt quy trình tự động tắt TikTok LIVE Studio...",
            })
            self.live_studio_controller.trigger_async_stop_live()
        elif cmd == "SET_AUTO_STOP_LIVE_STUDIO":
            self.auto_stop_live_studio = bool(data.get("enabled", True))
            logger.info("auto_stop_live_studio_setting_updated", enabled=self.auto_stop_live_studio)
            self.send_ws_command_threadsafe({
                "type": "AUTO_STOP_LIVE_STUDIO_UPDATED",
                "enabled": self.auto_stop_live_studio,
            })
        elif cmd == "START_CALIBRATE_LIVE_STUDIO":
            logger.info("starting_live_studio_calibration")
            self.live_studio_controller.start_coordinate_calibration()
        elif cmd == "CANCEL_CALIBRATE_LIVE_STUDIO":
            logger.info("cancelling_live_studio_calibration")
            self.live_studio_controller.cancel_coordinate_calibration()
        elif cmd == "CLEAR_CALIBRATE_LIVE_STUDIO":
            logger.info("clearing_live_studio_custom_coords")
            self.live_studio_controller.clear_custom_coordinates()
            self.send_ws_command_threadsafe({
                "type": "LIVE_STUDIO_COORDS_RESULT",
                "is_calibrated": False,
                "data": {},
            })
        elif cmd == "GET_CALIBRATE_LIVE_STUDIO_COORDS":
            coords = self.live_studio_controller.custom_points
            is_cal = bool(coords and coords.get("is_calibrated"))
            self.send_ws_command_threadsafe({
                "type": "LIVE_STUDIO_COORDS_RESULT",
                "is_calibrated": is_cal,
                "data": coords,
            })

        # -------------------------------------------------------------
        # BACKGROUND MUSIC (BGM) & AUDIO MIXER HANDLERS
        # -------------------------------------------------------------
        elif cmd == "START_BGM":
            folder = data.get("folder", "") or self.bgm_player.current_folder
            vol = float(data.get("volume", self.bgm_player.volume))
            sink = data.get("sink_name") or getattr(self.softcam_engine, "active_audio_sink", None)
            shuffle = bool(data.get("shuffle", False))
            self.bgm_player.start_bgm(folder_path=folder, volume=vol, sink_name=sink, shuffle=shuffle)
        elif cmd == "STOP_BGM":
            self.bgm_player.stop_bgm()
        elif cmd == "SET_BGM_VOLUME":
            vol = float(data.get("volume", 0.3))
            self.bgm_player.set_volume(vol)
            self.send_ws_command_threadsafe({"type": "BGM_VOLUME_UPDATED", "volume": vol})
        elif cmd == "SET_VIDEO_VOLUME":
            vol = float(data.get("volume", 1.0))
            self.video_volume = vol
            if hasattr(self.softcam_engine, "audio_relay") and self.softcam_engine.audio_relay:
                self.softcam_engine.audio_relay.set_volume(vol)
            self.send_ws_command_threadsafe({"type": "VIDEO_VOLUME_UPDATED", "volume": vol})
        elif cmd == "SCAN_BGM_FOLDER":
            folder = data.get("folder", "")
            tracks = self.bgm_player.scan_music_folder(folder)
            self.send_ws_command_threadsafe({
                "type": "BGM_FOLDER_SCANNED",
                "folder": folder,
                "total_tracks": len(tracks),
                "tracks": [Path(t).name for t in tracks[:50]],
            })
        elif cmd == "NEXT_BGM_TRACK":
            self.bgm_player.next_track()
        elif cmd == "GET_BGM_STATUS":
            st = self.bgm_player.get_status()
            st["video_volume"] = self.video_volume
            self.send_ws_command_threadsafe({"type": "BGM_STATUS_RESULT", "data": st})

    def _start_stream_recording(
        self,
        stream_url: str,
        output_dir: str | None = None,
        channel_name: str = "TikTokLive",
    ) -> None:
        """Start FFmpeg recording worker and progress broadcasting loop."""
        try:
            out_file = self.recorder.start_recording(
                stream_url=stream_url,
                output_dir=output_dir,
                channel_name=channel_name,
            )
            self.send_ws_command_threadsafe({
                "type": "RECORDING_STARTED",
                "file_path": str(out_file),
                "file_name": out_file.name,
            })

            async def _progress_loop() -> None:
                while self.recorder.is_recording:
                    stats = self.recorder.get_stats()
                    self.send_ws_command_threadsafe({
                        "type": "RECORD_PROGRESS",
                        "stats": stats,
                    })
                    await asyncio.sleep(1.0)

            if hasattr(self, "loop") and self.loop and self.loop.is_running():
                self._record_task = asyncio.run_coroutine_threadsafe(_progress_loop(), self.loop)  # type: ignore[assignment]
            else:
                self._record_task = asyncio.create_task(_progress_loop())
        except Exception as e:
            logger.error("start_stream_recording_failed", error=str(e))
            self.send_ws_command_threadsafe({
                "type": "RECORDING_ERROR",
                "error": f"Lỗi khởi động ghi hình: {e}",
            })

    def _stop_stream_recording(self) -> None:
        """Stop FFmpeg recording worker and notify UI with final file info."""
        if not self.recorder.is_recording:
            return

        final_file = self.recorder.stop_recording()
        if self._record_task and not self._record_task.done():
            self._record_task.cancel()
            self._record_task = None

        if final_file and final_file.exists():
            size_bytes = final_file.stat().st_size
            size_mb = round(size_bytes / (1024 * 1024), 2)
            self.send_ws_command_threadsafe({
                "type": "RECORD_FINISHED",
                "file_path": str(final_file),
                "file_name": final_file.name,
                "size_mb": size_mb,
                "size_formatted": f"{size_mb} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB",
            })

    async def stop(self) -> None:
        """Stop Backend Service, release hardware drivers and GPU memory."""
        if not self._running:
            return
        self._running = False
        self._stop_stream_recording()

        # Shutdown next-gen engines and clean VRAM
        if hasattr(self, "bgm_player"):
            self.bgm_player.stop_bgm()
        if hasattr(self, "seeding_manager"):
            self.seeding_manager.stop_seeding()
        if hasattr(self, "host_responder"):
            self.host_responder.stop_responder()
        if hasattr(self, "qwen_engine"):
            self.qwen_engine.unload_model_and_clean_gpu()
        if hasattr(self, "pinner"):
            self.pinner.close_browser()

        if hasattr(self, "_shutdown_event"):
            self._shutdown_event.set()
        logger.info("dta_backend_service_stopping")
        await self.ws_server.stop()
        self.softcam_engine.close()
        logger.info("dta_backend_service_stopped")


def main() -> None:
    """Main entry point for Python Backend Service."""
    print("=================================================================")
    print("   DTA AUTOLIVE BACKEND SERVICE v2.2.0 (ELECTRON NEXT-GEN AI)    ")
    print("   Phat trien boi DTA Studio — Chu quan: Duc Truong AI          ")
    print("   Hotline/Zalo: 0962.775.506 | Web: https://dta-studio.vercel.app/")
    print("=================================================================")
    print("[INFO] Headless Backend Service starting on ws://127.0.0.1:8765...")

    service = DTABackendService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(service.start())
    except KeyboardInterrupt:
        print("\n[INFO] Stopping Backend Service...")
        loop.run_until_complete(service.stop())
    finally:
        loop.close()
        print("[SUCCESS] Backend Service terminated cleanly.")


if __name__ == "__main__":
    main()
