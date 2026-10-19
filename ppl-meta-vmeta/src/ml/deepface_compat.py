"""DeepFace call helpers — stay compatible across DeepFace versions."""

from __future__ import annotations

import inspect
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from deepface import DeepFace

logger = logging.getLogger(__name__)

_WEIGHT_FILES = (
    "facenet512_weights.h5",
    "age_model_weights.h5",
    "gender_model_weights.h5",
)
_weights_paths_ready = False


def ensure_deepface_weight_paths() -> None:
    """
    Point DeepFace at the baked image weights.

    Build puts files in $DEEPFACE_HOME/weights (default /root/.deepface/weights).
    Some DeepFace builds also read $DEEPFACE_HOME/.deepface/weights and will
    re-download from GitHub into that nested folder if weights are missing.
    Symlink the nested names to the baked files and remove incomplete .part downloads.
    """
    global _weights_paths_ready
    if _weights_paths_ready:
        return

    home = Path(os.environ.get("DEEPFACE_HOME", "/root/.deepface"))
    primary = home / "weights"
    nested = home / ".deepface" / "weights"
    nested.mkdir(parents=True, exist_ok=True)

    for part in nested.glob("*.part"):
        try:
            part.unlink()
        except OSError as exc:
            logger.warning("Could not remove DeepFace partial download %s: %s", part, exc)

    for name in _WEIGHT_FILES:
        src = primary / name
        dst = nested / name
        if not src.is_file():
            continue
        try:
            if dst.is_symlink() or dst.is_file():
                if dst.resolve() == src.resolve():
                    continue
                dst.unlink()
            dst.symlink_to(src)
            logger.info("DeepFace weight link %s -> %s", dst, src)
        except OSError as exc:
            logger.warning("Could not link DeepFace weight %s: %s", name, exc)

    _weights_paths_ready = True


def _normalize_analyze_result(result: Any) -> List[Dict[str, Any]]:
    """Older DeepFace returns a dict; newer returns a list of dicts."""
    if result is None:
        return []
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    if isinstance(result, dict):
        # Some builds nest under "instance_1" / similar keys.
        if any(k in result for k in ("age", "gender", "dominant_gender", "emotion")):
            return [result]
        nested = [v for v in result.values() if isinstance(v, dict)]
        return nested or [result]
    return []


def deepface_analyze(
    img_path: Union[str, np.ndarray],
    actions: List[str],
    enforce_detection: bool = False,
    detector_backend: str = "opencv",
    models: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Call DeepFace.analyze across versions.

    - Newer DeepFace: supports `silent=`
    - Older DeepFace (this Lima image): uses `prog_bar=` instead
    """
    kwargs: Dict[str, Any] = {
        "img_path": img_path,
        "actions": actions,
        "enforce_detection": enforce_detection,
        "detector_backend": detector_backend,
    }
    if models:
        kwargs["models"] = models

    try:
        params = inspect.signature(DeepFace.analyze).parameters
    except (TypeError, ValueError):
        params = {}

    if "silent" in params:
        kwargs["silent"] = True
    elif "prog_bar" in params:
        kwargs["prog_bar"] = False

    result = DeepFace.analyze(**kwargs)
    return _normalize_analyze_result(result)


def deepface_build_model(model_name: str) -> Any:
    """
    Preload a DeepFace model (Age/Gender/…) with version-tolerant build_model.
    Newer DeepFace wants task='facial_attribute' for demography models.
    """
    ensure_deepface_weight_paths()
    try:
        params = inspect.signature(DeepFace.build_model).parameters
    except (TypeError, ValueError):
        params = {}

    if "task" in params:
        try:
            return DeepFace.build_model(model_name, task="facial_attribute")
        except Exception:
            return DeepFace.build_model(model_name)
    return DeepFace.build_model(model_name)


def warmup_age_gender_models() -> Dict[str, Any]:
    """Load Age + Gender weights into process memory (no image required)."""
    ensure_deepface_weight_paths()
    models: Dict[str, Any] = {}
    for key, name in (("age", "Age"), ("gender", "Gender")):
        models[key] = deepface_build_model(name)
    return models

