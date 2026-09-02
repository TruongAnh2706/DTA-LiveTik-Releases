import os
import random
import subprocess
import threading
import time
import urllib.request
from typing import Any


def find_system_chrome():
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return "chrome.exe"


class ProductPinnerManager:
    """
    Quản lý tự động Ghim (Chuyển lên đầu) sản phẩm trên TikTok Shop Streamer Live Dashboard.
    (URL: https://shop.tiktok.com/streamer/live/product/dashboard)
    Hỗ trợ 3 chế độ ghim:
    1. Ping-Pong / Zigzag: Lượt 1 xuôi (1->N), Lượt 2 ngược (N->1)
    2. Loop: Luân phiên tuần tự (1->N) lặp lại
    3. Random: Trộn ngẫu nhiên danh sách sản phẩm
    """
    def __init__(self, log_callback=None, status_callback=None, event_callback=None):
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.event_callback = event_callback
        self.is_running = False
        self.worker_thread = None

        self.product_list = []
        self.interval_seconds = 10
        self.random_interval = True
        self.interval_min = None
        self.interval_max = None
        self.mode = "ping_pong"
        self.auto_scroll = False
        self.keyword_mapping = {}
        self.cdp_port = 9222
        self.browser_process = None

        self.products_catalog = []
        self.product_interest_counts = {}
        self.pin_counts = {}
        self.auto_callout_enabled = True
        self.seeding_support_enabled = True

        # Bộ điều phối Khóa Giữ Ưu Tiên khi khách comment hỏi mã (Priority Pin Hold Window)
        self.priority_pin_lock_until: float = 0.0
        self.priority_pinned_pid: str = ""
        self.priority_hold_seconds: int = 60

    def record_product_interest(self, product_id: str | int) -> None:
        """Ghi nhận lượt khán giả hỏi về sản phẩm để tăng nhiệt kế quan tâm."""
        pid_str = str(product_id)
        self.product_interest_counts[pid_str] = self.product_interest_counts.get(pid_str, 0) + 1

    def record_pin_action(self, product_id: str | int) -> None:
        """Ghi nhận số lần sản phẩm đã được ghim lên đầu."""
        pid_str = str(product_id)
        self.pin_counts[pid_str] = self.pin_counts.get(pid_str, 0) + 1

    def get_analytics_summary(self) -> dict[str, Any]:
        """Tổng hợp dữ liệu nhiệt kế giỏ hàng thời gian thực."""
        total_pins = sum(self.pin_counts.values())
        total_queries = sum(self.product_interest_counts.values())
        return {
            "total_pins": total_pins,
            "total_queries": total_queries,
            "pin_counts": dict(self.pin_counts),
            "interest_counts": dict(self.product_interest_counts),
        }

    def log(self, tag, text):
        if self.log_callback:
            self.log_callback(tag, text)

    def set_status(self, text, color="#00FF66"):
        if self.status_callback:
            self.status_callback(text, color)

    def launch_browser(self):
        """
        Khởi chạy Native Google Chrome độc lập với Playwright.
        """
        def _launch():
            try:
                user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "dta_live_browser_profile"))
                os.makedirs(user_data_dir, exist_ok=True)

                chrome_is_active = False
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/version", timeout=1) as response:
                        if response.status == 200:
                            chrome_is_active = True
                            self.log("INFO", f"🌐 Native Chrome đang mở trên cổng {self.cdp_port}!")
                except Exception:
                    chrome_is_active = False

                if not chrome_is_active:
                    chrome_exe = find_system_chrome()
                    self.log("INFO", f"🌐 Đang mở NATIVE GOOGLE CHROME siêu tốc ({chrome_exe})...")

                    cmd = [
                        chrome_exe,
                        f"--remote-debugging-port={self.cdp_port}",
                        f"--user-data-dir={user_data_dir}",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-breakpad",
                        "--disable-client-side-phishing-detection",
                        "--disable-component-update",
                        "--disable-default-apps",
                        "--disable-dev-shm-usage",
                        "--disable-domain-reliability",
                        "--disable-hang-monitor",
                        "--disable-ipc-flooding-protection",
                        "--disable-popup-blocking",
                        "--disable-prompt-on-repost",
                        "--disable-renderer-backgrounding",
                        "--disable-sync",
                        "--force-color-profile=srgb",
                        "https://shop.tiktok.com/streamer/live/product/dashboard"
                    ]

                    self.browser_process = subprocess.Popen(cmd)
                    time.sleep(1.5)

                self.log("SUCCESS", "✅ Đã mở Trang quản lý sản phẩm TikTok Live Streamer thành công!")
                self.set_status("Trình duyệt Đã Mở", "#00FF66")

            except Exception as e:
                self.log("ERROR", f"❌ Lỗi mở Trình duyệt Chrome: {e}")
                self.set_status("Lỗi Mở Trình Duyệt", "#FF3344")

        threading.Thread(target=_launch, daemon=True).start()

    def close_browser(self) -> None:
        """Đóng tiến trình Chrome Live khi tắt app."""
        if hasattr(self, "browser_process") and self.browser_process:
            try:
                self.browser_process.terminate()
                self.browser_process.kill()
            except Exception:
                pass
            self.browser_process = None

        if os.name == "nt":
            try:
                cmd = f'powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like \'*--remote-debugging-port={self.cdp_port}*\' -or $_.CommandLine -like \'*dta_live_browser_profile*\' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"'
                subprocess.run(cmd, shell=True, capture_output=True, timeout=2.0)
            except Exception:
                pass

    def start_pinning(
        self,
        product_ids_str: str,
        interval_sec: int | str = 10,
        mode: str = "loop",
        keyword_map_str: str = "",
        auto_scroll: bool = False,
        random_interval: bool = True,
        interval_min: int | None = None,
        interval_max: int | None = None,
    ) -> None:
        if self.is_running:
            self.log("WARNING", "⚠️ Tiến trình ghim sản phẩm đang hoạt động!")
            return

        raw_ids = [p.strip() for p in product_ids_str.split(",") if p.strip()]
        if not raw_ids:
            self.log("ERROR", "❌ Danh sách mã sản phẩm trống!")
            return

        self.product_list = raw_ids
        self.interval_seconds = max(3, int(interval_sec))
        self.random_interval = bool(random_interval)
        self.interval_min = int(interval_min) if interval_min is not None else None
        self.interval_max = int(interval_max) if interval_max is not None else None
        self.mode = mode
        self.auto_scroll = bool(auto_scroll)
        self.is_running = True

        self.keyword_mapping = {}
        if keyword_map_str:
            for line in keyword_map_str.split("\n"):
                if ":" in line:
                    pid, kw_part = line.split(":", 1)
                    keywords = [k.strip().lower() for k in kw_part.split(",") if k.strip()]
                    self.keyword_mapping[pid.strip()] = keywords

        scroll_status = "Bật cuộn chuột" if self.auto_scroll else "TẮT CUỘN CHUỘT (Cố định màn hình)"
        rand_status = "🎲 Random thời gian" if self.random_interval else "Cố định thời gian"
        self.set_status("Đang Ghim SP...", "#00FFFF")
        self.log("INFO", f"🚀 Kích hoạt Ghim Luân Phiên (DS STT: {', '.join(raw_ids)} | Cơ sở: {self.interval_seconds}s ({rand_status}) | {scroll_status})")
        self.worker_thread = threading.Thread(target=self._pin_loop, daemon=True)
        self.worker_thread.start()

    def stop_pinning(self):
        if self.is_running:
            self.is_running = False
            self.log("SYSTEM", "🛑 Đã dừng tiến trình ghim sản phẩm.")
            self.set_status("Đã Dừng Ghim", "#FFCC00")

    def _do_pin(self, page, product_id):
        """
        Thao tác Ghim Sản Phẩm lên màn hình Live chuẩn xác 100%.
        Sử dụng đúng class 'pc_pin_product_pin' và 'pc_pin_product_unpin' từ TikTok Streamer DOM.
        Tuyệt đối loại trừ 'surprise-button' (Voucher) và 'pc_pin_product_list_pin' (Bundle list).
        """
        try:
            pid_str = str(product_id).strip()
            stt_num = int(pid_str) if pid_str.isdigit() else 0

            # Tìm tên chi tiết sản phẩm từ catalog (nếu có)
            prod_name = ""
            for p in self.products_catalog:
                if str(p.get("stt")) == pid_str:
                    prod_name = p.get("name", "")
                    break

            short_title = (prod_name[:30] + '...') if prod_name else f"SP #{pid_str}"
            self.log("ACTION", f"📌 Đang tiến hành Ghim SP #{pid_str} ({short_title}) lên màn hình Live...")

            res = page.evaluate(r"""async (args) => {
                const targetStt = args.stt;
                const targetName = (args.name || '').trim().toLowerCase();
                const autoScroll = args.auto_scroll;

                const sleep = (ms) => new Promise(r => setTimeout(r, ms));

                const dispatchFullClick = (el) => {
                    if (!el) return false;
                    try {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } catch(e) {}

                    try {
                        const rect = el.getBoundingClientRect();
                        const cx = rect.left + rect.width / 2;
                        const cy = rect.top + rect.height / 2;

                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtType => {
                            const evt = new MouseEvent(evtType, {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: cx,
                                clientY: cy
                            });
                            el.dispatchEvent(evt);
                        });

                        if (typeof el.click === 'function') {
                            el.click();
                        }
                        return true;
                    } catch(e) {
                        try {
                            el.click();
                            return true;
                        } catch(e2) {
                            return false;
                        }
                    }
                };

                const handleConfirmModal = async () => {
                    await sleep(200);
                    // CHỈ TÌM BÊN TRONG MODAL/DIALOG ĐANG HIỂN THỊ (NẾU CÓ POPUP HỎI THAY THẾ)
                    const activeModal = document.querySelector('.arco-modal:not([style*="display: none"]), [role="dialog"], div[class*="modal-wrapper"]');
                    if (!activeModal) {
                        return false;
                    }

                    const modalBtns = Array.from(activeModal.querySelectorAll('button, [role="button"]'));
                    const confirmBtn = modalBtns.find(b => {
                        const txt = (b.innerText || '').trim().toLowerCase();
                        const isCancel = txt.includes('hủy') || txt.includes('cancel') || txt.includes('đóng') || txt.includes('close');
                        return !isCancel && (txt === 'xác nhận' || txt === 'thay thế' || txt === 'đồng ý' || txt === 'confirm' || txt === 'replace' || (b.className && b.className.includes('primary')));
                    });
                    if (confirmBtn) {
                        dispatchFullClick(confirmBtn);
                        await sleep(150);
                        return true;
                    }
                    return false;
                };

                // -------------------------------------------------------------
                // TÌM CONTAINER CUỘN DANH SÁCH SẢN PHẨM (VIRTUALIZED LIST)
                // -------------------------------------------------------------
                const getScrollContainer = () => {
                    return document.querySelector('[class*="virtualized-container"]') || 
                           document.querySelector('.arco-table-body') || 
                           document.querySelector('[class*="table-body"]') || 
                           document.querySelector('[class*="list-container"]') || 
                           window;
                };

                // -------------------------------------------------------------
                // HÀM TÌM VÀ GHIM SẢN PHẨM TRÊN DOM
                // -------------------------------------------------------------
                const findTargetProductAndPin = () => {
                    // 1. Quét ưu tiên theo input STT chuẩn của TikTok Shop Streamer
                    if (targetStt > 0) {
                        const allInputs = Array.from(document.querySelectorAll('input[data-tid="m4b_input_number"], .pc_order_input input, input[role="spinbutton"], input.arco-input'));
                        for (const inp of allInputs) {
                            const val = parseInt(inp.value || inp.getAttribute('aria-valuenow') || '0', 10);
                            if (val === targetStt) {
                                let card = inp.parentElement;
                                for (let i = 0; i < 10; i++) {
                                    if (!card || card === document.body) break;
                                    const unpinBtn = card.querySelector('button.pc_pin_product_unpin, .pc_pin_product_unpin');
                                    if (unpinBtn) {
                                        return { success: true, method: 'already_pinned_active' };
                                    }
                                    const pinBtn = card.querySelector('button.pc_pin_product_pin, .pc_pin_product_pin, button');
                                    if (pinBtn && ((pinBtn.className && pinBtn.className.includes('pc_pin_product_pin')) || (pinBtn.innerText || '').includes('Ghim'))) {
                                        pinBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        dispatchFullClick(pinBtn);
                                        return { success: true, method: 'pc_pin_product_pin_clicked' };
                                    }
                                    card = card.parentElement;
                                }
                            }
                        }
                    }

                    // 2. Quét theo Tên sản phẩm hoặc STT dạng Text
                    const allProductBtns = Array.from(document.querySelectorAll('button.pc_pin_product_pin, .pc_pin_product_pin, button.pc_pin_product_unpin, .pc_pin_product_unpin')).filter(btn => {
                        const c = btn.className || '';
                        if (c.includes('surprise-button') || c.includes('pc_pin_product_list_pin')) {
                            return false;
                        }
                        let p = btn.parentElement;
                        for (let i = 0; i < 5; i++) {
                            if (!p || p === document.body) break;
                            const pTxt = p.innerText || '';
                            const pClass = p.className || '';
                            if (pClass.includes('surprise-button') || pClass.includes('pc_pin_product_list_pin') || 
                                pTxt.includes('Danh sách sản phẩm trong LIVE này') || (pTxt.includes('Voucher') && pTxt.includes('cho đơn trên'))) {
                                return false;
                            }
                            p = p.parentElement;
                        }
                        return true;
                    });

                    for (let idx = 0; idx < allProductBtns.length; idx++) {
                        const btn = allProductBtns[idx];
                        let card = btn.parentElement;
                        for (let lvl = 0; lvl < 8; lvl++) {
                            if (!card || card === document.body) break;
                            if (card.querySelector('.pc_order_input, input, img') && (card.innerText || '').length > 10) {
                                break;
                            }
                            card = card.parentElement;
                        }

                        const cardText = card ? (card.innerText || '') : '';
                        let cardStt = null;
                        if (card) {
                            const orderInp = card.querySelector('.pc_order_input input, input[type="number"], input[role="spinbutton"], input.arco-input');
                            if (orderInp && orderInp.value && parseInt(orderInp.value, 10)) {
                                cardStt = parseInt(orderInp.value, 10);
                            }
                            if (!cardStt) {
                                const numEls = Array.from(card.querySelectorAll('div, span, p')).filter(el => {
                                    if (el.children.length > 0) return false;
                                    const t = (el.innerText || '').trim();
                                    return /^\d{1,3}$/.test(t);
                                });
                                if (numEls.length > 0) cardStt = parseInt(numEls[0].innerText.trim(), 10);
                            }
                        }

                        const isSttMatch = (targetStt > 0 && cardStt === targetStt);
                        const isNameMatch = (targetName && targetName.length >= 3 && cardText.toLowerCase().includes(targetName.substring(0, 18).toLowerCase()));

                        if (isSttMatch || isNameMatch) {
                            const btnClass = btn.className || '';
                            const btnText = (btn.innerText || '').toLowerCase();
                            if (btnClass.includes('pc_pin_product_unpin') || btnText.includes('bỏ ghim') || btnText.includes('đã ghim')) {
                                return { success: true, method: 'already_pinned_active' };
                            }

                            dispatchFullClick(btn);
                            return { success: true, method: 'pc_pin_product_pin_clicked' };
                        }
                    }

                    // 3. CHIẾN LƯỢC TOÀN NĂNG: ROW / CARD-FIRST UNIVERSAL SEARCH
                    // Bao quát mọi giao diện mới của TikTok Shop Seller Center VN và TikTok Live Studio Web
                    const rowContainers = Array.from(document.querySelectorAll('.arco-table-tr, tr, [role="row"], div[class*="table-row"], div[class*="product-item"], div[class*="product-card"], div[class*="item-wrapper"]'));
                    for (const row of rowContainers) {
                        const rowText = (row.innerText || '').toLowerCase();
                        if (rowText.includes('danh sách sản phẩm trong live này') || rowText.length < 5) continue;

                        let matched = false;
                        if (targetStt > 0) {
                            const inp = row.querySelector('input[type="number"], input[role="spinbutton"], input[data-tid*="number"], .arco-input');
                            if (inp && parseInt(inp.value || '0', 10) === targetStt) {
                                matched = true;
                            } else {
                                const m = rowText.match(/(?:^|\s)#?\s*(\d{1,3})(?:\.|\s|$)/);
                                if (m && parseInt(m[1], 10) === targetStt) {
                                    matched = true;
                                }
                            }
                        }
                        if (!matched && targetName && targetName.length >= 3) {
                            if (rowText.includes(targetName.substring(0, 15).toLowerCase())) {
                                matched = true;
                            }
                        }

                        if (matched) {
                            const btns = Array.from(row.querySelectorAll('button, [role="button"], a, span[class*="btn"], div[class*="btn"], .arco-btn'));
                            for (const b of btns) {
                                const bTxt = (b.innerText || '').trim().toLowerCase();
                                const bClass = (b.className || '').toLowerCase();
                                const bAria = (b.getAttribute('aria-label') || '').toLowerCase();
                                if (bClass.includes('pc_pin_product_unpin') || bTxt.includes('bỏ ghim') || bTxt.includes('đã ghim') || bAria.includes('bỏ ghim') || bTxt.includes('unpin')) {
                                    return { success: true, method: 'already_pinned_active' };
                                }
                                if (bClass.includes('pc_pin_product_pin') || bTxt === 'ghim' || bTxt.includes('ghim') || bAria.includes('ghim') || bTxt === 'pin' || bAria.includes('pin')) {
                                    b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    dispatchFullClick(b);
                                    return { success: true, method: 'universal_row_pin_clicked' };
                                }
                            }
                        }
                    }

                    return null;
                };

                // Thử tìm ngay lập tức
                let res = findTargetProductAndPin();
                if (res && res.success) {
                    await handleConfirmModal();
                    return res;
                }

                // Nếu chưa thấy, cuộn container từ từ
                const sc = getScrollContainer();
                if (sc && sc.scrollHeight > (sc.clientHeight || 500)) {
                    const totalH = sc.scrollHeight;
                    const step = 300;
                    for (let sy = 0; sy <= totalH; sy += step) {
                        if (sc.scrollTop !== undefined) sc.scrollTop = sy;
                        else if (sc.scrollBy) sc.scrollBy(0, step);
                        else window.scrollBy(0, step);
                        await sleep(150);
                        
                        res = findTargetProductAndPin();
                        if (res && res.success) {
                            await handleConfirmModal();
                            return res;
                        }
                    }
                    // Reset scroll về đầu
                    if (sc.scrollTop !== undefined) sc.scrollTop = 0;
                }

                return { success: false };
            }""", {
                "stt": stt_num,
                "name": prod_name,
                "auto_scroll": self.auto_scroll,
            })

            if res and res.get("success"):
                method = res.get("method", "unknown")
                if method == "already_pinned_active":
                    self.log("SUCCESS", f"🔥 [TIKTOK LIVE] SP #{pid_str} hiện ĐANG ĐƯỢC GHIM SẴN trên màn hình Live!")
                else:
                    self.log("SUCCESS", f"🔥 [TIKTOK LIVE] Đã BẤM NÚT GHIM THỰC TẾ cho SP #{pid_str} thành công ({method})!")
                return True
            else:
                self.log("WARNING", f"⚠️ Không tìm thấy nút Ghim cho SP #{pid_str} trên bảng Live.")
                return False

        except Exception as e:
            self.log("ERROR", f"❌ Lỗi thao tác ghim SP '{product_id}': {e}")
            return False

    def test_pin_single_product(self, product_id: str | int = "1") -> bool:
        """Thử nghiệm ghim 1 sản phẩm ngay lập tức để kiểm tra kết nối."""
        self.log("INFO", f"⚡ Bắt đầu thao tác Ghim Thử Sản Phẩm #{product_id}...")
        self.set_status("Đang Ghim Thử...", "#00FFFF")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                except Exception:
                    self.log("WARNING", "⚠️ Chrome CDP 9222 chưa mở. Đang tự động kích hoạt trình duyệt...")
                    self.launch_browser()
                    time.sleep(2.0)
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")

                contexts = browser.contexts
                active_context = contexts[0] if contexts else browser
                pages = active_context.pages

                target_page = None
                for pg in pages:
                    try:
                        url_str = (pg.url or "").lower()
                        if "product/dashboard" in url_str or "streamer" in url_str:
                            target_page = pg
                            break
                        elif "tiktok.com" in url_str:
                            target_page = pg
                    except Exception:
                        pass

                page = target_page or (pages[0] if pages else active_context.new_page())
                success = self._do_pin(page, str(product_id))

                if self.event_callback:
                    self.event_callback({
                        "type": "PIN_EVENT_TRIGGERED",
                        "product_id": str(product_id),
                        "mode": "test",
                        "round": 1,
                        "direction": "Test ⚡",
                        "success": success,
                    })

                if success:
                    self.set_status("Ghim Thử Thành Công", "#00FF66")
                else:
                    self.set_status("Ghim Thử Thất Bại", "#FF9900")
                return success

        except Exception as err:
            self.log("ERROR", f"❌ Lỗi khi ghim thử SP #{product_id}: {err}")
            self.set_status("Lỗi Ghim Thử", "#FF3344")
            return False

    def pin_priority_product(self, product_id: str | int, hold_seconds: int | None = None) -> bool:
        """
        Ghim ƯU TIÊN sản phẩm theo yêu cầu của khách qua comment (On-Demand / Customer Priority Pin).
        Tạm dừng hệ thống ghim tự động và KHÓA GIỮ CỐ ĐỊNH trong 40s - 60s để khách xem và chốt đơn,
        sau đó hệ thống ghim tự động sẽ tự động tiếp tục chu kỳ bình thường.
        """
        if hold_seconds is not None:
            hold_sec = hold_seconds
        else:
            # Mặc định ngẫu nhiên trong khoảng 40s - 60s theo tiêu chuẩn DTA
            hold_sec = random.randint(40, 60)

        pid_str = str(product_id).strip()
        if not pid_str:
            return False

        self.record_product_interest(pid_str)
        self.priority_pinned_pid = pid_str
        self.priority_pin_lock_until = time.time() + hold_sec

        self.log("ACTION", f"🎯 [VÙNG 1: GHIM ƯU TIÊN] Tạm dừng ghim auto -> Ghim ngay SP #{pid_str} & GIỮ {hold_sec}s cho khách chốt đơn!")
        self.set_status(f"Ưu Tiên SP #{pid_str} ({hold_sec}s)", "#00FFFF")

        # Tiến hành ghim ngay lập tức
        ok = self.test_pin_single_product(pid_str)
        if self.event_callback:
            self.event_callback({
                "type": "PRIORITY_PIN_LOCKED",
                "product_id": pid_str,
                "hold_seconds": hold_sec,
                "lock_until": self.priority_pin_lock_until,
                "success": ok,
            })
        return ok

    def check_and_pin_by_keyword(self, comment_text: str) -> bool:
        """Kiểm tra từ khóa trong comment và ghim sản phẩm tương ứng nếu trùng khớp mapping."""
        if not self.is_running or not self.keyword_mapping:
            return False

        c_low = comment_text.lower().strip()
        for pid, keywords in self.keyword_mapping.items():
            for kw in keywords:
                if kw and kw in c_low:
                    self.log("ACTION", f"📌 [KEYWORD PIN] Phát hiện từ khóa '{kw}' -> Ghim ưu tiên SP #{pid}...")
                    return self.pin_priority_product(pid)
        return False

    def _pin_loop(self):
        """
        Vòng lặp Ghim Sản Phẩm Đa Chế Độ có điều phối thông minh:
        Tạm dừng vòng lặp khi có Khóa Giữ Ưu Tiên của khách (Priority Hold Window).
        """
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                self.log("INFO", f"🔌 Kết nối CDP tới Chrome (Cổng {self.cdp_port})...")
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                except Exception:
                    self.log("WARNING", "⚠️ Chrome CDP 9222 chưa mở. Tự động kích hoạt...")
                    self.launch_browser()
                    time.sleep(2.0)
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")

                contexts = browser.contexts
                active_context = contexts[0] if contexts else browser
                pages = active_context.pages

                target_page = None
                for pg in pages:
                    try:
                        url_str = (pg.url or "").lower()
                        if "product/dashboard" in url_str or "streamer" in url_str:
                            target_page = pg
                            break
                        elif "tiktok.com" in url_str:
                            target_page = pg
                    except Exception:
                        pass

                page = target_page or (pages[0] if pages else active_context.new_page())

                round_count = 1
                while self.is_running:
                    # Xác định chuỗi thứ tự theo chế độ
                    if self.mode == "random":
                        current_sequence = random.sample(self.product_list, len(self.product_list))
                        dir_str = "Ngẫu nhiên 🎲"
                    elif self.mode == "loop":
                        current_sequence = list(self.product_list)
                        dir_str = "Tuần tự 🔄"
                    elif self.mode == "flash_sale":
                        # Ưu tiên các sản phẩm Flash Sale / Đang kết thúc sau xuất hiện nhiều hơn
                        flash_pids = []
                        for p in self.products_catalog:
                            c = (p.get("campaign") or "").lower()
                            if "flash" in c or "kết thúc" in c or "giảm" in c or "ưu đãi" in c:
                                flash_pids.append(str(p.get("stt")))
                        active_flash = [pid for pid in flash_pids if pid in self.product_list]
                        current_sequence = active_flash + list(self.product_list) if active_flash else list(self.product_list)
                        dir_str = "Ưu tiên Flash Sale 🔥"
                    elif self.mode == "hot_demand":
                        # Ưu tiên các sản phẩm khách hỏi nhiều nhất
                        sorted_pids = sorted(
                            self.product_list,
                            key=lambda pid: self.product_interest_counts.get(str(pid), 0),
                            reverse=True,
                        )
                        hot_items = [pid for pid in sorted_pids if self.product_interest_counts.get(str(pid), 0) > 0]
                        current_sequence = hot_items + sorted_pids if hot_items else sorted_pids
                        dir_str = "Ưu tiên Nhu Cầu Hỏi 📈"
                    else:  # ping_pong
                        is_forward = (round_count % 2 != 0)
                        if is_forward:
                            current_sequence = list(self.product_list)
                            dir_str = "Xuôi ➡️"
                        else:
                            reversed_list = list(reversed(self.product_list))
                            if len(reversed_list) > 1:
                                current_sequence = reversed_list[1:] + [reversed_list[0]]
                            else:
                                current_sequence = reversed_list
                            dir_str = "Ngược ⬅️"

                    self.log("INFO", f"🔄 [LƯỢT GHIM #{round_count}] Bắt đầu chu kỳ {dir_str} (Thứ tự: {', '.join(current_sequence)})")

                    for item_idx, current_pid in enumerate(current_sequence, start=1):
                        if not self.is_running:
                            break

                        # Kiểm tra xem có đang bị Khóa Giữ Ưu Tiên cho khách hỏi hay không
                        while self.is_running and time.time() < self.priority_pin_lock_until:
                            remain = int(self.priority_pin_lock_until - time.time())
                            if remain > 0 and remain % 15 == 0:
                                self.log("INFO", f"⏳ [GIỮ ƯU TIÊN KHÁCH] Đang ghim cố định SP #{self.priority_pinned_pid} cho khách xem chốt đơn (còn {remain}s)...")
                            time.sleep(1.0)

                        if not self.is_running:
                            break

                        self.log("INFO", f"📌 (Lượt #{round_count} - {dir_str}) Ghim SP #{current_pid} lên đầu [{item_idx}/{len(current_sequence)}]...")
                        ok = self._do_pin(page, current_pid)

                        # Ghi nhận số lượt ghim vào bộ đếm
                        self.record_pin_action(current_pid)

                        # Tìm thông tin chi tiết của sản phẩm để gửi kèm sự kiện
                        prod_detail = None
                        for p in self.products_catalog:
                            if str(p.get("stt")) == str(current_pid):
                                prod_detail = p
                                break

                        # Tính toán thời gian chờ ngẫu nhiên (Random Jitter) chống lặp lại / chống bot detection
                        if self.random_interval:
                            if self.interval_min is not None and self.interval_max is not None:
                                min_s = max(3, min(self.interval_min, self.interval_max))
                                max_s = max(min_s + 1, max(self.interval_min, self.interval_max))
                                current_wait_sec = random.randint(min_s, max_s)
                            else:
                                base = self.interval_seconds
                                min_s = max(4, int(base * 0.75))
                                max_s = max(min_s + 2, int(base * 1.35))
                                current_wait_sec = random.randint(min_s, max_s)
                        else:
                            current_wait_sec = self.interval_seconds

                        if self.event_callback:
                            self.event_callback({
                                "type": "PIN_EVENT_TRIGGERED",
                                "product_id": str(current_pid),
                                "product_name": prod_detail.get("name") if prod_detail else f"Sản phẩm #{current_pid}",
                                "sale_price": prod_detail.get("sale_price") if prod_detail else "",
                                "stock": prod_detail.get("stock") if prod_detail else "",
                                "campaign": prod_detail.get("campaign") if prod_detail else "",
                                "round": round_count,
                                "mode": self.mode,
                                "direction": dir_str,
                                "success": ok,
                                "wait_seconds": current_wait_sec,
                                "pin_counts": dict(self.pin_counts),
                                "interest_counts": dict(self.product_interest_counts),
                            })

                        if self.random_interval:
                            self.log("INFO", f"⏳ [Random Thời Gian] Giữ ghim SP #{current_pid} trong {current_wait_sec}s (Gốc: {self.interval_seconds}s) trước khi đổi SP tiếp theo...")

                        # Chờ khoảng thời gian current_wait_sec (nhưng nếu có khách hỏi ưu tiên thì dừng chờ để ưu tiên ngay)
                        for _ in range(current_wait_sec):
                            if not self.is_running:
                                break
                            if time.time() < self.priority_pin_lock_until:
                                break
                            time.sleep(1.0)

                    round_count += 1

        except Exception as err:
            self.log("ERROR", f"❌ Lỗi luồng ghim SP: {err}")
            self.set_status("Lỗi Luồng Ghim", "#FF3344")

    def close(self):
        self.stop_pinning()
