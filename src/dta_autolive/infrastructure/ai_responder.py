import threading
import time

import requests

from dta_autolive.infrastructure.deepseek_engine import query_deepseek_v3
from dta_autolive.infrastructure.tiktok_shop_knowledge_base import TikTokShopKnowledgeBase


class GeminiKeyRotator:
    """
    Quản lý hàng đợi xoay vòng nhiều Gemini API Keys.
    Tự động chuyển sang Key tiếp theo khi dính lỗi HTTP 429 (Rate Limit) hoặc Lỗi Xác thực Key.
    """
    def __init__(self, api_keys, log_callback=None):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.current_index = 0
        self.log_callback = log_callback
        self.lock = threading.Lock()

    def log(self, tag, text):
        if self.log_callback:
            self.log_callback(tag, text)

    def get_active_key(self):
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.current_index % len(self.api_keys)]

    def rotate_key(self, reason="Rate Limit 429"):
        with self.lock:
            if len(self.api_keys) <= 1:
                self.log("WARNING", f"⚠️ Dính lỗi Gemini ({reason}) nhưng chỉ có 1 API Key trong danh sách!")
                return
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            self.log("WARNING", f"🔄 Gemini API Key #{old_index + 1} dính lỗi ({reason}) -> Đã tự động xoay sang Key #{self.current_index + 1}!")

    def generate_response(self, system_prompt, user_comment):
        """
        Gửi prompt đến Gemini API.
        """
        max_attempts = max(1, len(self.api_keys))

        for attempt in range(max_attempts):
            active_key = self.get_active_key()
            if not active_key:
                raise ValueError("Chưa nhập Gemini API Key!")

            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={active_key}"

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"System Guidelines / Context:\n{system_prompt}\n\nKhán giả hỏi: {user_comment}\nTrả lời ngắn gọn, thân thiện (dưới 100 từ):"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 150
                }
            }
            headers = {"Content-Type": "application/json"}

            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=12)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return text.strip()
                    return "DTA AI: Cảm ơn bạn đã bình luận!"

                if resp.status_code == 429:
                    self.rotate_key("HTTP 429 Rate Limit Exceeded")
                    time.sleep(0.5)
                    continue

                if resp.status_code in [400, 401, 403]:
                    self.rotate_key(f"HTTP {resp.status_code} Invalid Key")
                    time.sleep(0.5)
                    continue

                raise Exception(f"Gemini API Error {resp.status_code}: {resp.text}")

            except requests.exceptions.RequestException as e:
                self.log("ERROR", f"❌ Gemini Network Exception: {e}")
                self.rotate_key("Network Error")
                time.sleep(0.5)

        raise Exception("Tất cả Gemini API Keys đều bị lỗi hoặc dính Rate Limit!")


class DeepSeekKeyRotator:
    """
    Quản lý hàng đợi xoay vòng nhiều DeepSeek API Keys.
    Tự động chuyển sang Key tiếp theo khi dính lỗi HTTP 429 (Rate Limit) hoặc Lỗi Xác thực Key.
    """
    def __init__(self, api_keys, log_callback=None):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.current_index = 0
        self.log_callback = log_callback
        self.lock = threading.Lock()

    def log(self, tag, text):
        if self.log_callback:
            self.log_callback(tag, text)

    def get_active_key(self):
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.current_index % len(self.api_keys)]

    def rotate_key(self, reason="Rate Limit 429"):
        with self.lock:
            if len(self.api_keys) <= 1:
                self.log("WARNING", f"⚠️ Dính lỗi DeepSeek ({reason}) nhưng chỉ có 1 API Key trong danh sách!")
                return
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            self.log("WARNING", f"🔄 DeepSeek API Key #{old_index + 1} dính lỗi ({reason}) -> Đã tự động xoay sang Key #{self.current_index + 1}!")

    def generate_response(self, nickname, comment_text, system_prompt):
        max_attempts = max(1, len(self.api_keys))
        for attempt in range(max_attempts):
            active_key = self.get_active_key()
            if not active_key:
                raise ValueError("Chưa nhập DeepSeek API Key!")
            try:
                reply = query_deepseek_v3(nickname, comment_text, active_key, system_prompt)
                if reply:
                    return reply
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "Rate limit" in err_str:
                    self.rotate_key("HTTP 429 Rate Limit")
                elif "401" in err_str or "403" in err_str:
                    self.rotate_key("HTTP 401/403 Invalid Key")
                else:
                    self.log("ERROR", f"❌ DeepSeek Error: {e}")
                    self.rotate_key("API Error")
                time.sleep(0.5)

        raise Exception("Tất cả DeepSeek API Keys đều bị lỗi hoặc dính Rate Limit!")


