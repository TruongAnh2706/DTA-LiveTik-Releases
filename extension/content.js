/**
 * DTA AutoLive Chrome Extension Bridge - Content Script
 * Supports TikTok Live Sniffing & TikTok Shop Streamer AutoPin
 */

console.log("[DTA AutoLive Extension] Content script loaded on:", window.location.href);

// 1. Auto Sniff TikTok Live Stream Video URL
function sniffTikTokLiveStream() {
  const currentUrl = window.location.href;
  if (!currentUrl.includes("tiktok.com")) return;

  // Check for video src or source tags
  const video = document.querySelector("video");
  if (video && video.src && (video.src.includes(".flv") || video.src.includes(".m3u8") || video.src.includes("pull-") || video.src.includes("blob:"))) {
    chrome.runtime.sendMessage({
      type: "LIVE_STREAM_DETECTED",
      url: currentUrl,
      videoSrc: video.src
    });
  }

  // Check for script tags containing pull URLs
  try {
    const scripts = document.querySelectorAll("script");
    scripts.forEach(s => {
      if (s.textContent && (s.textContent.includes(".flv") || s.textContent.includes("pull_data"))) {
        const flvMatch = s.textContent.match(/(https?:\/\/[^\s"\\]+?\.flv[^\s"\\]*)/);
        if (flvMatch && flvMatch[1]) {
          const cleanFlv = flvMatch[1].replace(/\\u0026/g, "&").replace(/\\/g, "");
          chrome.runtime.sendMessage({
            type: "LIVE_STREAM_DETECTED",
            url: currentUrl,
            streamUrl: cleanFlv
          });
        }
      }
    });
  } catch (e) {
    // Ignore parse errors
  }
}

// Run sniffing when page loads
setTimeout(sniffTikTokLiveStream, 2000);
setTimeout(sniffTikTokLiveStream, 5000);

// 2. Handle AutoPin Commands for TikTok Shop Streamer
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "PIN_PRODUCT") {
    const productId = request.payload?.product_id;
    console.log(`[DTA Content Script] Executing PIN_PRODUCT for ID: ${productId}`);

    // Click selector for official Streamer Product Dashboard
    const topButtons = document.querySelectorAll('.pc_top_product, .pin-btn, button[role="button"]');
    if (topButtons.length > 0) {
      const btn = topButtons[0];
      btn.click();
      console.log(`[DTA Content Script] Clicked top product pin button`);
    }

    sendResponse({ status: "SUCCESS", productId });
  }
  return true;
});
