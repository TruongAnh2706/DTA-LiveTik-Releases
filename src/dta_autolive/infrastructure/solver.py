import cv2
import numpy as np


def find_captcha_modal(full_app_img):
    """
    Tự động quét và khoét Khung Captcha Modal bằng thuật toán Phân đoạn màu Trắng (White Color Segmentation).
    Trả về: (captcha_modal_img, (modal_x, modal_y, modal_w, modal_h)) hoặc (None, None)
    """
    if full_app_img is None or full_app_img.size == 0:
        return None, None

    try:
        h, w, _ = full_app_img.shape

        lower_white = np.array([225, 225, 225], dtype=np.uint8)
        upper_white = np.array([255, 255, 255], dtype=np.uint8)
        white_mask = cv2.inRange(full_app_img, lower_white, upper_white)

        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_modals = []
        if contours:
            for c in contours:
                bx, by, bw, bh = cv2.boundingRect(c)
                if 180 <= bw <= 480 and 140 <= bh <= 420:
                    aspect_ratio = bw / float(bh)
                    if 1.0 <= aspect_ratio <= 1.6:
                        center_dist = abs((bx + bw // 2) - w // 2) + abs((by + bh // 2) - h // 2)
                        valid_modals.append((center_dist, bx, by, bw, bh))

        if valid_modals:
            valid_modals.sort(key=lambda x: x[0])
            _, mx, my, mw, mh = valid_modals[0]
            captcha_modal_img = full_app_img[my : my + mh, mx : mx + mw]
            return captcha_modal_img, (mx, my, mw, mh)

        lower_white2 = np.array([200, 200, 200], dtype=np.uint8)
        white_mask2 = cv2.inRange(full_app_img, lower_white2, upper_white)
        contours2, _ = cv2.findContours(white_mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours2:
            for c in contours2:
                bx, by, bw, bh = cv2.boundingRect(c)
                if 170 <= bw <= 520 and 130 <= bh <= 440:
                    aspect_ratio = bw / float(bh)
                    if 0.95 <= aspect_ratio <= 1.65:
                        center_dist = abs((bx + bw // 2) - w // 2) + abs((by + bh // 2) - h // 2)
                        valid_modals.append((center_dist, bx, by, bw, bh))

        if valid_modals:
            valid_modals.sort(key=lambda x: x[0])
            _, mx, my, mw, mh = valid_modals[0]
            captcha_modal_img = full_app_img[my : my + mh, mx : mx + mw]
            return captcha_modal_img, (mx, my, mw, mh)

        return None, None
    except Exception:
        return None, None


def is_captcha_visible(full_app_img):
    """
    Kiểm tra xem Captcha Modal có đang xuất hiện trên màn hình hay không.
    """
    modal_img, modal_rect = find_captcha_modal(full_app_img)
    return modal_img is not None


def extract_puzzle_piece(photo_canvas):
    """
    FIX 1: STRICT CONTOUR FILTERING FOR PUZZLE PIECE (FIX GIANT CYAN BOX)
    Lọc nghiêm ngặt kích thước mảnh ghép từ 30x30px đến 60x60px. Nếu thất bại dùng Fallback chuẩn 42x42px.
    """
    p_h, p_w, _ = photo_canvas.shape
    # Restrict search zone to the far-left 32% of the canvas
    left_zone = photo_canvas[:, : int(p_w * 0.32)]

    gray = cv2.cvtColor(left_zone, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 100, 200)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    valid_pieces = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = float(w) / h if h > 0 else 0

        # STRICT TikTok Piece Size Filters (Adjusted for ~280px modal)
        if 30 <= w <= 60 and 30 <= h <= 60 and 0.7 <= aspect_ratio <= 1.3:
            valid_pieces.append((x, y, w, h))

    if valid_pieces:
        # Pick the piece closest to the vertical center
        valid_pieces.sort(key=lambda b: abs((b[1] + b[3] / 2) - (p_h / 2)))
        return valid_pieces[0]

    # FALLBACK: If contour fails, use fixed geometric crop for TikTok's default piece slot
    fallback_w, fallback_h = 42, 42
    fallback_x = 12
    fallback_y = int((p_h - fallback_h) / 2)
    return (fallback_x, fallback_y, fallback_w, fallback_h)


def find_target_hole_canny(photo_canvas, piece_bbox):
    """
    FIX 2: CANNY EDGE TEMPLATE MATCHING FOR TARGET HOLE (FIX BLUE SKY BOX)
    Match chính xác viền SHAPE BORDER bằng Canny Edges thay vì match RGB màu sắc.
    """
    px, py, pw, ph = piece_bbox
    p_h, p_w, _ = photo_canvas.shape

    # 1. Extract Piece Template (Canny Edges)
    piece_crop = photo_canvas[py : py + ph, px : px + pw]
    piece_gray = cv2.cvtColor(piece_crop, cv2.COLOR_BGR2GRAY)
    piece_edges = cv2.Canny(piece_gray, 50, 150)

    # 2. Isolate Right Search Zone (75% right side of photo)
    search_min_x = int(p_w * 0.25)
    search_zone = photo_canvas[:, search_min_x:]
    search_gray = cv2.cvtColor(search_zone, cv2.COLOR_BGR2GRAY)
    search_edges = cv2.Canny(search_gray, 50, 150)

    # 3. Perform Match on Edge Maps
    if (
        search_edges.shape[1] >= piece_edges.shape[1]
        and search_edges.shape[0] >= piece_edges.shape[0]
        and piece_edges.size > 0
    ):
        result = cv2.matchTemplate(search_edges, piece_edges, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # 4. Calculate Absolute Hole Position inside Photo Canvas
        hole_x = search_min_x + max_loc[0]
        hole_y = max_loc[1]
    else:
        hole_x = int(p_w * 0.58)
        hole_y = py

    drag_distance_x = hole_x - px
    return drag_distance_x, (hole_x, hole_y, pw, ph)


def get_slider_arrow_local_coords(modal_w, modal_h):
    """
    FIX 2: HARDCODE RELATIVE ANCHOR FOR SLIDER ARROW BUTTON (->)
    Calculates the exact center of the white circular slider arrow button (->)
    inside the Captcha modal card.
    Arrow button center is ALWAYS 10% from modal left edge, 88% from modal top.
    """
    slider_local_x = int(modal_w * 0.10)  # ~28px on a 281px modal
    slider_local_y = int(modal_h * 0.88)  # ~248px on a 283px modal
    return slider_local_x, slider_local_y


def solve_puzzle_split_zone(modal_img, draw_annotations=True):
    """
    Tích hợp Động cơ AI Canny Edge Precision V2:
    - Trích xuất Mảnh Ghép chuẩn (30x30px - 60x60px) loại bỏ hoàn toàn ô Cyan siêu to.
    - Canny Edge Template Matching cho Khe Khuyết loại bỏ hoàn toàn ô Blue trên bầu trời.
    - Anchor chuẩn xác Nút Trượt Slider ở rel_x ≈ 28px (~10% modal_w).
    """
    if modal_img is None or modal_img.size == 0:
        return None

    try:
        annotated = modal_img.copy()
        modal_h, modal_w, _ = modal_img.shape

        # 1. Crop Photo Canvas (Upper 72% height, excluding header & slider)
        y_top = int(modal_h * 0.12)
        y_bottom = int(modal_h * 0.75)
        photo_canvas = modal_img[y_top:y_bottom, :]

        # 2. Extract Puzzle Piece (Strict contour filter)
        piece_bbox = extract_puzzle_piece(photo_canvas)
        px, py, pw, ph = piece_bbox

        # 3. Find Target Hole via Canny Edges
        drag_offset_x, hole_bbox = find_target_hole_canny(photo_canvas, piece_bbox)
        hole_x, hole_y, hw, hh = hole_bbox

        # 4. Anchor Slider Arrow Button Relative Coords
        slider_local_x, slider_local_y = get_slider_arrow_local_coords(modal_w, modal_h)

        if draw_annotations:
            # - Ô VÀNG (Yellow Box khít khịt Mảnh Ghép ~42x42px): BGR (0, 255, 255)
            cv2.rectangle(
                annotated,
                (int(px), int(y_top + py)),
                (int(px + pw), int(y_top + py + ph)),
                (0, 255, 255),
                2,
            )
            cv2.putText(
                annotated,
                "Piece",
                (int(px), int(max(12, y_top + py - 4))),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 255),
                1,
            )

            # - Ô ĐỎ (Red Box khít khịt Khe Khuyết Shadow Hole): BGR (0, 0, 255)
            cv2.rectangle(
                annotated,
                (int(hole_x), int(y_top + py)),
                (int(hole_x + pw), int(y_top + py + ph)),
                (0, 0, 255),
                2,
            )
            cv2.putText(
                annotated,
                "Target",
                (int(hole_x), int(max(12, y_top + py - 4))),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )

            # - Mũi tên xanh & Điểm tâm Nút Slider chuẩn rel_x ≈ 28px
            cv2.line(
                annotated,
                (int(px + pw // 2), int(slider_local_y)),
                (int(hole_x + pw // 2), int(slider_local_y)),
                (0, 255, 0),
                2,
            )
            cv2.circle(annotated, (int(slider_local_x), int(slider_local_y)), 6, (0, 255, 0), -1)

        return {
            "drag_offset_x": int(max(30, drag_offset_x)),
            "piece_x": px,
            "piece_y": y_top + py,
            "piece_w": pw,
            "piece_h": ph,
            "hole_target_x": hole_x,
            "slider_local_x": slider_local_x,
            "slider_local_y": slider_local_y,
            "annotated_modal": annotated,
        }

    except Exception:
        return None
