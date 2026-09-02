"""DTA Studio - Local Qwen AI Engine & GPU VRAM Lifecycle Manager.

Manages offline GGUF Model Loading, Streaming Auto-Download from Hugging Face with
Progress Reporting, GPU/CUDA Layer Offloading, Real-time Knowledge Base Inference,
and Deterministic VRAM Memory Cleanup.
"""

import gc
import os
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Optional import for llama_cpp
try:
    import llama_cpp  # type: ignore[import-untyped]
except ImportError:
    llama_cpp = None

# Default Model Specifications (Bartowski High-Performance GGUF Monoliths)
MODELS_CATALOG: dict[str, dict[str, Any]] = {
    "Qwen2.5-7B-Instruct-Q4_K_M": {
        "filename": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "size_bytes": 4683074240,
        "recommended_vram_gb": 6.0,
        "description": "Qwen 2.5 7B Instruct (Q4_K_M) - Cân bằng tốc độ & độ chuẩn xác cao nhất (Khuyên dùng)",
    },
    "Qwen2.5-1.5B-Instruct-Q4_K_M": {
        "filename": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "size_bytes": 1118671232,
        "recommended_vram_gb": 2.5,
        "description": "Qwen 2.5 1.5B Instruct (Q4_K_M) - Siêu nhẹ, chạy mượt trên mọi GPU và Laptop yếu",
    },
    "Qwen2.5-3B-Instruct-Q4_K_M": {
        "filename": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        "size_bytes": 2168581888,
        "recommended_vram_gb": 3.5,
        "description": "Qwen 2.5 3B Instruct (Q4_K_M) - Tối ưu cho Laptop và máy cấu hình vừa",
    },
}

DIALECT_PERSONA_MAP: dict[str, dict[str, str]] = {
    "north": {
        "name": "Miền Bắc (Hà Nội, Đông Bắc, Tây Bắc)",
        "addressing": "bác / anh em / em",
        "ending": "nhé bác / nhá anh em / ạ",
        "price_unit": "cành",
        "description": "Giọng Miền Bắc thân thiện, đon đả, xưng hô 'bác/anh em', dùng từ 'cành', 'chuẩn đét', 'ưng bụng', 'bọc PVC kỹ càng', 'bấm lẹ'.",
    },
    "central": {
        "name": "Miền Trung (Đà Nẵng, Huế, Nghệ An, Bình Định)",
        "addressing": "mình ơi / bồ ơi / anh chị",
        "ending": "nè / hỉ / hè / nha mình",
        "price_unit": "k",
        "description": "Giọng Miền Trung chân chất, dễ thương, xưng hô 'mình/bồ', dùng từ 'mềm xèo', 'chắc nịch', 'ngon lành', 'chốt lẹ hỉ'.",
    },
    "south": {
        "name": "Miền Nam / Tây (Sài Gòn, Miền Tây, Đông Nam Bộ)",
        "addressing": "anh em ơi / bồ ơi / mấy ní / bác tài",
        "ending": "nha anh em / nè / nghen",
        "price_unit": "k",
        "description": "Giọng Miền Nam/Tây hào sảng, xởi lởi, dùng từ 'lụm liền', 'bao êm', 'hết nước chấm', 'ngon lành cành đào', 'bấm vô chốt lẹ'.",
    },
}

