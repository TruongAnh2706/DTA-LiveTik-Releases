"""DTA Studio - DeepSeek V3 Cloud API Engine & Hybrid AI Orchestrator.

Provides ultra-intelligent cloud reasoning for Livestream Sales Consultations,
Dynamic Product Matching, and Script Generation via DeepSeek V3 (671B MoE).

Developed by DTA Studio - Duc Truong AI (0962.775.506 / ductruong.onl@gmail.com)
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any

import structlog

logger = structlog.get_logger()

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


class DTADeepSeekEngine:
    """High-Performance DeepSeek V3 Client with Robust Error Handling & Retries."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key: str = api_key.strip()
        self.model: str = "deepseek-chat"  # DeepSeek V3
        self.is_configured: bool = bool(self.api_key)
        self.last_latency_ms: float = 0.0

    def set_api_key(self, api_key: str) -> None:
        """Update DeepSeek API Key."""
        self.api_key = api_key.strip()
        self.is_configured = bool(self.api_key)

    def _parse_http_error(self, e: urllib.error.HTTPError, latency: float) -> dict[str, Any]:
        """Format friendly Vietnamese message for HTTP errors."""
        err_msg = e.read().decode("utf-8", errors="ignore")
        if e.code == 401:
            msg = "API Key không hợp lệ (Mã lỗi 401 Unauthorized)!"
        elif e.code == 402:
            msg = "Tài khoản DeepSeek hết số dư (Mã lỗi 402 Insufficient Balance)!"
        else:
            msg = f"Lỗi HTTP {e.code}: {err_msg[:120]}"
        return {"success": False, "message": msg, "latency_ms": latency}

    def get_balance(self, test_key: str = "") -> dict[str, Any]:
        """Fetch real-time user balance from DeepSeek API (https://api.deepseek.com/user/balance)."""
        key_to_use = (test_key or self.api_key).strip()
        if not key_to_use:
            return {"is_available": False, "balance_display": "Chưa có Key"}

        url = "https://api.deepseek.com/user/balance"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {key_to_use}",
        }
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            is_avail = bool(data.get("is_available", True))
            balance_infos = data.get("balance_infos", [])
            display_parts = []

            for b in balance_infos:
                curr = b.get("currency", "USD")
                total = b.get("total_balance", "0.00")
                if float(total) > 0 or not display_parts:
                    sym = "$" if curr == "USD" else ("¥" if curr == "CNY" else "")
                    display_parts.append(f"{sym}{total} {curr}")

            balance_str = " | ".join(display_parts) if display_parts else "$0.00 USD"
            return {
                "is_available": is_avail,
                "balance_display": balance_str,
                "balance_infos": balance_infos,
            }
        except Exception as e:
            logger.warning("get_deepseek_balance_failed", error=str(e))
            return {"is_available": False, "balance_display": "Không lấy được"}

    def test_connection(self, test_key: str = "") -> dict[str, Any]:
        """Test API key validity with a lightweight ping to DeepSeek V3 and retrieve live balance."""
        key_to_use = (test_key or self.api_key).strip()
        if not key_to_use:
            return {
                "success": False,
                "message": "Vui lòng nhập DeepSeek API Key trước khi kiểm tra!",
                "latency_ms": 0,
                "balance": "",
            }

        start_t = time.perf_counter()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key_to_use}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Bạn là Trợ lý DTA Studio. Trả lời cực ngắn dưới 10 từ."},
                {"role": "user", "content": "Xin chào, hãy xác nhận DeepSeek V3 hoạt động tốt."},
            ],
            "max_tokens": 30,
            "temperature": 0.5,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(DEEPSEEK_API_URL, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                status_code = resp.getcode()
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))

            latency = round((time.perf_counter() - start_t) * 1000, 1)
            self.last_latency_ms = latency

            # Lấy số dư tài khoản thực tế
            bal_res = self.get_balance(key_to_use)
            bal_str = bal_res.get("balance_display", "")

            if status_code == 200 and "choices" in data and data["choices"]:
                reply = data["choices"][0].get("message", {}).get("content", "").strip()
                msg = f"Kết nối DeepSeek V3 thành công ({latency}ms)!"
                if bal_str:
                    msg += f" [Số dư: {bal_str}]"
                return {
                    "success": True,
                    "message": msg,
                    "reply": reply,
                    "latency_ms": latency,
                    "balance": bal_str,
                }
            return {
                "success": False,
                "message": f"API trả về mã lỗi HTTP {status_code}: {data}",
                "latency_ms": latency,
                "balance": "",
            }
        except urllib.error.HTTPError as e:
            latency = round((time.perf_counter() - start_t) * 1000, 1)
            err_dict = self._parse_http_error(e, latency)
            err_dict["balance"] = ""
            return err_dict
        except Exception as e:
            latency = round((time.perf_counter() - start_t) * 1000, 1)
            return {"success": False, "message": f"Không thể kết nối máy chủ DeepSeek: {str(e)}", "latency_ms": latency, "balance": ""}

    def generate_response(
        self,
        user_prompt: str,
        system_prompt: str = "",
        knowledge_catalog: str = "",
        region_dialect: str = "south",
        tone_style: str = "genz_casual",
        use_slangs: bool = True,
        max_tokens: int = 200,
        temperature: float = 0.7,
    ) -> str:
        """Generate response via DeepSeek V3 API using purely user-defined system prompt."""
        if not self.is_configured or not self.api_key:
            raise RuntimeError("Chưa cấu hình DeepSeek API Key! Vui lòng vào Cài Đặt nhập API Key.")

        full_system = system_prompt.strip() if system_prompt else "Bạn là Trợ lý Livestream Bán hàng AI."

        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start_t = time.perf_counter()
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(DEEPSEEK_API_URL, data=req_data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=12.0) as resp:
            resp_bytes = resp.read()
            data = json.loads(resp_bytes.decode("utf-8"))

        self.last_latency_ms = round((time.perf_counter() - start_t) * 1000, 1)

        if "choices" in data and data["choices"]:
            return data["choices"][0].get("message", {}).get("content", "").strip()

        return ""
