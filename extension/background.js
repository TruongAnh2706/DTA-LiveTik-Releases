/**
 * DTA AutoLive Chrome Extension Bridge - Background Service Worker
 * WebSocket Client connecting to ws://127.0.0.1:8765
 */

let ws = null;
const SERVER_URL = "ws://127.0.0.1:8765";
const PAIRING_TOKEN = "dta_autolive_secret_pairing_token_v1.1";

function connectWebSocket() {
  ws = new WebSocket(SERVER_URL);

  ws.onopen = () => {
    console.log("[DTA Bridge] Connected to DTA AutoLive Desktop Application.");
    // Send Handshake HELLO
    const helloPayload = {
      type: "HELLO",
      version: "1.1.0",
      token: PAIRING_TOKEN
    };
    ws.send(JSON.stringify(helloPayload));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("[DTA Bridge] Received Message:", data);

      if (data.type === "WELCOME") {
        console.log("[DTA Bridge] Handshake Success. Extension Active.");
      } else if (data.type === "PIN_PRODUCT") {
        // Forward to Content Script to trigger TikTok Seller Center Pin
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]) {
            chrome.tabs.sendMessage(tabs[0].id, data);
          }
        });
        // Send ACK back to Desktop App
        const ack = {
          type: "COMMAND_RESULT",
          event_id: data.event_id,
          status: "SUCCESS",
          message: `Product ${data.payload?.product_id} Pinned Successfully.`
        };
        ws.send(JSON.stringify(ack));
      }
    } catch (e) {
      console.error("[DTA Bridge] Error parsing message:", e);
    }
  };

  ws.onclose = () => {
    console.warn("[DTA Bridge] Connection closed. Retrying in 3s...");
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("[DTA Bridge] WebSocket Error:", err);
  };
}

// Listen for detected streams from content.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "LIVE_STREAM_DETECTED") {
    console.log("[DTA Bridge] Live Stream Detected in Tab:", message);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        command: "TIKTOK_LIVE_SNIFFED",
        stream_url: message.streamUrl || message.videoSrc || "",
        page_url: message.url || ""
      }));
    }
    sendResponse({ status: "SENT_TO_DTA_APP" });
  }
  return true;
});

// Start WebSocket connection
connectWebSocket();
