"""ONNX YOLO detect helpers (YOLOv8-style outputs) via onnxruntime."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_sessions: dict[str, Any] = {}


def _ort():
    try:
        import onnxruntime as ort

        return ort
    except ImportError:
        logger.warning("onnxruntime not installed")
        return None


def load_session(path: str):
    ort = _ort()
    if ort is None:
        return None
    key = str(Path(path).resolve())
    if key in _sessions:
        return _sessions[key]
    if not Path(path).is_file():
        logger.warning("ONNX file missing: %s", path)
        return None
    try:
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        _sessions[key] = sess
        return sess
    except Exception as exc:
        logger.warning("Failed to load ONNX %s: %s", path, exc)
        return None


def unload_session(path: str) -> None:
    key = str(Path(path).resolve())
    _sessions.pop(key, None)


def _letterbox(image: np.ndarray, imgsz: int = 640):
    h, w = image.shape[:2]
    scale = min(imgsz / h, imgsz / w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)
    top = (imgsz - nh) // 2
    left = (imgsz - nw) // 2
    canvas[top : top + nh, left : left + nw] = resized
    return canvas, scale, left, top


def _nms(boxes: list[list[float]], scores: list[float], iou_thresh: float = 0.45):
    if not boxes:
        return []
    idxs = cv2.dnn.NMSBoxes(
        [[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in boxes],
        scores,
        score_threshold=0.01,
        nms_threshold=iou_thresh,
    )
    if idxs is None or len(idxs) == 0:
        return []
    flat = np.array(idxs).reshape(-1).tolist()
    return [int(i) for i in flat]


def detect_yolo_onnx(
    image: np.ndarray,
    *,
    model_path: str,
    conf: float = 0.25,
    imgsz: int = 640,
    class_ids: list[int] | None = None,
    class_labels: dict[int, str] | None = None,
) -> dict:
    """
    Run YOLOv8-style ONNX detection.

    Returns {success, detections:[{bbox, confidence, class_id, class_label}], method}.
    """
    sess = load_session(model_path)
    if sess is None:
        return {"success": False, "error": "onnx_session_unavailable", "detections": []}

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image
    canvas, scale, pad_x, pad_y = _letterbox(rgb, imgsz)
    blob = canvas.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))[None, ...]

    input_name = sess.get_inputs()[0].name
    try:
        outputs = sess.run(None, {input_name: blob})
    except Exception as exc:
        return {"success": False, "error": str(exc), "detections": []}

    pred = outputs[0]
    # YOLOv8 export shapes: (1, 84, N) or (1, N, 84) or (1, 5+nc, N)
    if pred.ndim == 3:
        pred = pred[0]
    if pred.shape[0] < pred.shape[1] and pred.shape[0] <= 512:
        pred = pred.T

    boxes: list[list[float]] = []
    scores: list[float] = []
    classes: list[int] = []
    h0, w0 = image.shape[:2]

    for row in pred:
        if row.shape[0] < 5:
            continue
        # xywh + class scores
        cx, cy, bw, bh = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        class_scores = row[4:]
        if class_scores.size == 0:
            continue
        cls_id = int(np.argmax(class_scores))
        score = float(class_scores[cls_id])
        if score < conf:
            continue
        if class_ids is not None and cls_id not in class_ids:
            continue
        x1 = (cx - bw / 2 - pad_x) / scale
        y1 = (cy - bh / 2 - pad_y) / scale
        x2 = (cx + bw / 2 - pad_x) / scale
        y2 = (cy + bh / 2 - pad_y) / scale
        x1 = max(0.0, min(float(w0 - 1), x1))
        y1 = max(0.0, min(float(h0 - 1), y1))
        x2 = max(0.0, min(float(w0 - 1), x2))
        y2 = max(0.0, min(float(h0 - 1), y2))
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append([x1, y1, x2, y2])
        scores.append(score)
        classes.append(cls_id)

    keep = _nms(boxes, scores)
    labels = class_labels or {}
    detections = []
    for i in keep:
        cid = classes[i]
        detections.append(
            {
                "bbox": [int(boxes[i][0]), int(boxes[i][1]), int(boxes[i][2]), int(boxes[i][3])],
                "confidence": float(scores[i]),
                "class_id": cid,
                "class_label": labels.get(cid, str(cid)),
                "method": "onnx_yolo",
            }
        )

    return {
        "success": True,
        "detections": detections,
        "method": "onnx_yolo",
        "faces_detected": len(detections),
    }


# COCO-80 class names (YOLOv8 detect index order)
COCO80_LABELS: dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush",
}

# Default left-object / luggage-related COCO ids
DEFAULT_LEFT_OBJECT_CLASS_IDS = [24, 26, 28, 39]


# COCO-17 keypoint names (YOLOv8-pose)
COCO17_KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


def detect_yolo_pose_onnx(
    image: np.ndarray,
    *,
    model_path: str,
    conf: float = 0.25,
    imgsz: int = 640,
    kpt_conf: float = 0.3,
) -> dict:
    """
    Run YOLOv8-pose ONNX.

    Expected output channels: 4 (xywh) + 1 (obj) + 17*3 (x,y,conf) = 56,
    or 4 + nc + 51 when nc class scores precede keypoints.

    Returns detections with bbox, confidence, keypoints[{name,x,y,confidence}].
    """
    sess = load_session(model_path)
    if sess is None:
        return {"success": False, "error": "onnx_session_unavailable", "detections": []}

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image
    canvas, scale, pad_x, pad_y = _letterbox(rgb, imgsz)
    blob = canvas.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))[None, ...]

    input_name = sess.get_inputs()[0].name
    try:
        outputs = sess.run(None, {input_name: blob})
    except Exception as exc:
        return {"success": False, "error": str(exc), "detections": []}

    pred = outputs[0]
    if pred.ndim == 3:
        pred = pred[0]
    if pred.shape[0] < pred.shape[1] and pred.shape[0] <= 512:
        pred = pred.T

    boxes: list[list[float]] = []
    scores: list[float] = []
    keypoints_list: list[list[dict]] = []
    h0, w0 = image.shape[:2]

    for row in pred:
        dim = int(row.shape[0])
        if dim < 5:
            continue
        cx, cy, bw, bh = float(row[0]), float(row[1]), float(row[2]), float(row[3])

        # Pose layouts: 56 = xywh + obj + 51 kpts; or 4+nc+51
        if dim >= 56:
            # Prefer single-object score at index 4 when remaining fits 17*3
            if (dim - 5) % 3 == 0 and (dim - 5) // 3 >= 17:
                score = float(row[4])
                kpt_offset = 5
            else:
                # class scores then keypoints
                n_kpt_vals = 17 * 3
                class_end = dim - n_kpt_vals
                if class_end <= 4:
                    continue
                class_scores = row[4:class_end]
                cls_id = int(np.argmax(class_scores))
                score = float(class_scores[cls_id])
                kpt_offset = class_end
        else:
            continue

        if score < conf:
            continue

        x1 = (cx - bw / 2 - pad_x) / scale
        y1 = (cy - bh / 2 - pad_y) / scale
        x2 = (cx + bw / 2 - pad_x) / scale
        y2 = (cy + bh / 2 - pad_y) / scale
        x1 = max(0.0, min(float(w0 - 1), x1))
        y1 = max(0.0, min(float(h0 - 1), y1))
        x2 = max(0.0, min(float(w0 - 1), x2))
        y2 = max(0.0, min(float(h0 - 1), y2))
        if x2 <= x1 or y2 <= y1:
            continue

        kpts = []
        for ki, name in enumerate(COCO17_KEYPOINT_NAMES):
            base = kpt_offset + ki * 3
            if base + 2 >= dim:
                break
            kx = (float(row[base]) - pad_x) / scale
            ky = (float(row[base + 1]) - pad_y) / scale
            kc = float(row[base + 2])
            kx = max(0.0, min(float(w0 - 1), kx))
            ky = max(0.0, min(float(h0 - 1), ky))
            kpts.append(
                {
                    "name": name,
                    "x": float(kx),
                    "y": float(ky),
                    "confidence": float(kc),
                    "visible": bool(kc >= kpt_conf),
                }
            )

        boxes.append([x1, y1, x2, y2])
        scores.append(score)
        keypoints_list.append(kpts)

    keep = _nms(boxes, scores)
    detections = []
    for i in keep:
        detections.append(
            {
                "bbox": [
                    int(boxes[i][0]),
                    int(boxes[i][1]),
                    int(boxes[i][2]),
                    int(boxes[i][3]),
                ],
                "confidence": float(scores[i]),
                "class_id": 0,
                "class_label": "person",
                "keypoints": keypoints_list[i],
                "method": "onnx_yolo_pose",
            }
        )

    return {
        "success": True,
        "detections": detections,
        "method": "onnx_yolo_pose",
    }


def estimate_posture_from_keypoints(
    keypoints: list[dict] | None,
    bbox: list[float] | None = None,
    *,
    min_visible: int = 4,
) -> dict:
    """
    Derive upright / horizontal / uncertain from COCO-17 keypoints.
    Falls back to bbox aspect ratio when keypoints are insufficient.
    """
    kpts = {k["name"]: k for k in (keypoints or []) if isinstance(k, dict) and "name" in k}
    shoulders = []
    hips = []
    for name in ("left_shoulder", "right_shoulder"):
        k = kpts.get(name)
        if k and k.get("visible"):
            shoulders.append((float(k["x"]), float(k["y"]), float(k.get("confidence") or 0)))
    for name in ("left_hip", "right_hip"):
        k = kpts.get(name)
        if k and k.get("visible"):
            hips.append((float(k["x"]), float(k["y"]), float(k.get("confidence") or 0)))

    visible_count = sum(1 for k in (keypoints or []) if k.get("visible"))
    if len(shoulders) >= 1 and len(hips) >= 1 and visible_count >= min_visible:
        sx = sum(p[0] for p in shoulders) / len(shoulders)
        sy = sum(p[1] for p in shoulders) / len(shoulders)
        hx = sum(p[0] for p in hips) / len(hips)
        hy = sum(p[1] for p in hips) / len(hips)
        dx = hx - sx
        dy = hy - sy
        import math

        angle_from_vertical = abs(math.degrees(math.atan2(dx, dy)))
        # dy>0 means hips below shoulders in image coords
        conf = min(1.0, (visible_count / 17.0) * 0.9 + 0.1)
        if angle_from_vertical <= 35:
            return {"posture": "upright", "posture_confidence": conf, "torso_angle_deg": angle_from_vertical}
        if angle_from_vertical >= 55:
            return {"posture": "horizontal", "posture_confidence": conf, "torso_angle_deg": angle_from_vertical}
        return {"posture": "uncertain", "posture_confidence": conf * 0.5, "torso_angle_deg": angle_from_vertical}

    # Bbox aspect fallback (weak)
    if bbox and len(bbox) >= 4:
        w = max(1.0, float(bbox[2]) - float(bbox[0]))
        h = max(1.0, float(bbox[3]) - float(bbox[1]))
        ratio = h / w
        if ratio >= 1.2:
            return {"posture": "upright", "posture_confidence": 0.35, "torso_angle_deg": None}
        if ratio <= 0.75:
            return {"posture": "horizontal", "posture_confidence": 0.35, "torso_angle_deg": None}
    return {"posture": "uncertain", "posture_confidence": 0.0, "torso_angle_deg": None}


def estimate_height_px(keypoints: list[dict] | None, bbox: list[float] | None = None) -> dict:
    """Relative height in pixels (not meters). Prefer head–ankle span."""
    kpts = {k["name"]: k for k in (keypoints or []) if isinstance(k, dict) and "name" in k}
    head_ys = []
    for name in ("nose", "left_eye", "right_eye", "left_ear", "right_ear"):
        k = kpts.get(name)
        if k and k.get("visible"):
            head_ys.append(float(k["y"]))
    ankle_ys = []
    for name in ("left_ankle", "right_ankle"):
        k = kpts.get(name)
        if k and k.get("visible"):
            ankle_ys.append(float(k["y"]))
    if head_ys and ankle_ys:
        span = abs(max(ankle_ys) - min(head_ys))
        return {"height_px": float(span), "height_relative": float(span), "height_m": None, "method": "head_ankle"}
    if bbox and len(bbox) >= 4:
        span = abs(float(bbox[3]) - float(bbox[1]))
        return {"height_px": float(span), "height_relative": float(span), "height_m": None, "method": "bbox"}
    return {"height_px": None, "height_relative": None, "height_m": None, "method": None}


def estimate_fallen(*_args, **_kwargs) -> dict:
    """
    PLACEHOLDER — not implemented in V1.

    Posture horizontal is not certified fallen / life-safety.
    Future: temporal motion + pose classifier for industrial/ship scenes.
    """
    # TODO: implement fallen classifier (temporal hip/shoulder velocity + pose)
    return {"fallen": "unknown", "fallen_confidence": 0.0, "method": "placeholder"}


def estimate_dominant_colors(
    image=None,
    bbox: list[float] | None = None,
    keypoints: list[dict] | None = None,
    *,
    k: int = 3,
    max_colors: int = 3,
    inset: float = 0.12,
) -> dict:
    """
    Estimate dominant clothing colors from a person crop.

    Prefers a torso band from pose keypoints when shoulders+hips are visible;
    otherwise uses an inset person bbox. Returns top hex colors with fractions.
    """
    if image is None or bbox is None or len(bbox) < 4:
        return {"dominant_colors": None, "method": "hsv_kmeans_bbox"}

    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"dominant_colors": None, "method": "hsv_kmeans_bbox"}

    h_img, w_img = image.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]

    # Prefer torso rectangle from shoulders → hips when available
    kpts = {
        kpt["name"]: kpt
        for kpt in (keypoints or [])
        if isinstance(kpt, dict) and kpt.get("name") and kpt.get("visible")
    }
    shoulders = [
        kpts[n]
        for n in ("left_shoulder", "right_shoulder")
        if n in kpts
    ]
    hips = [kpts[n] for n in ("left_hip", "right_hip") if n in kpts]
    if shoulders and hips:
        xs = [float(p["x"]) for p in shoulders + hips]
        ys = [float(p["y"]) for p in shoulders + hips]
        pad_x = max(8.0, 0.15 * (max(xs) - min(xs) + 1))
        pad_y = max(8.0, 0.10 * (max(ys) - min(ys) + 1))
        x1, x2 = min(xs) - pad_x, max(xs) + pad_x
        y1, y2 = min(ys) - pad_y, max(ys) + pad_y
    else:
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        x1 += bw * inset
        x2 -= bw * inset
        y1 += bh * inset
        y2 -= bh * inset

    ix1 = int(max(0, min(w_img - 1, x1)))
    iy1 = int(max(0, min(h_img - 1, y1)))
    ix2 = int(max(0, min(w_img, x2)))
    iy2 = int(max(0, min(h_img, y2)))
    if ix2 - ix1 < 4 or iy2 - iy1 < 4:
        return {"dominant_colors": None, "method": "hsv_kmeans_bbox"}

    crop = image[iy1:iy2, ix1:ix2]
    if crop.size == 0:
        return {"dominant_colors": None, "method": "hsv_kmeans_bbox"}

    # Downsample for speed
    max_side = 96
    ch, cw = crop.shape[:2]
    scale = min(1.0, max_side / float(max(ch, cw)))
    if scale < 1.0:
        crop = cv2.resize(
            crop,
            (max(1, int(cw * scale)), max(1, int(ch * scale))),
            interpolation=cv2.INTER_AREA,
        )

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    pixels = hsv.reshape(-1, 3).astype(np.float32)
    # Drop near-gray / extreme value (background, shadows, glare)
    sat = pixels[:, 1]
    val = pixels[:, 2]
    mask = (sat >= 30) & (val >= 40) & (val <= 245)
    filtered = pixels[mask]
    if len(filtered) < 20:
        filtered = pixels
    if len(filtered) < 8:
        return {"dominant_colors": None, "method": "hsv_kmeans_bbox"}

    # Cap samples for k-means
    if len(filtered) > 2000:
        rng = np.random.default_rng(0)
        idx = rng.choice(len(filtered), size=2000, replace=False)
        filtered = filtered[idx]

    k_eff = int(min(k, max(1, len(filtered) // 10)))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _compactness, labels, centers = cv2.kmeans(
        filtered, k_eff, None, criteria, 3, cv2.KMEANS_PP_CENTERS
    )
    counts = np.bincount(labels.flatten(), minlength=k_eff).astype(np.float64)
    total = float(counts.sum()) or 1.0
    order = np.argsort(-counts)

    colors: list[dict] = []
    for i in order[:max_colors]:
        fraction = float(counts[i] / total)
        if fraction < 0.05 and colors:
            continue
        h, s, v = [float(x) for x in centers[i]]
        bgr = cv2.cvtColor(
            np.uint8([[[h, s, v]]]), cv2.COLOR_HSV2BGR
        )[0, 0]
        b, g, r = [int(x) for x in bgr]
        colors.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "fraction": round(fraction, 3),
            }
        )

    return {
        "dominant_colors": colors or None,
        "method": "hsv_kmeans_torso" if shoulders and hips else "hsv_kmeans_bbox",
    }