TONE_STYLE_MAP: dict[str, dict[str, str]] = {
    "genz_casual": {
        "name": "Gen Z & Cộc Lốc Siêu Thật",
        "prompt": "Nói chuyện cộc lốc, đời thường, cực ngắn dưới 20 chữ, gõ phím nhanh như người dùng thật đang chat, không câu nệ ngữ pháp.",
    },
    "angler_pro": {
        "name": "Cần Thủ Đam Mê (Chuyên Sâu)",
        "prompt": "Nói chuyện như cao thủ câu cá, bàn sâu về phôi carbon 30T/40T, lực phân bổ 19-28i, độ nảy cá, bo cá to, câu đài/lure.",
    },
    "fomo_sale": {
        "name": "Săn Deal & FOMO Dồn Dập",
        "prompt": "Giọng điệu thúc giục chốt sale dồn dập, cảnh báo số lượng có hạn, giục bấm giỏ hàng lấy voucher 30k-50k trước khi hết deal.",
    },
    "humorous": {
        "name": "Hài Hước & Duyên Dáng",
        "prompt": "Pha trò hóm hỉnh, tếu táo, dân dã, tạo không khí phòng livestream vui tươi sôi động, khiến khách nghe là muốn mua.",
    },
    "polite": {
        "name": "Lịch Sự & Chuẩn Mực",
        "prompt": "Dạ thưa chu đáo, chuẩn mực cửa hàng phân phối chính hãng, tư vấn chuyên nghiệp tận tình.",
    },
}


def apply_human_slangs_and_typos(text: str, region_dialect: str = "south", slang_rate: float = 1.0) -> str:
    """Biến đổi văn bản sang tiếng lóng, viết tắt tự nhiên như người dùng mạng xã hội."""
    import re
    res = text
    # Viết tắt phổ biến
    res = re.sub(r"\bkhông\b", "ko", res, flags=re.IGNORECASE)
    res = re.sub(r"\bđược\b", "dc", res, flags=re.IGNORECASE)
    res = re.sub(r"\banh em\b", "ae", res, flags=re.IGNORECASE)
    res = re.sub(r"\bmọi người\b", "mn", res, flags=re.IGNORECASE)
    res = re.sub(r"\bsản phẩm\b", "sp", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(nghìn|ngàn)\s*(đồng|đ)?\b", "k", res, flags=re.IGNORECASE)
    res = re.sub(r"\.000đ\b", "k", res, flags=re.IGNORECASE)
    res = re.sub(r"\.000\s*vnđ\b", "k", res, flags=re.IGNORECASE)

    if region_dialect == "north":
        res = re.sub(r"\bbao nhiêu\b", "bao tiền", res, flags=re.IGNORECASE)
    elif region_dialect == "central":
        res = re.sub(r"\bbao nhiêu\b", "mấy rứa", res, flags=re.IGNORECASE)
    else:
        res = re.sub(r"\bbao nhiêu\b", "nhiu", res, flags=re.IGNORECASE)

    return res


def format_price_shorthand(raw_price: Any) -> str:
    """Format any price string or number into realistic streamer shorthand (e.g. 185.000đ -> 185k, 70.000 -> 70k, 1.250.000 -> 1250k)."""
    if not raw_price:
        return ""
    import re
    s = str(raw_price).strip()

    # If already in shorthand format like '185k' or '185K'
    if re.match(r"^\d+(?:\.\d+)?\s*[kK]$", s):
        return s.lower().replace(" ", "")

    # Extract digits only (ignoring currency symbols, dots, commas)
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return s

    try:
        val = int(digits)
        if val >= 1000:
            if val % 1000 == 0:
                return f"{val // 1000}k"
            k_val = round(val / 1000.0, 1)
            return f"{int(k_val)}k" if k_val == int(k_val) else f"{k_val}k"
        return f"{val}k"
    except Exception:
        return s


def get_default_models_dir() -> Path:
    """Get persistent models directory in user app data or local directory."""
    local_dir = Path(__file__).resolve().parent.parent.parent.parent / "models"
    if local_dir.exists():
        return local_dir
    app_data = Path(os.path.expanduser("~")) / ".dta_autolive" / "models"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data


def get_gpu_info() -> dict[str, Any]:
    """Inspect local GPU hardware via torch/ctypes/nvidia-smi."""
    gpu_data: dict[str, Any] = {
        "has_gpu": False,
        "gpu_name": "CPU Only",
        "total_vram_gb": 0.0,
        "used_vram_gb": 0.0,
        "free_vram_gb": 0.0,
        "gpu_temp_c": 0,
        "cuda_available": False,
    }

    # 1. Try PyTorch CUDA if available
    try:
        import torch  # type: ignore[import-untyped]

        if torch.cuda.is_available():
            gpu_data["has_gpu"] = True
            gpu_data["cuda_available"] = True
            gpu_data["gpu_name"] = torch.cuda.get_device_name(0)
            total_b = torch.cuda.get_device_properties(0).total_memory
            reserved_b = torch.cuda.memory_reserved(0)
            gpu_data["total_vram_gb"] = round(total_b / (1024**3), 2)
            gpu_data["used_vram_gb"] = round(reserved_b / (1024**3), 2)
            gpu_data["free_vram_gb"] = round((total_b - reserved_b) / (1024**3), 2)
            return gpu_data
    except Exception:
        pass

    # 2. Try Windows NVML / ctypes / wmi / nvidia-smi as fallback
    try:
        import subprocess

        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5, check=False)
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                gpu_data["has_gpu"] = True
                gpu_data["cuda_available"] = True
                gpu_data["gpu_name"] = parts[0]
                gpu_data["total_vram_gb"] = round(float(parts[1]) / 1024.0, 2)
                gpu_data["used_vram_gb"] = round(float(parts[2]) / 1024.0, 2)
                gpu_data["free_vram_gb"] = round(float(parts[3]) / 1024.0, 2)
                if len(parts) >= 5 and parts[4].isdigit():
                    gpu_data["gpu_temp_c"] = int(parts[4])
                return gpu_data
    except Exception:
        pass

    return gpu_data