class TikTokAIResponderManager:
    """
    Quản lý Lắng nghe Bình luận Live Stream TikTok & Tự động Trả lời bằng AI (DeepSeek V3 hoặc Gemini).
    """
    def __init__(self, log_callback=None, status_callback=None, pinner_manager=None):
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.pinner_manager = pinner_manager

        self.is_running = False
        self.rotator = None
        self.ds_rotator = None
        self.deepseek_key = ""
        self.selected_ai = "DeepSeek V3"
        self.system_prompt = ""
        self.username = ""
        self.listener_thread = None
        self.tiktok_client = None

    def log(self, tag, text):
        if self.log_callback:
            self.log_callback(tag, text)

    def set_status(self, text, color="#00FF66"):
        if self.status_callback:
            self.status_callback(text, color)

    def start_responder(self, api_keys_text, username, system_prompt, selected_ai="DeepSeek V3", deepseek_key=""):
        if self.is_running:
            self.log("WARNING", "⚠️ AI Responder đang chạy!")
            return

        clean_username = username.strip().replace("@", "")
        if not clean_username:
            self.log("ERROR", "❌ Chưa nhập TikTok Username (@username)!")
            return

        self.username = clean_username
        self.system_prompt = system_prompt
        self.selected_ai = selected_ai
        self.deepseek_key = deepseek_key.strip()

        api_keys = [k.strip() for k in api_keys_text.split("\n") if k.strip()]
        self.rotator = GeminiKeyRotator(api_keys, log_callback=self.log_callback)

        ds_keys = [k.strip() for k in deepseek_key.replace(",", "\n").split("\n") if k.strip()]
        self.ds_rotator = DeepSeekKeyRotator(ds_keys, log_callback=self.log_callback)

        if self.selected_ai == "DeepSeek V3" and not ds_keys:
            self.log("ERROR", "❌ Đang chọn DeepSeek V3 nhưng chưa nhập DeepSeek API Key trong Popup Cấu Hình!")
            return

        self.is_running = True
        self.set_status(f"Đang Nghe ({self.selected_ai})...", "#00FFFF")
        self.log("INFO", f"🤖 Đã kết nối AI Responder [{self.selected_ai}] lắng nghe TikTok Live Stream: @{self.username}")

        self.listener_thread = threading.Thread(target=self._run_tiktok_listener, daemon=True)
        self.listener_thread.start()

    def stop_responder(self):
        if self.is_running:
            self.is_running = False
            try:
                if self.tiktok_client:
                    self.tiktok_client.stop()
            except Exception:
                pass
            self.log("SYSTEM", "🛑 Đã dừng AI Responder.")
            self.set_status("Đã Dừng AI", "#FFCC00")

    def _inject_chat_reply(self, reply_text):
        """
        Nhập câu trả lời AI trực tiếp vào khung Chat của TikTok Live qua Playwright Page nếu có.
        """
        if self.pinner_manager and self.pinner_manager.page and not self.pinner_manager.page.is_closed():
            try:
                page = self.pinner_manager.page
                chat_input = page.locator("textarea[placeholder*='chat'], input[placeholder*='chat'], [contenteditable='true']").first
                if chat_input.is_visible(timeout=2000):
                    chat_input.fill(reply_text)
                    page.keyboard.press("Enter")
                    self.log("ACTION", f"💬 [Live Chat Injected] Đã gửi bình luận: {reply_text}")
                    return True
            except Exception as e:
                self.log("WARNING", f"⚠️ Không thể tự động nhập chatbox Playwright: {e}")
        return False

    def process_comment(self, nickname, comment_text):
        """
        Xử lý bình luận khán giả:
        1. Kiểm tra chính sách TikTok Shop để giải quyết triệt để lỗi trả lời lệch sóng và ngăn ghim nhầm SP.
        2. Gửi bình luận đến Product Pinner để kiểm tra Smart Keyword Pinning (nếu không phải câu hỏi chính sách).
        3. Gửi bình luận đến DeepSeek V3 / Gemini / TikTokShopKnowledgeBase để tạo câu trả lời chuẩn xác.
        4. Inject câu trả lời vào khung chat Live.
        """
        if not self.is_running:
            return

        self.log("INFO", f"💬 Bình luận mới từ [{nickname}]: {comment_text}")

        # Nhận diện chính sách nền tảng TikTok Shop
        policy_intent = TikTokShopKnowledgeBase.detect_policy_intent(comment_text)

        # 1. Kiểm tra ghim sản phẩm thông minh nếu đang bật (CHỈ GHIM NẾU KHÔNG PHẢI CÂU HỎI CHÍNH SÁCH)
        if self.pinner_manager and not policy_intent:
            if hasattr(self.pinner_manager, "check_and_pin_by_keyword"):
                self.pinner_manager.check_and_pin_by_keyword(comment_text)

        # 2. Tạo câu trả lời AI qua TikTokShopKnowledgeBase hoặc DeepSeek V3 / Gemini Rotator
        def _generate():
            try:
                if policy_intent:
                    ai_reply = TikTokShopKnowledgeBase.generate_policy_response(
                        intent=policy_intent,
                        nickname=nickname,
                        region_dialect="south",
                        use_slangs=True
                    )
                elif self.selected_ai == "DeepSeek V3":
                    enhanced_prompt = f"{self.system_prompt}\n\n{TikTokShopKnowledgeBase.get_knowledge_summary_for_ai_prompt()}"
                    if self.ds_rotator:
                        ai_reply = self.ds_rotator.generate_response(nickname, comment_text, enhanced_prompt)
                    else:
                        ai_reply = query_deepseek_v3(nickname, comment_text, self.deepseek_key, enhanced_prompt)
                else:
                    enhanced_prompt = f"{self.system_prompt}\n\n{TikTokShopKnowledgeBase.get_knowledge_summary_for_ai_prompt()}"
                    ai_reply = self.rotator.generate_response(enhanced_prompt, comment_text)

                self.log("SUCCESS", f"🤖 [{self.selected_ai if not policy_intent else 'TikTokShop KB'}] Phản hồi cho [{nickname}]: {ai_reply}")
                # 3. Inject câu trả lời vào Live Chat
                self._inject_chat_reply(f"@{nickname} {ai_reply}")
            except Exception as e:
                self.log("ERROR", f"❌ Lỗi tạo phản hồi AI: {e}")

        threading.Thread(target=_generate, daemon=True).start()

    def _run_tiktok_listener(self):
        """
        Vòng lặp kết nối lắng nghe TikTok Live Chat Stream qua thư viện TikTokLive.
        """
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent

            self.tiktok_client = TikTokLiveClient(unique_id=self.username)

            @self.tiktok_client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                if self.is_running:
                    nickname = event.user.nickname if hasattr(event.user, "nickname") else "Khán giả"
                    comment = event.comment
                    self.process_comment(nickname, comment)

            self.tiktok_client.run()
        except ImportError:
            self.log("WARNING", "⚠️ Thư viện TikTokLive chưa cài đặt hoặc không khả dụng. Đang dùng chế độ Simulated Listener.")
            self._simulated_listener_loop()
        except Exception as e:
            self.log("ERROR", f"❌ Lỗi kết nối TikTok Live Stream: {e}")
            self.log("INFO", "🔄 Chuyển sang chế độ Chờ Bình luận (Standby mode)...")
            self._simulated_listener_loop()

    def _simulated_listener_loop(self):
        while self.is_running:
            time.sleep(3.0)
