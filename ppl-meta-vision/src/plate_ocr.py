"""
License plate OCR helper.

Localizes a plate-like region in a vehicle crop (lower band heuristic) and runs
optional EasyOCR when installed. Returns null plate fields when OCR is unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_EASY_READER = None
_EASY_TRIED = False

# Alphanumeric plate-like token (locale-agnostic V1)
_PLATE_TOKEN_RE = re.compile(r"[A-Z0-9]{4,10}")


def _get_easyocr_reader():
    global _EASY_READER, _EASY_TRIED
    if _EASY_TRIED:
        return _EASY_READER
    _EASY_TRIED = True
    # Opt-in: EasyOCR can segfault on some hosts during model load.
    import os

    if os.getenv("PLATE_OCR_ENGINE", "").strip().lower() not in ("easyocr", "1", "true"):
        logger.info(
            "Plate OCR: EasyOCR disabled (set PLATE_OCR_ENGINE=easyocr to enable); "
            "returning heuristic ROI only"
        )
        _EASY_READER = None
        return None
    try:
        import easyocr  # type: ignore

        _EASY_READER = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("EasyOCR reader initialized for plate OCR")
    except Exception as exc:
        logger.info("EasyOCR unavailable for plate OCR (%s); plates will be null", exc)
        _EASY_READER = None
    return _EASY_READER


def _heuristic_plate_roi(crop: np.ndarray) -> Tuple[np.ndarray, List[float]]:
    """
    Take a lower-central band of the vehicle crop as plate candidate.
    Returns (roi_image, bbox_in_crop_coords).
    """
    h, w = crop.shape[:2]
    if h < 8 or w < 8:
        return crop, [0.0, 0.0, float(w), float(h)]
    y1 = int(h * 0.55)
    y2 = int(h * 0.95)
    x1 = int(w * 0.15)
    x2 = int(w * 0.85)
    y1, y2 = max(0, y1), min(h, max(y1 + 1, y2))
    x1, x2 = max(0, x1), min(w, max(x1 + 1, x2))
    roi = crop[y1:y2, x1:x2]
    return roi, [float(x1), float(y1), float(x2), float(y2)]


def _normalize_plate_text(raw: str) -> Optional[str]:
    if not raw:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if len(cleaned) < 4:
        return None
    m = _PLATE_TOKEN_RE.search(cleaned)
    return m.group(0) if m else cleaned[:10] if len(cleaned) >= 4 else None


def ocr_plate_on_vehicle_crop(
    crop_bgr: np.ndarray,
    *,
    conf_threshold: float = 0.3,
) -> Dict[str, Any]:
    """
    Detect+OCR plate text on a vehicle crop.

    Returns dict with plate_text, plate_confidence, plate_bbox (crop-relative),
    method. plate_text may be None.
    """
    empty = {
        "success": True,
        "plate_text": None,
        "plate_confidence": None,
        "plate_bbox": None,
        "method": "none",
    }
    if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
        return {**empty, "success": False, "error": "empty_crop"}

    roi, plate_bbox = _heuristic_plate_roi(crop_bgr)
    reader = _get_easyocr_reader()
    if reader is None:
        return {
            **empty,
            "plate_bbox": plate_bbox,
            "method": "heuristic_roi_no_ocr",
        }

    try:
        # EasyOCR expects RGB
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        results = reader.readtext(rgb)
        best_text: Optional[str] = None
        best_conf = 0.0
        best_box_local: Optional[List[float]] = None
        for item in results or []:
            if len(item) < 3:
                continue
            box, text, conf = item[0], item[1], float(item[2])
            if conf < conf_threshold:
                continue
            normalized = _normalize_plate_text(str(text))
            if not normalized:
                continue
            if conf > best_conf:
                best_conf = conf
                best_text = normalized
                try:
                    xs = [float(p[0]) for p in box]
                    ys = [float(p[1]) for p in box]
                    # Map from ROI-local to crop coords
                    ox, oy = plate_bbox[0], plate_bbox[1]
                    best_box_local = [
                        min(xs) + ox,
                        min(ys) + oy,
                        max(xs) + ox,
                        max(ys) + oy,
                    ]
                except Exception:
                    best_box_local = plate_bbox
        return {
            "success": True,
            "plate_text": best_text,
            "plate_confidence": round(best_conf, 4) if best_text else None,
            "plate_bbox": best_box_local or plate_bbox,
            "method": "easyocr_heuristic_roi",
        }
    except Exception as exc:
        logger.debug("plate OCR error: %s", exc)
        return {
            **empty,
            "plate_bbox": plate_bbox,
            "method": "ocr_error",
            "error": str(exc),
        }
