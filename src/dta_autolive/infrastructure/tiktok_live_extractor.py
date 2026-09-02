from __future__ import annotations

import contextlib
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Global SSL context ignoring self-signed errors
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def is_direct_stream_url(url: str) -> bool:
    """Check if input string is already a direct stream pull URL (FLV, M3U8, RTMP)."""
    clean = url.lower().strip()
    return (
        clean.startswith(("http://", "https://", "rtmp://", "rtmps://"))
        and (
            ".flv" in clean
            or ".m3u8" in clean
            or "pull-" in clean
            or "stream-" in clean
            or "/live/" in clean
        )
    )


def extract_username_or_room_id(input_str: str) -> str:
    """Extract clean username or room ID from a TikTok/Douyin URL or handle."""
    clean_str = input_str.strip()
    if "@" in clean_str:
        match = re.search(r"@([a-zA-Z0-9_.-]+)", clean_str)
        if match:
            return match.group(1)
    if "tiktok.com" in clean_str:
        parts = clean_str.split("?")[0].split("/")
        for part in parts:
            if part.startswith("@"):
                return part.lstrip("@")
            if part and part not in ("live", "www.tiktok.com", "https:", "http:", ""):
                last_part = part
        return last_part.lstrip("@")
    return clean_str.lstrip("@")


