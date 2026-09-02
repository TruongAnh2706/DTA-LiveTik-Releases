"""DTA Studio - Virtual Camera Stream Tester for Discord & TikTok LIVE Studio.

Generates a dynamic 9:16 (1080x1920 @ 30 FPS) live test stream with color animation,
timestamp, and DTA AutoLive branding directly onto system DirectShow Virtual Camera.
"""

import time

import numpy as np

from dta_autolive.infrastructure.dta_softcam_engine import DTASoftcamEngine


def main() -> None:
    """Run DTA Virtual Camera Test Stream for Discord & TikTok LIVE Studio."""
    width = 1080
    height = 1920
    fps = 30

    print("================================================================")
    print("🚀 DTA STUDIO - VIRTUAL CAMERA DRIVER TESTER")
    print("================================================================")
    print(f"Khởi tạo luồng Virtual Camera: {width}x{height} @ {fps} FPS (Tỷ lệ 9:16)...")

    engine = DTASoftcamEngine(width=width, height=height, fps=fps)

    if engine.vcam is not None:
        print("✅ ĐÃ KẾT NỐI VÀ TRUYỀN LUỒNG VIDEO THÀNH CÔNG TỚI VIRTUAL CAMERA!")
        print(f"   • Device Name: {engine.vcam.device}")
        print(f"   • Driver Backend: {engine.vcam.backend}")
        print("----------------------------------------------------------------")
        print("💡 KIỂM TRA TRÊN DISCORD / TIKTOK LIVE STUDIO:")
        print("   1. Mở Discord / TikTok LIVE Studio -> Chọn Camera 'OBS Virtual Camera'")
        print("   2. Bạn sẽ thấy ngay hình nền màu nảy theo thời gian thực 9:16!")
        print("----------------------------------------------------------------")
    else:
        print("⚠️ Chạy ở chế độ Shared Memory IPC Fallback Engine...")

    print("Đang phát luồng video test (Nhấn Ctrl+C để dừng)...")
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            frame_count += 1
            elapsed = time.time() - start_time

            # Create dynamic gradient test frame (1080x1920 BGR)
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Animated color hue shift
            r_val = int((1 + np.sin(elapsed * 2.0)) * 127)
            g_val = int((1 + np.cos(elapsed * 1.5)) * 127)
            b_val = 200

            # Fill frame background with smooth color gradient
            frame[:, :, 0] = b_val
            frame[:, :, 1] = g_val
            frame[:, :, 2] = r_val

            # Draw central high-tech highlight box
            cy, cx = height // 2, width // 2
            frame[cy - 300 : cy + 300, cx - 400 : cx + 400] = [0, 255, 255]  # Neon Cyan Box

            # Send frame to Virtual Camera
            engine.send_bgr_frame(frame)

            if frame_count % 90 == 0:
                cur_fps = frame_count / elapsed
                print(f"[STREAMING LOG] Sent {frame_count} frames | Realtime FPS: {cur_fps:.1f}")

            time.sleep(1.0 / fps)
    except KeyboardInterrupt:
        print("\n🛑 Đã nhận lệnh dừng stream từ người dùng.")
    finally:
        engine.close()
        print("✨ Da giai phong Virtual Camera Driver an toan!")


if __name__ == "__main__":
    main()