class DTAQwenEngine:
    """Manages Qwen GGUF Model on local GPU with full lifecycle control."""

    def __init__(
        self,
        models_dir: Path | None = None,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self.models_dir = models_dir or get_default_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.log_callback = log_callback
        self.current_model_key: str = "Qwen2.5-7B-Instruct-Q4_K_M"
        self.llm: Any = None
        self.is_loaded: bool = False
        self._lock = threading.Lock()
        self._download_thread: threading.Thread | None = None
        self._download_cancel_event = threading.Event()
        self._is_downloading = False

    def log(self, tag: str, text: str) -> None:
        """Forward logs to callback or structlog."""
        if self.log_callback:
            self.log_callback(tag, text)
        else:
            try:
                logger.info("dta_qwen_log", tag=tag, text=text)
            except Exception:
                pass

    def check_model_status(self, model_key: str = "Qwen2.5-7B-Instruct-Q4_K_M") -> dict[str, Any]:
        """Check if model exists on disk, returning size and GPU telemetry."""
        spec = MODELS_CATALOG.get(model_key, MODELS_CATALOG["Qwen2.5-7B-Instruct-Q4_K_M"])
        target_path = self.models_dir / spec["filename"]
        exists = target_path.exists()
        size_bytes = target_path.stat().st_size if exists else 0
        size_gb = round(size_bytes / (1024**3), 2) if exists else 0.0

        gpu = get_gpu_info()

        return {
            "model_key": model_key,
            "filename": spec["filename"],
            "path": str(target_path),
            "exists": exists,
            "size_gb": size_gb,
            "expected_size_gb": round(spec["size_bytes"] / (1024**3), 2),
            "is_loaded": self.is_loaded and (self.current_model_key == model_key),
            "is_downloading": self._is_downloading,
            "gpu_info": gpu,
            "catalog": MODELS_CATALOG,
        }

    def start_download(
        self,
        model_key: str = "Qwen2.5-7B-Instruct-Q4_K_M",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> bool:
        """Start background download of the model GGUF from Hugging Face."""
        if self._is_downloading:
            self.log("WARNING", "⚠️ Đang có tiến trình tải Model khác đang chạy!")
            return False

        spec = MODELS_CATALOG.get(model_key, MODELS_CATALOG["Qwen2.5-7B-Instruct-Q4_K_M"])
        target_path = self.models_dir / spec["filename"]

        self._download_cancel_event.clear()
        self._is_downloading = True

        def _worker() -> None:
            url = spec["url"]
            self.log("INFO", f"⬇️ Bắt đầu tải Model '{model_key}' từ máy chủ...")
            start_time = time.time()
            temp_path = target_path.with_suffix(".part")

            try:
                existing_bytes = temp_path.stat().st_size if temp_path.exists() else 0
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                if existing_bytes > 0:
                    headers["Range"] = f"bytes={existing_bytes}-"

                req = urllib.request.Request(url, headers=headers)
                
                try:
                    response = urllib.request.urlopen(req, timeout=45)
                except urllib.error.HTTPError as he:
                    if he.code == 416:  # Range Not Satisfiable -> Restart fresh
                        if temp_path.exists():
                            temp_path.unlink()
                        existing_bytes = 0
                        req = urllib.request.Request(url, headers={"User-Agent": headers["User-Agent"]})
                        response = urllib.request.urlopen(req, timeout=45)
                    else:
                        raise he

                with response:
                    content_length = response.headers.get("Content-Length")
                    total_bytes = int(content_length) + existing_bytes if content_length else spec["size_bytes"]

                    mode = "ab" if existing_bytes > 0 else "wb"
                    downloaded = existing_bytes

                    with open(temp_path, mode) as f:
                        chunk_size = 1024 * 512  # 512 KB
                        last_update_time = time.time()
                        last_downloaded = downloaded

                        while not self._download_cancel_event.is_set():
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            if now - last_update_time >= 0.5:
                                speed_mb = (
                                    (downloaded - last_downloaded)
                                    / (now - last_update_time)
                                    / (1024 * 1024)
                                    if now > last_update_time
                                    else 0.0
                                )
                                progress_pct = round((downloaded / total_bytes) * 100, 1) if total_bytes > 0 else 0.0
                                eta_sec = int((total_bytes - downloaded) / (speed_mb * 1024 * 1024)) if speed_mb > 0 else 0

                                if progress_callback:
                                    progress_callback({
                                        "status": "downloading",
                                        "model_key": model_key,
                                        "progress_pct": progress_pct,
                                        "downloaded_gb": round(downloaded / (1024**3), 2),
                                        "total_gb": round(total_bytes / (1024**3), 2),
                                        "speed_mb": round(speed_mb, 2),
                                        "eta_sec": eta_sec,
                                    })
                                last_update_time = now
                                last_downloaded = downloaded

                if self._download_cancel_event.is_set():
                    self.log("SYSTEM", f"🛑 Đã hủy tải Model '{model_key}'.")
                    if progress_callback:
                        progress_callback({"status": "cancelled", "model_key": model_key})
                else:
                    if temp_path.exists():
                        if target_path.exists():
                            target_path.unlink()
                        temp_path.rename(target_path)
                    self.log("SUCCESS", f"✅ Tải thành công Model '{model_key}' vào GPU Directory!")
                    if progress_callback:
                        progress_callback({
                            "status": "completed",
                            "model_key": model_key,
                            "progress_pct": 100.0,
                            "path": str(target_path),
                        })

            except Exception as e:
                self.log("ERROR", f"❌ Lỗi tải Model '{model_key}': {e}")
                if progress_callback:
                    progress_callback({"status": "error", "model_key": model_key, "error": str(e)})
            finally:
                self._is_downloading = False

        self._download_thread = threading.Thread(target=_worker, daemon=True)
        self._download_thread.start()
        return True

    def cancel_download(self) -> None:
        """Cancel active model download."""
        if self._is_downloading:
            self._download_cancel_event.set()
            self._is_downloading = False

    def delete_model(self, model_key: str = "Qwen2.5-7B-Instruct-Q4_K_M") -> dict[str, Any]:
        """Delete model GGUF file from disk to free up space or reinstall."""
        self.unload_model_and_clean_gpu()
        spec = MODELS_CATALOG.get(model_key, MODELS_CATALOG["Qwen2.5-7B-Instruct-Q4_K_M"])
        target_path = self.models_dir / spec["filename"]
        temp_path = target_path.with_suffix(".part")
        deleted = False
        try:
            if target_path.exists():
                target_path.unlink()
                deleted = True
                self.log("SUCCESS", f"🗑️ Đã xóa tệp Model '{model_key}' khỏi thư mục lưu trữ.")
            if temp_path.exists():
                temp_path.unlink()
                deleted = True
        except Exception as e:
            self.log("ERROR", f"❌ Không thể xóa tệp Model: {e}")
            return {"success": False, "error": str(e), "model_key": model_key}
        return {"success": True, "deleted": deleted, "model_key": model_key, "status": self.check_model_status(model_key)}

    def load_model_to_gpu(
        self,
        model_key: str = "Qwen2.5-7B-Instruct-Q4_K_M",
        n_gpu_layers: int = -1,
        n_ctx: int = 4096,
    ) -> bool:
        """Preload Model directly into GPU VRAM."""
        with self._lock:
            if self.is_loaded and self.current_model_key == model_key and self.llm is not None:
                self.log("INFO", f"⚡ Model '{model_key}' đã được nạp sẵn trên GPU VRAM!")
                return True

            # Unload previous model if any
            self._unload_vram_unsafe()

            spec = MODELS_CATALOG.get(model_key, MODELS_CATALOG["Qwen2.5-7B-Instruct-Q4_K_M"])
            model_path = self.models_dir / spec["filename"]

            if not model_path.exists():
                self.log("ERROR", f"❌ Không tìm thấy file model: {model_path}. Vui lòng tải model trước!")
                return False

            self.log("INFO", f"🚀 Đang nạp Model '{model_key}' vào GPU VRAM (n_gpu_layers={n_gpu_layers}, n_ctx={n_ctx})...")

            if llama_cpp is None:
                self.log(
                    "WARNING",
                    "⚠️ Thư viện 'llama-cpp-python' chưa được cài đặt trong môi trường. Đang chạy chế độ Simulated Fast Engine.",
                )
                self.is_loaded = True
                self.current_model_key = model_key
                self.llm = "SIMULATED_ENGINE"
                self.log("SUCCESS", f"✅ [Simulated] Model '{model_key}' đã sẵn sàng phản hồi!")
                return True

            try:
                start_t = time.time()
                self.llm = llama_cpp.Llama(
                    model_path=str(model_path),
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=n_ctx,
                    verbose=False,
                )
                elapsed = round(time.time() - start_t, 2)
                self.is_loaded = True
                self.current_model_key = model_key
                self.log("SUCCESS", f"✅ Đã nạp thành công Model '{model_key}' vào GPU trong {elapsed}s!")
                return True
            except Exception as e:
                self.log("ERROR", f"❌ Lỗi nạp Model vào GPU: {e}")
                self.is_loaded = False
                self.llm = None
                return False

    def unload_model_and_clean_gpu(self) -> None:
        """Thread-safe unload model instance and garbage collect CUDA cache."""
        with self._lock:
            self._unload_vram_unsafe()

    def _unload_vram_unsafe(self) -> None:
        """Internal worker to release LLM and clean GPU."""
        if self.llm is not None:
            self.log("SYSTEM", f"🛑 Đang giải phóng VRAM và dọn dẹp GPU ({self.current_model_key})...")
            self.llm = None
            self.is_loaded = False

            # Force python garbage collection
            gc.collect()

            # Attempt torch cuda cache cleanup if available
            try:
                import torch  # type: ignore[import-untyped]

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except Exception:
                pass

            self.log("SUCCESS", "✨ Đã giải phóng 100% VRAM GPU. Máy đã trở về trạng thái nghỉ!")

    @staticmethod
    def apply_human_slangs_and_typos(text: str, region_dialect: str = "south", slang_rate: float = 1.0) -> str:
        """Forwarder to module-level slang and typo generator."""
        return apply_human_slangs_and_typos(text, region_dialect, slang_rate)

    def generate_response(
        self,
        user_prompt: str,
        system_prompt: str = "",
        knowledge_catalog: str = "",
        region_dialect: str = "south",
        tone_style: str = "genz_casual",
        use_slangs: bool = True,
        max_tokens: int = 150,
        temperature: float = 0.75,
    ) -> str:
        """Generate response with user's custom system prompt via Qwen."""
        if not self.is_loaded or self.llm is None:
            raise RuntimeError("Model Qwen chưa được nạp vào GPU! Vui lòng bấm 'Khởi Động Server AI'.")

        full_system = system_prompt.strip() if system_prompt else "Bạn là Trợ lý Livestream Bán hàng AI."

        # Standard Qwen ChatML Format
        formatted_prompt = (
            f"<|im_start|>system\n{full_system}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        # Fallback smart generative engine if llama_cpp is in simulated mode
        if self.llm == "SIMULATED_ENGINE" or llama_cpp is None:
            import re
            time.sleep(0.05)  # Fast inference simulation

            u_low = user_prompt.lower()

            # Search product in knowledge_catalog if present
            matched_info = None
            if knowledge_catalog:
                # Find by STT match (e.g. #3, mã 3, cây 3, số 3)
                m_stt = re.search(r"(?:mã\s*số|mẫu\s*số|sản\s*phẩm|mã|mẫu|sp|cây|cần|số|mục)\s*#?\s*(\d+)", u_low) or re.search(r"#(\d+)", u_low)
                if m_stt:
                    target_num = m_stt.group(1)
                    for line in knowledge_catalog.split("\n"):
                        if f"Mã SP {target_num}:" in line or f"#{target_num}" in line:
                            matched_info = line
                            break

            reply_out = ""
            if matched_info:
                clean_info = matched_info.replace('• ', '')
                if region_dialect == "north":
                    reply_out = f"Dạ {clean_info} nhá bác ơi! Em ghim ngay lên góc trái rồi, bác bấm lẹ kẻo hết deal nhá!"
                elif region_dialect == "central":
                    reply_out = f"Dạ {clean_info} nè mình ơi! Em ghim góc trái rồi, chốt lẹ nhận ưu đãi hỉ!"
                else:
                    reply_out = f"Dạ {clean_info} nha anh em! Em ghim liền góc trái nè, bấm vô lụm lẹ kẻo hết nha!"
            elif "ship" in u_low or "giao" in u_low or "mấy ngày" in u_low:
                if region_dialect == "north":
                    reply_out = "Dạ bên em bọc ống PVC cứng cáp giao tận nhà 2-3 hôm, bác bóc ra kiểm tra hàng thoải mái mới thanh toán nhá!"
                elif region_dialect == "central":
                    reply_out = "Dạ shop freeship toàn quốc, đóng ống PVC kĩ càng giao 2-3 ngày, mình kiểm tra ưng ý mới nhận hỉ!"
                else:
                    reply_out = "Dạ freeship toàn quốc nha anh em, đóng ống PVC bao êm 2-3 hôm tới, bồ kiểm tra hàng thoải mái nha!"
            elif "bảo hành" in u_low or "gãy" in u_low or "lóng" in u_low:
                if region_dialect == "north":
                    reply_out = "Dạ hàng chính hãng bảo hành 1 năm 1 lóng trừ lóng gốc, lỗi 1 đổi 1 trong tuần đầu nên bác cứ yên tâm đánh bắt nhá!"
                elif region_dialect == "central":
                    reply_out = "Dạ bảo hành 1 năm 1 lóng chính hãng, có phiếu bảo hành đi kèm, mình cứ yên tâm sử dụng hỉ!"
                else:
                    reply_out = "Dạ bảo hành 1 năm 1 lóng xịn sò nha mấy ní, lỗi là 1 đổi 1 liền tay, anh em yên tâm kéo cá bự nha!"
            elif "voucher" in u_low or "giảm giá" in u_low or "khuyến mãi" in u_low:
                if region_dialect == "north":
                    reply_out = "Dạ bác bấm ngay vào góc trái lưu voucher 30k - 50k với mã freeship để chốt deal hời nhá!"
                elif region_dialect == "central":
                    reply_out = "Dạ mình bấm ngay vô giỏ hàng góc trái lưu voucher 30k-50k nhận trợ giá liền hỉ!"
                else:
                    reply_out = "Dạ bồ bấm liền vô giỏ hàng góc trái lụm voucher 30k - 50k với freeship liền tay kẻo hết nè!"
            else:
                if region_dialect == "north":
                    reply_out = "Dạ chào bác! Bác bấm vào giỏ hàng góc trái xem chi tiết các mẫu cần đang trợ giá sốc nhá!"
                elif region_dialect == "central":
                    reply_out = "Dạ chào mình! Mọi người bấm vô giỏ hàng góc trái để xem ưu đãi hỉ!"
                else:
                    reply_out = "Dạ chào anh em! Bồ bấm vô giỏ hàng góc trái chọn mẫu săn deal ngon lành cành đào nha!"

            if use_slangs:
                reply_out = apply_human_slangs_and_typos(reply_out, region_dialect)
            return reply_out

        try:
            output = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["<|im_end|>", "<|im_start|>", "\n\n\n"],
                echo=False,
            )
            raw_text = output["choices"][0]["text"].strip()
            if use_slangs:
                raw_text = apply_human_slangs_and_typos(raw_text, region_dialect)
            return raw_text if raw_text else "Dạ shop cảm ơn anh em đã ủng hộ nha!"
        except Exception as e:
            self.log("ERROR", f"❌ Lỗi suy luận Qwen: {e}")
            raise

    def generate_seeding_scenarios(
        self,
        products_catalog: list[dict[str, Any]],
        count: int = 5,
    ) -> list[str]:
        """Generate dynamic seeding comments based on current live products."""
        if not products_catalog:
            return [
                "Cần câu này 5H đánh cá tầm bao nhiêu kg vậy shop?",
                "Mới săn được giá rẻ 315k nè mọi người ơi!",
                "Shop ơi cho em hỏi còn mã số 1 không ạ?",
                "Giao hàng về Hà Nội mấy ngày tới shop?",
                "Em vừa chốt 1 cây mã 2 rồi nhé shop!",
            ]

        if self.llm == "SIMULATED_ENGINE" or llama_cpp is None:
            results = []
            for p in products_catalog:
                stt = p.get("stt", 1)
                name = p.get("name", f"Sản phẩm #{stt}")
                price = p.get("sale_price", "")
                results.append(f"Mã #{stt} ({name[:30]}) giá {price} còn hàng không shop?")
                results.append(f"Shop ghim lại mã #{stt} em áp mã voucher với ạ!")
                results.append(f"Em mới nhận cây #{stt} hôm qua, phôi dày cầm rất đầm tay!")
            while len(results) < count:
                results.append("Hôm nay có voucher giảm giá nào không shop ơi?")
            return results[:count]

        catalog_summary = "\n".join([
            f"- STT {p.get('stt')}: {p.get('name')} | Giá: {p.get('sale_price')} | Tồn: {p.get('stock')}"
            for p in products_catalog[:8]
        ])

        prompt = (
            f"Dựa vào danh sách sản phẩm sau đây:\n{catalog_summary}\n\n"
            f"Hãy tạo ra đúng {count} câu bình luận seeding (comment mồi) của khán giả người mua hàng bằng tiếng Việt. "
            "Bao gồm: câu hỏi thông số hàng, câu khen review tốt, câu tạo FOMO giục mọi người chốt đơn. "
            "Mỗi câu trên một dòng, không đánh số thứ tự."
        )

        try:
            raw_res = self.generate_response(
                user_prompt=prompt,
                system_prompt="Bạn là chuyên gia Seeding Livestream TikTok. Xuất danh sách câu comment tự nhiên như người mua hàng thật.",
                max_tokens=250,
                temperature=0.85,
            )
            lines = [line.strip().lstrip("0123456789.- ") for line in raw_res.split("\n") if line.strip()]
            return lines[:count] if lines else [
                "Sản phẩm đẹp quá shop ơi!",
                "Mã 1 còn hàng không ạ?",
                "Em vừa thanh toán xong rồi nhé!",
            ]
        except Exception:
            return [
                "Cần câu này cầm đầm tay không shop?",
                "Giá hôm nay sale rẻ quá em vừa mua rồi",
                "Shop ghim lại mã 1 cho em xem với ạ",
            ]
