"""
Enrich ppl/vprofile match payloads with Presence People Profile (PPP) display names.

PPP name is the product source of truth for a real person's display name when a
group member is linked. Action templates / audit logs historically used only the
MVR plain ``existing_member_name`` field; this module fills that gap at match time
so every action type (log/alert/email/…) stays consistent.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

from src.config import get_config

logger = logging.getLogger(__name__)


def _presence_base_url() -> str:
    return os.getenv(
        "PRESENCE_SERVICE_URL",
        getattr(get_config(), "PRESENCE_SERVICE_URL", "http://localhost:8011"),
    ).rstrip("/")


def display_name_from_best_match(best_match: Optional[Dict[str, Any]]) -> str:
    """Prefer People Profile name, then MVR plain name."""
    if not isinstance(best_match, dict):
        return ""
    people_name = (best_match.get("people_name") or "").strip()
    if people_name:
        return people_name
    return (best_match.get("existing_member_name") or "").strip()


async def lookup_people_profile_by_member(
    individual_id: Optional[str],
    *,
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """
    GET /api/v1/presence/people-profiles/lookup?individual_id=...

    Returns the PPP dict (``name``, ``ppp_uuid``, …) or None.
    """
    member_id = (individual_id or "").strip()
    if not member_id:
        return None

    # Prefer the internal (no end-user JWT) match-pipeline path; fall back to
    # the authenticated route for older presence builds.
    base = _presence_base_url()
    urls = (
        f"{base}/api/v1/presence/internal/people-profiles/lookup",
        f"{base}/api/v1/presence/people-profiles/lookup",
    )
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        last_status = None
        last_body = ""
        for idx, url in enumerate(urls):
            response = await http.get(url, params={"individual_id": member_id})
            last_status = response.status_code
            last_body = response.text[:160]
            if response.status_code == 401 and idx == 0:
                # Unexpected on internal path — try authenticated path next.
                continue
            if response.status_code == 401:
                logger.warning(
                    "PPP lookup unauthorized for %s (presence requires auth; "
                    "deploy presence with /internal/people-profiles/lookup)",
                    member_id[:12],
                )
                return None
            if response.status_code != 200:
                continue
            payload = response.json() or {}
            data = payload.get("data") if isinstance(payload, dict) else None
            if data is None:
                return None
            if not isinstance(data, dict):
                return None
            if (data.get("status") or "active") == "inactive":
                return None
            return data
        logger.warning(
            "PPP lookup failed for %s: %s %s",
            member_id[:12],
            last_status,
            last_body,
        )
        return None
    except Exception as exc:
        logger.warning("PPP lookup error for %s: %s", member_id[:12], exc)
        return None
    finally:
        if owns_client:
            await http.aclose()


async def enrich_best_match_with_people_profile(
    best_match: Optional[Dict[str, Any]],
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[Dict[str, Any]]:
    """
    Mutate ``best_match`` in place:

    - ``people_name`` / ``matched_ppp_uuid`` when a PPP link exists
    - Prefer PPP name for ``existing_member_name`` (keeps ``{matched_member_name}``
      and legacy audit fields working); preserve MVR plain name as ``mvr_member_name``
    """
    if not isinstance(best_match, dict):
        return best_match

    member_uuid = (
        best_match.get("matched_member_uuid")
        or best_match.get("existing_member_id")
        or best_match.get("member_uuid")
    )
    if not member_uuid:
        return best_match

    # Already enriched in this cycle
    if best_match.get("matched_ppp_uuid") and best_match.get("people_name"):
        return best_match

    profile = await lookup_people_profile_by_member(str(member_uuid), client=client)
    if not profile:
        return best_match

    people_name = (profile.get("name") or "").strip()
    ppp_uuid = profile.get("ppp_uuid")
    if not people_name:
        return best_match

    mvr_name = (best_match.get("existing_member_name") or "").strip()
    if mvr_name and "mvr_member_name" not in best_match:
        best_match["mvr_member_name"] = mvr_name

    best_match["people_name"] = people_name
    if ppp_uuid:
        best_match["matched_ppp_uuid"] = ppp_uuid
    # Prefer PPP for all legacy consumers of existing_member_name / matched_member_name
    best_match["existing_member_name"] = people_name
    logger.info(
        "  👤 PPP display name for member %s → %s (ppp=%s)",
        str(member_uuid)[:12],
        people_name,
        str(ppp_uuid)[:12] if ppp_uuid else "—",
    )
    return best_match


async def enrich_match_info_with_people_profiles(
    match_info: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Enrich ``best_match`` and any ``top_k_results`` / ``top_candidates`` lists."""
    if not isinstance(match_info, dict):
        return match_info

    mode = match_info.get("mode")
    if mode not in ("ppl_match", "vprofile_match") and not match_info.get("matched"):
        # Still allow when best_match present (some paths omit mode)
        if not isinstance(match_info.get("best_match"), dict):
            return match_info

    async with httpx.AsyncClient(timeout=2.0) as client:
        best = match_info.get("best_match")
        if isinstance(best, dict):
            await enrich_best_match_with_people_profile(best, client=client)

        for key in ("top_k_results", "top_candidates"):
            rows = match_info.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict):
                    await enrich_best_match_with_people_profile(row, client=client)

    return match_info