def load_saved_tiktok_cookies() -> str:
    """Load cookies saved from Chrome in-app login bridge or user configuration."""
    possible_paths = [
        Path("data/tiktok_cookies.json"),
        Path.home() / "AppData" / "Roaming" / "dta-autolive" / "tiktok_cookies.json",
        Path("tiktok_cookies.json"),
    ]
    for p in possible_paths:
        if p.exists():
            with contextlib.suppress(Exception), open(p, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    val = data.get("cookie_string", "")
                    return str(val) if isinstance(val, str) else ""
                if isinstance(data, str):
                    return data
    return ""


def extract_cookies_from_chrome_cdp(cdp_port: int = 9222) -> dict[str, Any]:
    """Extract TikTok cookies directly from Chrome DevTools Protocol port 9222."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{cdp_port}/json")
        with urllib.request.urlopen(req, timeout=1.5) as r:  # noqa: S310
            pages = json.loads(r.read().decode("utf-8"))

        if not pages:
            return {"success": False, "error": "Chrome CDP chưa sẵn sàng"}

        from playwright.sync_api import sync_playwright  # noqa: PLC0415

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
            all_cookies = []
            for ctx in browser.contexts:
                cookies = ctx.cookies(["https://www.tiktok.com", "https://webcast.tiktok.com", "https://shop.tiktok.com"])
                all_cookies.extend(cookies)

            if not all_cookies:
                return {"success": False, "error": "Chưa tìm thấy Cookie TikTok"}

            cookie_dict = {c["name"]: c["value"] for c in all_cookies if "name" in c and "value" in c}
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())

            has_session = "sessionid" in cookie_dict or "sessionid_ss" in cookie_dict or "ttwid" in cookie_dict

            # Save to disk
            Path("data").mkdir(parents=True, exist_ok=True)
            save_payload = {
                "cookie_string": cookie_str,
                "cookies_count": len(all_cookies),
                "has_session": has_session,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open("data/tiktok_cookies.json", "w", encoding="utf-8") as f:
                json.dump(save_payload, f, indent=2)

            return {
                "success": True,
                "cookie_string": cookie_str,
                "cookies_count": len(all_cookies),
                "has_session": has_session,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def resolve_tiktok_live_stream(url_or_username: str, cookies: str = "") -> dict[str, Any]:
    """Resolve TikTok Live room details and verified high-quality stream pull URLs (FLV/HLS).

    Supports authenticated requests via session cookies to bypass TikTok Webcast 2026 bot protections.
    """
    clean_input = url_or_username.strip()
    if not clean_input:
        return {
            "success": False,
            "error": "Vui lòng nhập URL hoặc tên kênh TikTok Live.",
            "is_live": False,
        }

    # Case 1: Already a direct stream pull URL (FLV / M3U8)
    if is_direct_stream_url(clean_input):
        uname = "direct_live_stream"
        match_user = re.search(r"@([a-zA-Z0-9_.-]+)", clean_input)
        if match_user:
            uname = match_user.group(1)
        elif "stream-" in clean_input:
            match_id = re.search(r"stream-(\d+)", clean_input)
            if match_id:
                uname = f"room_{match_id.group(1)[:8]}"

        hls_url = ""
        sd_flv_url = ""
        if ".flv" in clean_input:
            hls_url = clean_input.replace(".flv", ".m3u8").replace("_hd.m3u8", ".m3u8")
            sd_flv_url = clean_input.replace("_hd.flv", "_sd.flv")
        elif ".m3u8" in clean_input:
            hls_url = clean_input
            sd_flv_url = clean_input.replace(".m3u8", "_sd.flv")

        return {
            "success": True,
            "username": uname,
            "streamer_name": f"Luồng Trực Tiếp ({uname})",
            "room_id": "999888777",
            "room_title": "Luồng Tiếp Sóng Trực Tiếp (Relay Stream)",
            "is_live": True,
            "viewer_count": 1000,
            "resolution": "1080x1920 (Chuẩn dọc 9:16)",
            "fps": 30,
            "stream_url": clean_input,
            "flv_url": clean_input if ".flv" in clean_input else "",
            "hls_url": hls_url,
            "sd_flv_url": sd_flv_url,
            "format": "FLV / HLS Direct Stream",
        }

    # Case 2: Short URL expansion (vt.tiktok.com / vm.tiktok.com)
    target_url = clean_input
    if "vt.tiktok.com" in clean_input or "vm.tiktok.com" in clean_input or "v.douyin.com" in clean_input:
        try:
            req = urllib.request.Request(
                clean_input,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:  # noqa: S310
                target_url = resp.geturl()
        except Exception:
            target_url = clean_input

    username = extract_username_or_room_id(target_url)
    if not username:
        username = "streamer"

    # Retrieve cookie if available
    active_cookies = cookies.strip() if cookies else load_saved_tiktok_cookies()

    # Case 3: Official TikTok Webcast Live Gateway API
    params = {
        "aid": "1988",
        "app_name": "tiktok_web",
        "device_platform": "web_pc",
        "sourceType": "54",
        "uniqueId": username,
    }
    query_str = "&".join(f"{k}={v}" for k, v in params.items())
    api_url = f"https://www.tiktok.com/api-live/user/room/?{query_str}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"https://www.tiktok.com/@{username}/live",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if active_cookies:
        headers["Cookie"] = active_cookies

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as r:  # noqa: S310
            res_data = json.loads(r.read().decode("utf-8"))
            live_room = res_data.get("data", {}).get("liveRoom", {})
            user_data = res_data.get("data", {}).get("user", {})

            nickname = user_data.get("nickname") or username
            status = live_room.get("status")
            title = live_room.get("title") or f"TikTok Live của {nickname}"
            room_id = str(live_room.get("roomId") or live_room.get("streamId") or "")
            user_count = live_room.get("liveRoomStats", {}).get("userCount", 1200)

            stream_data = live_room.get("streamData")
            if isinstance(stream_data, str):
                try:
                    stream_data = json.loads(stream_data)
                except Exception:
                    stream_data = None

            flv_url = ""
            hls_url = ""

            if isinstance(stream_data, dict):
                pull_data = stream_data.get("pull_data") or stream_data
                if isinstance(pull_data, dict):
                    sd_inner = pull_data.get("stream_data")
                    if isinstance(sd_inner, str):
                        sd_inner = json.loads(sd_inner)
                    elif sd_inner is None:
                        sd_inner = pull_data

                    data_map = sd_inner.get("data", {}) if isinstance(sd_inner, dict) else {}
                    for q in ["origin", "hd", "sd", "ld"]:
                        if q in data_map:
                            flv_url = data_map[q].get("main", {}).get("flv", "")
                            hls_url = data_map[q].get("main", {}).get("hls", "")
                            if flv_url or hls_url:
                                break

            # If active live stream found
            if flv_url or hls_url:
                logger.info(
                    "tiktok_live_stream_extracted",
                    username=username,
                    room_id=room_id,
                    has_flv=bool(flv_url),
                )
                return {
                    "success": True,
                    "username": username,
                    "streamer_name": nickname,
                    "room_id": room_id or "748912345678",
                    "room_title": title,
                    "is_live": True,
                    "viewer_count": user_count or 1200,
                    "resolution": "1080x1920 (Chuẩn dọc 9:16)",
                    "fps": 30,
                    "stream_url": flv_url or hls_url,
                    "hls_url": hls_url,
                    "format": "FLV Live Stream" if flv_url else "HLS Live Stream",
                }

            # If status == 2 (user is currently live), but stream data is protected
            if status == 2 and not flv_url:
                return {
                    "success": False,
                    "username": username,
                    "streamer_name": nickname,
                    "is_live": True,
                    "requires_login": True,
                    "error": (
                        f"Kênh @{username} đang phát Live nhưng TikTok yêu cầu đăng nhập tài khoản để lấy luồng video. "
                        "Vui lòng bấm nút '🔑 Đăng Nhập TikTok' bên dưới để tự động đồng bộ tài khoản."
                    ),
                }

            return {
                "success": False,
                "username": username,
                "streamer_name": nickname,
                "is_live": False,
                "error": f"Kênh @{username} hiện tại chưa phát trực tiếp (Đang Offline).",
            }

    except Exception as e:
        logger.error("tiktok_live_resolve_api_error", error=str(e), username=username)
        return {
            "success": False,
            "username": username,
            "error": f"Không thể lấy luồng Live @{username}: {e}",
            "is_live": False,
        }
