"""HubSpot CRM client for Presence contact import and grant posting."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE = "https://api.hubapi.com"

PRESENCE_CONTACT_PROPERTIES = (
    {
        "name": "last_presence_at",
        "label": "Last Presence At",
        "type": "datetime",
        "fieldType": "date",
        "groupName": "contactinformation",
        "description": "Timestamp of the most recent EyeNet Presence grant",
    },
    {
        "name": "last_presence_type",
        "label": "Last Presence Type",
        "type": "string",
        "fieldType": "text",
        "groupName": "contactinformation",
        "description": "Grant type of the most recent EyeNet Presence grant",
    },
    {
        "name": "last_presence_session_id",
        "label": "Last Presence Session Id",
        "type": "string",
        "fieldType": "text",
        "groupName": "contactinformation",
        "description": "EyeNet Presence session UUID for the most recent grant",
    },
)

CONTACT_PROPERTY_NAMES = [
    "firstname",
    "lastname",
    "email",
    "phone",
    "mobilephone",
]


@dataclass
class HubSpotContact:
    contact_id: str
    firstname: str = ""
    lastname: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None

    @property
    def display_name(self) -> str:
        parts = [part.strip() for part in (self.firstname, self.lastname) if part and part.strip()]
        if parts:
            return " ".join(parts)
        if self.email:
            return self.email
        return f"HubSpot {self.contact_id}"


def map_hubspot_contact(raw: dict[str, Any]) -> HubSpotContact | None:
    contact_id = str(raw.get("id") or "").strip()
    if not contact_id:
        return None
    props = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    email = (props.get("email") or "").strip() or None
    phone = (props.get("phone") or props.get("mobilephone") or "").strip() or None
    return HubSpotContact(
        contact_id=contact_id,
        firstname=(props.get("firstname") or "").strip(),
        lastname=(props.get("lastname") or "").strip(),
        email=email,
        phone=phone,
    )


def grant_note_body(
    *,
    session_uuid: str,
    grant_type: str,
    assurance_level: str | None,
    person_name: str | None,
    occurred_at: datetime | None,
) -> str:
    when = (occurred_at or datetime.utcnow()).isoformat() + "Z"
    name = person_name or "Unknown"
    level = assurance_level or "n/a"
    return (
        f"EyeNet Presence grant\n"
        f"Person: {name}\n"
        f"Type: {grant_type}\n"
        f"Assurance: {level}\n"
        f"When: {when}\n"
        f"session_uuid={session_uuid}"
    )


class HubSpotCrmClient:
    def __init__(self, access_token: str, *, timeout: float = 30.0) -> None:
        self.access_token = (access_token or "").strip()
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        if not self.access_token:
            raise ValueError("HubSpot access token is not configured")
        url = path if path.startswith("http") else f"{HUBSPOT_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
                params=params,
            )
        if response.status_code >= 400:
            detail = response.text[:500]
            raise RuntimeError(f"HubSpot {method} {path} failed ({response.status_code}): {detail}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def test_connection(self) -> tuple[bool, str, str | None]:
        try:
            data = await self._request("GET", "/account-info/v3/details")
        except Exception as exc:  # noqa: BLE001 — surface connection errors to UI
            return False, str(exc), None
        hub_id = None
        if isinstance(data, dict):
            hub_id = str(data.get("portalId") or data.get("hub_id") or "") or None
        return True, "Connected to HubSpot", hub_id

    async def ensure_presence_properties(self) -> None:
        for prop in PRESENCE_CONTACT_PROPERTIES:
            try:
                await self._request("GET", f"/crm/v3/properties/contacts/{prop['name']}")
                continue
            except RuntimeError as exc:
                if "404" not in str(exc):
                    logger.warning("Unable to read HubSpot property %s: %s", prop["name"], exc)
            try:
                await self._request("POST", "/crm/v3/properties/contacts", json_body=prop)
            except RuntimeError as create_exc:
                msg = str(create_exc)
                if "409" in msg or "PROPERTY_ALREADY_EXISTS" in msg:
                    continue
                logger.warning("Unable to create HubSpot property %s: %s", prop["name"], create_exc)

    async def iter_contacts(self, *, list_id: str | None = None) -> AsyncIterator[HubSpotContact]:
        if list_id and str(list_id).strip():
            async for contact in self._iter_list_contacts(str(list_id).strip()):
                yield contact
            return
        after: str | None = None
        while True:
            params: dict[str, Any] = {
                "limit": 100,
                "properties": ",".join(CONTACT_PROPERTY_NAMES),
            }
            if after:
                params["after"] = after
            data = await self._request("GET", "/crm/v3/objects/contacts", params=params)
            results = data.get("results") if isinstance(data, dict) else None
            if not isinstance(results, list):
                return
            for raw in results:
                if isinstance(raw, dict):
                    mapped = map_hubspot_contact(raw)
                    if mapped is not None:
                        yield mapped
            paging = data.get("paging") if isinstance(data, dict) else None
            next_page = paging.get("next") if isinstance(paging, dict) else None
            after = str(next_page.get("after")) if isinstance(next_page, dict) and next_page.get("after") else None
            if not after:
                return

    async def _iter_list_contacts(self, list_id: str) -> AsyncIterator[HubSpotContact]:
        after: str | None = None
        while True:
            params: dict[str, Any] = {"limit": 100}
            if after:
                params["after"] = after
            data = await self._request("GET", f"/crm/v3/lists/{list_id}/memberships", params=params)
            results = data.get("results") if isinstance(data, dict) else None
            if not isinstance(results, list) or not results:
                return
            for membership in results:
                if not isinstance(membership, dict):
                    continue
                record_id = str(membership.get("recordId") or membership.get("record_id") or "").strip()
                if not record_id:
                    continue
                contact = await self.get_contact(record_id)
                if contact is not None:
                    yield contact
            paging = data.get("paging") if isinstance(data, dict) else None
            next_page = paging.get("next") if isinstance(paging, dict) else None
            after = str(next_page.get("after")) if isinstance(next_page, dict) and next_page.get("after") else None
            if not after:
                return

    async def get_contact(self, contact_id: str) -> HubSpotContact | None:
        data = await self._request(
            "GET",
            f"/crm/v3/objects/contacts/{contact_id}",
            params={"properties": ",".join(CONTACT_PROPERTY_NAMES)},
        )
        if not isinstance(data, dict):
            return None
        return map_hubspot_contact(data)

    async def find_contact_by_email(self, email: str) -> HubSpotContact | None:
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        data = await self._request(
            "POST",
            "/crm/v3/objects/contacts/search",
            json_body={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": normalized,
                            }
                        ]
                    }
                ],
                "properties": CONTACT_PROPERTY_NAMES,
                "limit": 1,
            },
        )
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        return map_hubspot_contact(first) if isinstance(first, dict) else None

    async def create_note_for_contact(self, *, contact_id: str, body: str) -> str | None:
        # HubSpot notes use hs_timestamp in milliseconds
        ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        data = await self._request(
            "POST",
            "/crm/v3/objects/notes",
            json_body={
                "properties": {
                    "hs_note_body": body,
                    "hs_timestamp": str(ts_ms),
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 202,
                            }
                        ],
                    }
                ],
            },
        )
        if isinstance(data, dict):
            return str(data.get("id") or "") or None
        return None

    async def update_presence_properties(
        self,
        *,
        contact_id: str,
        occurred_at: datetime,
        grant_type: str,
        session_uuid: str,
    ) -> None:
        # HubSpot datetime properties expect milliseconds since epoch
        ts_ms = int(occurred_at.replace(tzinfo=timezone.utc).timestamp() * 1000) if occurred_at.tzinfo is None else int(occurred_at.timestamp() * 1000)
        await self._request(
            "PATCH",
            f"/crm/v3/objects/contacts/{contact_id}",
            json_body={
                "properties": {
                    "last_presence_at": str(ts_ms),
                    "last_presence_type": grant_type,
                    "last_presence_session_id": session_uuid,
                }
            },
        )
