"""DTA Studio - TikTok Shop Live Cart Scraper Engine.

Connects to TikTok Shop Streamer Dashboard via Chrome DevTools Protocol (CDP :9222)
and extracts complete real-time product data: STT, Title, Discount Price, Original Price,
Campaign / Flash Sale status, and Inventory Stock.
"""

import time
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()


class TikTokCartScraper:
    """Extracts live cart catalog from shop.tiktok.com/streamer/live/product/dashboard."""

    def __init__(
        self,
        cdp_port: int = 9222,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self.cdp_port = cdp_port
        self.log_callback = log_callback
        self.cached_products: list[dict[str, Any]] = []
        self.last_scraped_time: float = 0.0

    def log(self, tag: str, text: str) -> None:
        """Log message with callback support."""
        if self.log_callback:
            self.log_callback(tag, text)
        else:
            logger.info("tiktok_cart_scraper", tag=tag, text=text)

    def scrape_cart(self) -> dict[str, Any]:
        """Scrape live cart DOM via Playwright CDP connection."""
        self.log("INFO", f"🛒 Đang kết nối Chrome CDP ({self.cdp_port}) để cào dữ liệu giỏ hàng...")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                except Exception as e:
                    self.log("WARNING", f"⚠️ Chưa kết nối được cổng CDP {self.cdp_port}: {e}. Đang tự động kích hoạt trình duyệt Chrome...")
                    self.launch_browser()
                    time.sleep(2.0)
                    try:
                        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                    except Exception as e2:
                        self.log("ERROR", f"❌ Không thể kết nối cổng CDP {self.cdp_port}: {e2}. Vui lòng kiểm tra Chrome Live!")
                        return self._fallback_simulated_cart("Chưa mở trình duyệt Chrome CDP 9222")

                all_pages = []
                for ctx in browser.contexts:
                    all_pages.extend(ctx.pages)
                if not all_pages and hasattr(browser, "pages"):
                    all_pages = browser.pages

                target_page = None
                for pg in all_pages:
                    try:
                        url_l = pg.url.lower()
                        if "tiktok.com" in url_l and ("streamer" in url_l or "product" in url_l or "dashboard" in url_l or "live" in url_l or "seller" in url_l):
                            target_page = pg
                            break
                    except Exception:
                        pass

                if not target_page:
                    for pg in all_pages:
                        try:
                            if "tiktok" in pg.url.lower():
                                target_page = pg
                                break
                        except Exception:
                            pass

                if not target_page and all_pages:
                    target_page = all_pages[0]

                if not target_page:
                    self.log("WARNING", "⚠️ Không tìm thấy Tab TikTok Live trong trình duyệt Chrome.")
                    return self._fallback_simulated_cart("Không tìm thấy Tab Streamer Live Dashboard")

                self.log("INFO", f"🌐 Đã kết nối Tab: {target_page.url}. Đang kích hoạt cuộn ảo đa tầng (Deep Virtual Scroll) để cào 100% giỏ hàng...")

                # Evaluate comprehensive DOM extraction script with multi-container virtual scroll
                extracted_data: list[dict[str, Any]] = target_page.evaluate(r"""async () => {
                    // Helper to identify all scrollable containers on the page
                    const getScrollableElements = () => {
                        const list = [];
                        document.querySelectorAll('*').forEach(el => {
                            try {
                                const style = window.getComputedStyle(el);
                                const overflow = style.overflowY || style.overflow;
                                if ((overflow === 'auto' || overflow === 'scroll') && el.scrollHeight > el.clientHeight + 40) {
                                    list.push(el);
                                }
                            } catch (e) {}
                        });
                        return list;
                    };

                    const scrollables = getScrollableElements();
                    const productsMap = new Map();

                    const isPriceOnlyLine = (str) => {
                        const trimmed = str.trim();
                        if (/^[0-9.,\s₫đVNĐvndĐ\-\/]+$/i.test(trimmed)) return true;
                        if (/^([0-9]{1,3}(?:[.,][0-9]{3})*\s*(?:đ|₫|vnđ|vnd|đ)?\s*)+$/i.test(trimmed)) return true;
                        if (/^[0-9]{1,3}(?:[.,][0-9]{3})+\s*[đ₫VNĐvndĐ]?$/i.test(trimmed)) return true;
                        return false;
                    };

                    const isSystemUiOrTag = (str) => {
                        const low = str.trim().toLowerCase();
                        if (!low || low.length < 2) return true;
                        if (low.startsWith('còn') || low.startsWith('kho:') || low.includes('minh họa')) return true;

                        const systemBlacklist = [
                            'toggle sidebar', 'toggle', 'sidebar', 'yêu cầu minh họa', 'đã yêu cầu',
                            'đưa lên đầu', 'ghim', 'hủy ghim', 'sửa', 'xóa', 'thao tác', 'chỉnh sửa',
                            'lựa chọn yêu thích', 'flash sale', 'kết thúc sau', 'yêu thích',
                            'khuyến mãi live', 'sản phẩm', 'xem trước', 'đang phát', 'chưa phát',
                            'icon', 'button', 'avatar', 'svg', 'close', 'arrow', 'collapse', 'expand'
                        ];

                        if (systemBlacklist.some(item => low === item || low.startsWith(item + ':') || low.startsWith(item + ' '))) return true;
                        return false;
                    };

                    const parseCardElements = (cardEl) => {
                        if (!cardEl) return null;
                        const text = (cardEl.innerText || '').trim();
                        if (!text || text.length < 3) return null;

                        // LOẠI TRỪ TUYỆT ĐỐI VOUCHER VÀ BUNDLE
                        if (cardEl.querySelector('.surprise-button, .pc_pin_product_list_pin') || 
                            text.includes('cho đơn trên') || text.includes('Danh sách sản phẩm trong LIVE này') ||
                            (text.includes('Voucher') && text.includes('Giảm'))) {
                            return null;
                        }

                        const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
                        if (lines.length === 0) return null;

                        // 1. EXTRACT STT (Exact Number from card)
                        let stt = 0;
                        const inp = cardEl.querySelector('.pc_order_input input, input[role="spinbutton"], input[type="number"]');
                        if (inp && inp.value && parseInt(inp.value, 10)) {
                            stt = parseInt(inp.value, 10);
                        }
                        if (!stt) {
                            const numEl = cardEl.querySelector('div[class*="index"], span[class*="index"], div[class*="order"], span[class*="order"], div[class*="num"], span[class*="num"], div[class*="seq"]');
                            if (numEl && numEl.innerText && /^\s*([0-9]{1,3})\s*$/.test(numEl.innerText)) {
                                stt = parseInt(numEl.innerText.trim(), 10);
                            }
                        }
                        if (!stt) {
                            for (let i = 0; i < Math.min(3, lines.length); i++) {
                                if (/^\s*([0-9]{1,3})\s*$/.test(lines[i])) {
                                    stt = parseInt(lines[i], 10);
                                    break;
                                }
                            }
                        }
                        if (!stt) {
                            const leadMatch = text.match(/^\s*([0-9]{1,3})\b/);
                            if (leadMatch) {
                                stt = parseInt(leadMatch[1], 10);
                            }
                        }
                        if (!stt || stt <= 0 || stt > 999) return null;

                        // 2. EXTRACT TITLE (Tier 1: img[alt] -> Tier 2: title elements -> Tier 3: clean text lines)
                        let title = '';

                        // Tier 1: img[alt]
                        const img = cardEl.querySelector('img[alt]');
                        if (img && img.alt) {
                            const altVal = img.alt.trim();
                            if (altVal.length >= 6 && !isSystemUiOrTag(altVal) && !isPriceOnlyLine(altVal)) {
                                title = altVal;
                            }
                        }

                        // Tier 2: Dedicated Title Elements
                        if (!title) {
                            const titleNodes = Array.from(cardEl.querySelectorAll('div[class*="title"], span[class*="title"], div[class*="name"], span[class*="name"], .arco-typography, p, h1, h2, h3, h4, a'));
                            for (const node of titleNodes) {
                                const tAttr = (node.getAttribute('title') || '').trim();
                                if (tAttr.length >= 6 && !isSystemUiOrTag(tAttr) && !isPriceOnlyLine(tAttr)) {
                                    title = tAttr;
                                    break;
                                }
                                const nodeText = (node.innerText || '').trim();
                                if (nodeText.length >= 6 && !isSystemUiOrTag(nodeText) && !isPriceOnlyLine(nodeText)) {
                                    title = nodeText;
                                    break;
                                }
                            }
                        }

                        // Tier 3: Scan text lines
                        if (!title) {
                            const cleanLines = lines.filter(l => {
                                if (/^\s*[0-9]{1,3}\s*$/.test(l)) return false; // Pure STT
                                if (isPriceOnlyLine(l)) return false;
                                if (isSystemUiOrTag(l)) return false;
                                return l.length >= 4 && /[a-zA-ZÀ-ỹ]{2,}/.test(l);
                            });

                            if (cleanLines.length > 0) {
                                // Pick the longest clean line
                                cleanLines.sort((a, b) => b.length - a.length);
                                title = cleanLines[0];
                            }
                        }

                        // Clean any trailing prices or noise from title
                        if (title) {
                            title = title.replace(/\s*([0-9]{1,3}(?:[.,][0-9]{3})+\s*[đ₫VNĐvndĐ]?)\s*$/gi, '').trim();
                            if (isSystemUiOrTag(title) || isPriceOnlyLine(title)) {
                                title = '';
                            }
                        }

                        // 3. EXTRACT PRICES
                        const priceMatches = text.match(/[0-9]{1,3}(?:[.,][0-9]{3})*\s*(?:đ|₫|VNĐ|vnd|Đ)/gi) || [];
                        let salePrice = priceMatches[0] || '';
                        let originalPrice = priceMatches[1] || '';

                        if (!salePrice) {
                            const rawNumMatch = text.match(/\b([0-9]{1,3}(?:[.,][0-9]{3})+)\b/);
                            if (rawNumMatch) {
                                salePrice = rawNumMatch[1] + 'đ';
                            } else {
                                salePrice = 'Chưa rõ giá';
                            }
                        }

                        // 4. EXTRACT STOCK
                        let stock = 'Còn hàng';
                        const stockLine = lines.find(l => l.toLowerCase().startsWith('còn') || l.toLowerCase().startsWith('kho:'));
                        if (stockLine) {
                            const sMatch = stockLine.match(/Còn(?:\s*ít)?\s*:\s*([^|\n]+)/i) || stockLine.match(/Kho\s*:\s*([^|\n]+)/i);
                            stock = sMatch ? `Còn: ${sMatch[1].trim()}` : stockLine.split('|')[0].trim();
                        } else {
                            const sMatch = text.match(/Còn(?:\s*ít)?\s*:\s*([0-9]+(?:[.,][0-9]+)?[KkMm]?)/i);
                            if (sMatch) stock = `Còn: ${sMatch[1]}`;
                        }

                        // 5. EXTRACT CAMPAIGN
                        let campaign = 'Thường';
                        if (text.includes('Kết thúc sau')) {
                            const cMatch = text.match(/Kết thúc sau[^\n]+/);
                            if (cMatch) campaign = cMatch[0];
                        } else if (text.toLowerCase().includes('flash sale')) {
                            campaign = 'Flash Sale';
                        } else if (text.includes('Lựa chọn yêu thích') || text.includes('Yêu thích')) {
                            campaign = 'Yêu thích';
                        } else if (text.includes('Khuyến mãi Live')) {
                            campaign = 'Khuyến mãi Live';
                        }

                        return {
                            stt,
                            name: title || `Sản phẩm #${stt}`,
                            sale_price: salePrice,
                            original_price: originalPrice,
                            stock,
                            campaign
                        };
                    };

                    const scanAllCards = () => {
                        // 1. Scan from all product thumbnails
                        const imgs = Array.from(document.querySelectorAll('img')).filter(img => {
                            return img.src && (img.src.includes('byteimg') || img.src.includes('tiktok') || img.src.includes('tos-') || (img.width >= 25 && img.height >= 25));
                        });

                        imgs.forEach(img => {
                            let card = img;
                            for (let i = 0; i < 6; i++) {
                                if (card && card.parentElement && card.parentElement !== document.body) {
                                    card = card.parentElement;
                                    if (card.innerText && (card.innerText.includes('đ') || card.innerText.includes('₫') || card.innerText.includes('Còn:'))) {
                                        break;
                                    }
                                }
                            }
                            if (card) {
                                const parsed = parseCardElements(card);
                                if (parsed && parsed.stt) {
                                    const existing = productsMap.get(parsed.stt);
                                    const hasRealName = parsed.name && !parsed.name.startsWith('Sản phẩm #');
                                    if (!existing || (!existing.name && hasRealName) || (existing.name.startsWith('Sản phẩm #') && hasRealName) || (hasRealName && parsed.name.length > existing.name.length)) {
                                        productsMap.set(parsed.stt, parsed);
                                    }
                                }
                            }
                        });

                        // 2. Scan from order inputs / spinbuttons
                        const orderInputs = Array.from(document.querySelectorAll('.pc_order_input input, input[role="spinbutton"], input[type="number"]'));
                        orderInputs.forEach(inp => {
                            let card = inp;
                            for (let i = 0; i < 8; i++) {
                                if (card && card.parentElement && card.parentElement !== document.body) {
                                    card = card.parentElement;
                                    if (card.querySelector('img') && (card.innerText.includes('đ') || card.innerText.includes('₫') || card.innerText.includes('Còn:'))) {
                                        break;
                                    }
                                }
                            }
                            if (card) {
                                const parsed = parseCardElements(card);
                                if (parsed && parsed.stt) {
                                    const existing = productsMap.get(parsed.stt);
                                    const hasRealName = parsed.name && !parsed.name.startsWith('Sản phẩm #');
                                    if (!existing || (!existing.name && hasRealName) || (existing.name.startsWith('Sản phẩm #') && hasRealName) || (hasRealName && parsed.name.length > existing.name.length)) {
                                        productsMap.set(parsed.stt, parsed);
                                    }
                                }
                            }
                        });

                        // 3. Scan generic table rows and cards
                        const rows = Array.from(document.querySelectorAll('.arco-table-row, tr, div[class*="table-row"], div[class*="item-card"], div[class*="product_item"]'));
                        rows.forEach(r => {
                            const parsed = parseCardElements(r);
                            if (parsed && parsed.stt) {
                                const existing = productsMap.get(parsed.stt);
                                const hasRealName = parsed.name && !parsed.name.startsWith('Sản phẩm #');
                                if (!existing || (!existing.name && hasRealName) || (existing.name.startsWith('Sản phẩm #') && hasRealName) || (hasRealName && parsed.name.length > existing.name.length)) {
                                    productsMap.set(parsed.stt, parsed);
                                }
                            }
                        });
                    };

                    // Step 1: Scroll all containers to top
                    scrollables.forEach(s => { s.scrollTop = 0; });
                    window.scrollTo(0, 0);
                    await new Promise(r => setTimeout(r, 200));

                    // Step 2: Multi-step deep auto-scroll loop (up to 40 steps)
                    for (let step = 0; step < 40; step++) {
                        scanAllCards();

                        // Scroll each scrollable container and dispatch wheel events
                        scrollables.forEach(s => {
                            s.scrollTop += 280;
                            s.dispatchEvent(new WheelEvent('wheel', { deltaY: 300, bubbles: true }));
                        });

                        window.scrollBy(0, 280);
                        window.dispatchEvent(new WheelEvent('wheel', { deltaY: 300, bubbles: true }));

                        await new Promise(r => setTimeout(r, 200));
                    }

                    // Final scan at bottom
                    scanAllCards();

                    // Step 3: Scroll back to top
                    scrollables.forEach(s => { s.scrollTop = 0; });
                    window.scrollTo(0, 0);

                    return Array.from(productsMap.values()).sort((a, b) => a.stt - b.stt);
                }""")

                if extracted_data:
                    self.cached_products = extracted_data
                    self.last_scraped_time = time.time()
                    self.log("SUCCESS", f"✅ Đã cào thành công {len(extracted_data)} sản phẩm từ TikTok Live Dashboard!")
                    return {
                        "success": True,
                        "products": extracted_data,
                        "count": len(extracted_data),
                        "timestamp": self.last_scraped_time,
                        "knowledge_base_text": self.format_knowledge_base_text(extracted_data),
                    }

                self.log("WARNING", "⚠️ Không tìm thấy danh sách sản phẩm trong DOM. Sử dụng dữ liệu mẫu.")
                return self._fallback_simulated_cart("DOM trống hoặc chưa tải xong giỏ hàng")

        except Exception as e:
            self.log("ERROR", f"❌ Lỗi khi cào giỏ hàng: {e}")
            return self._fallback_simulated_cart(str(e))

    def format_knowledge_base_text(self, products: list[dict[str, Any]] | None = None) -> str:
        """Format products into concise structured text for AI prompt injection."""
        items = products or self.cached_products
        if not items:
            return "Chưa có thông tin sản phẩm trong giỏ hàng."

        lines = []
        from dta_autolive.infrastructure.dta_qwen_engine import format_price_shorthand

        for p in items:
            stt = p.get("stt", "?")
            name = p.get("name", "Sản phẩm")
            sale_price = format_price_shorthand(p.get("sale_price", ""))
            orig_price = f" (Giá gốc: {format_price_shorthand(p.get('original_price'))})" if p.get("original_price") else ""
            campaign = f" [{p.get('campaign')}]" if p.get("campaign") else ""
            stock = f" - Tồn kho: {p.get('stock')}" if p.get("stock") else ""
            lines.append(f"• Mã SP {stt}: {name} - Giá: {sale_price}{orig_price}{campaign}{stock}")

        return "\n".join(lines)

    def _fallback_simulated_cart(self, reason: str = "") -> dict[str, Any]:
        """Provide mock fallback data if browser is not connected."""
        simulated = [
            {
                "stt": 1,
                "name": "Xả Hàng Thao Dao Quỷ 5H - 28i bản cao cấp phôi full cacbon",
                "sale_price": "620.000đ",
                "original_price": "1.200.000đ",
                "campaign": "Kết thúc sau 1 ngày (Flash Sale)",
                "stock": "Còn ít: 3",
            },
            {
                "stt": 2,
                "name": "Xả Hàng Cần Đài Hắc Đạo Phong 6H-19i full cacbon cao cấp",
                "sale_price": "500.000đ",
                "original_price": "900.000đ",
                "campaign": "Kết thúc sau 1 ngày",
                "stock": "Còn: 77",
            },
            {
                "stt": 3,
                "name": "(BẢO HÀNH) Cần Câu Tay Hoàng Đan 5.5H Phân Bổ Lực 28i",
                "sale_price": "315.999đ",
                "original_price": "460.000đ",
                "campaign": "Khuyến mãi Live",
                "stock": "Còn: 163",
            },
            {
                "stt": 4,
                "name": "Xả Hàng Cần Đài Huyền Thiên 6H-19i full cacbon 30-40T",
                "sale_price": "500.000đ",
                "original_price": "900.000đ",
                "campaign": "Kết thúc sau 1 ngày",
                "stock": "Còn: 170",
            },
        ]
        self.cached_products = simulated
        self.last_scraped_time = time.time()
        return {
            "success": False,
            "reason": reason,
            "is_simulated": True,
            "products": simulated,
            "count": len(simulated),
            "timestamp": self.last_scraped_time,
            "knowledge_base_text": self.format_knowledge_base_text(simulated),
        }
