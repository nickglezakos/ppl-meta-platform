"""Licence feature lookup against Node cached Authority state."""

from __future__ import annotations

import logging

import httpx

from config import config

logger = logging.getLogger(__name__)

FEATURE_CATALOG = "eyenet_mv_models"
FEATURE_UPLOAD = "mv_models_upload"
FEATURE_CUSTOM = "mv_models_custom_capability"


def fetch_licence_features() -> list[str]:
    url = f"{config.NODE_SERVICE_URL}/licensing/authority/status"
    headers = {}
    if config.SERVICE_SECRET:
        headers["X-Service-Secret"] = config.SERVICE_SECRET
        headers["X-Service-Name"] = "ppl-meta-models"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            authority = payload.get("authority") or {}
            features = authority.get("licence_features") or authority.get(
                "cached_licence_features"
            )
            if isinstance(features, list):
                return [str(item) for item in features]
    except Exception as exc:
        logger.warning("licence feature lookup failed: %s", exc)
    return []


def has_feature(feature: str) -> bool:
    if not config.REQUIRE_LICENCE and config.ENVIRONMENT == "development":
        # Local boot without Authority still needs catalog + upload for Phase B smoke.
        if feature in (FEATURE_CATALOG, FEATURE_UPLOAD, FEATURE_CUSTOM):
            return True
    if config.ENVIRONMENT == "development" and feature in (
        FEATURE_CATALOG,
        FEATURE_UPLOAD,
        FEATURE_CUSTOM,
    ):
        features = fetch_licence_features()
        if FEATURE_CATALOG in features or not features:
            # Empty cache locally: allow catalog/upload/custom for Phase B.
            if not features:
                return True
            if feature == FEATURE_CATALOG:
                return FEATURE_CATALOG in features
            if feature == FEATURE_UPLOAD:
                return FEATURE_UPLOAD in features or FEATURE_CATALOG in features
            if feature == FEATURE_CUSTOM:
                return FEATURE_CUSTOM in features or FEATURE_CATALOG in features
    return feature in fetch_licence_features()
