from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

DATABASE_PATH = Path(os.getenv("AUTHORITY_DATABASE_PATH", "data/authority.db"))


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entitlements (
                entitlement_uuid TEXT PRIMARY KEY,
                application_key TEXT NOT NULL UNIQUE,
                approved_owner_email TEXT NOT NULL,
                owner_enabled INTEGER NOT NULL DEFAULT 1,
                licence_status TEXT NOT NULL,
                offline_grace_days INTEGER NOT NULL DEFAULT 14,
                tenant_name TEXT,
                installation_uuid TEXT,
                activation_status TEXT NOT NULL DEFAULT 'pending_activation',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS installations (
                installation_uuid TEXT PRIMARY KEY,
                application_key TEXT NOT NULL,
                approved_owner_email TEXT NOT NULL,
                owner_enabled INTEGER NOT NULL DEFAULT 1,
                licence_status TEXT NOT NULL,
                offline_grace_days INTEGER NOT NULL DEFAULT 14,
                tenant_name TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()

    _migrate_installations_to_entitlements()


def seed_demo_installation() -> None:
    if get_entitlement_by_application_key("mvp-demo-key") is not None:
        return

    upsert_entitlement(
        {
            "application_key": "mvp-demo-key",
            "approved_owner_email": "owner@example.com",
            "owner_enabled": True,
            "licence_status": "active",
            "offline_grace_days": 14,
            "tenant_name": "MVP Demo Tenant",
            "installation_uuid": "test-installation",
            "activation_status": "active",
            "notes": "Seed record for first authority-service deployment.",
        }
    )


def upsert_entitlement(record: dict[str, Any]) -> dict[str, Any]:
    entitlement_uuid = record.get("entitlement_uuid") or str(uuid.uuid4())
    application_key = record.get("application_key") or str(uuid.uuid4())
    installation_uuid = record.get("installation_uuid") or None
    activation_status = record.get("activation_status") or (
        "active" if installation_uuid else "pending_activation"
    )

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO entitlements (
                entitlement_uuid,
                application_key,
                approved_owner_email,
                owner_enabled,
                licence_status,
                offline_grace_days,
                tenant_name,
                installation_uuid,
                activation_status,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entitlement_uuid) DO UPDATE SET
                application_key = excluded.application_key,
                approved_owner_email = excluded.approved_owner_email,
                owner_enabled = excluded.owner_enabled,
                licence_status = excluded.licence_status,
                offline_grace_days = excluded.offline_grace_days,
                tenant_name = excluded.tenant_name,
                installation_uuid = excluded.installation_uuid,
                activation_status = excluded.activation_status,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                entitlement_uuid,
                application_key,
                record["approved_owner_email"],
                int(record["owner_enabled"]),
                record["licence_status"],
                record["offline_grace_days"],
                record.get("tenant_name"),
                installation_uuid,
                activation_status,
                record.get("notes"),
            ),
        )

        if installation_uuid:
            connection.execute(
                """
                INSERT INTO installations (
                    installation_uuid,
                    application_key,
                    approved_owner_email,
                    owner_enabled,
                    licence_status,
                    offline_grace_days,
                    tenant_name,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(installation_uuid) DO UPDATE SET
                    application_key = excluded.application_key,
                    approved_owner_email = excluded.approved_owner_email,
                    owner_enabled = excluded.owner_enabled,
                    licence_status = excluded.licence_status,
                    offline_grace_days = excluded.offline_grace_days,
                    tenant_name = excluded.tenant_name,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    installation_uuid,
                    application_key,
                    record["approved_owner_email"],
                    int(record["owner_enabled"]),
                    record["licence_status"],
                    record["offline_grace_days"],
                    record.get("tenant_name"),
                    record.get("notes"),
                ),
            )
        connection.commit()

    stored_record = get_entitlement_by_uuid(entitlement_uuid)
    if stored_record is None:
        raise RuntimeError("Entitlement upsert failed")

    return stored_record


def activate_entitlement(application_key: str, installation_uuid: str, owner_email: str) -> dict[str, Any]:
    entitlement = get_entitlement_by_application_key(application_key)
    if entitlement is None:
        return {"approved": False, "reason": "unknown_application_key"}
    if entitlement["approved_owner_email"].lower() != owner_email.lower():
        return {"approved": False, "reason": "owner_email_not_approved"}
    if entitlement["owner_enabled"] is not True:
        return {"approved": False, "reason": "owner_disabled"}
    if entitlement["licence_status"] not in {"active", "grace"}:
        return {"approved": False, "reason": "licence_inactive"}
    if entitlement["installation_uuid"] and entitlement["installation_uuid"] != installation_uuid:
        return {"approved": False, "reason": "installation_already_bound_elsewhere"}

    existing_installation = get_installation_by_uuid(installation_uuid)
    if existing_installation and existing_installation["application_key"] != application_key:
        return {"approved": False, "reason": "installation_already_bound_elsewhere"}

    updated_entitlement = upsert_entitlement(
        {
            **entitlement,
            "installation_uuid": installation_uuid,
            "activation_status": "active",
        }
    )
    return {
        "approved": True,
        "reason": "approved_owner",
        **updated_entitlement,
    }


def get_installation_by_uuid(installation_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM installations WHERE installation_uuid = ?",
            (installation_uuid,),
        ).fetchone()

    return _row_to_dict(row)


def get_entitlement_by_uuid(entitlement_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM entitlements WHERE entitlement_uuid = ?",
            (entitlement_uuid,),
        ).fetchone()

    return _entitlement_row_to_dict(row)


def get_entitlement_by_application_key(application_key: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM entitlements WHERE application_key = ?",
            (application_key,),
        ).fetchone()

    return _entitlement_row_to_dict(row)


def list_entitlements() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM entitlements ORDER BY updated_at DESC, approved_owner_email ASC"
        ).fetchall()

    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def delete_installation(installation_uuid: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM installations WHERE installation_uuid = ?",
            (installation_uuid,),
        )
        connection.commit()

    return cursor.rowcount > 0


def delete_entitlement(entitlement_uuid: str) -> bool:
    entitlement = get_entitlement_by_uuid(entitlement_uuid)
    if entitlement is None:
        return False

    with _connect() as connection:
        if entitlement["installation_uuid"]:
            connection.execute(
                "DELETE FROM installations WHERE installation_uuid = ?",
                (entitlement["installation_uuid"],),
            )
        cursor = connection.execute(
            "DELETE FROM entitlements WHERE entitlement_uuid = ?",
            (entitlement_uuid,),
        )
        connection.commit()

    return cursor.rowcount > 0


def find_installation_by_owner_email(email: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM entitlements WHERE lower(approved_owner_email) = lower(?) LIMIT 1",
            (email,),
        ).fetchone()

    return _entitlement_row_to_dict(row)


def _migrate_installations_to_entitlements() -> None:
    with _connect() as connection:
        entitlement_count = connection.execute(
            "SELECT COUNT(*) AS count FROM entitlements"
        ).fetchone()["count"]
        if entitlement_count:
            return

        rows = connection.execute("SELECT * FROM installations").fetchall()
        for row in rows:
            connection.execute(
                """
                INSERT INTO entitlements (
                    entitlement_uuid,
                    application_key,
                    approved_owner_email,
                    owner_enabled,
                    licence_status,
                    offline_grace_days,
                    tenant_name,
                    installation_uuid,
                    activation_status,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    row["application_key"],
                    row["approved_owner_email"],
                    row["owner_enabled"],
                    row["licence_status"],
                    row["offline_grace_days"],
                    row["tenant_name"],
                    row["installation_uuid"],
                    "active",
                    row["notes"],
                ),
            )
        connection.commit()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "installation_uuid": row["installation_uuid"],
        "application_key": row["application_key"],
        "approved_owner_email": row["approved_owner_email"],
        "owner_enabled": bool(row["owner_enabled"]),
        "licence_status": row["licence_status"],
        "offline_grace_days": row["offline_grace_days"],
        "tenant_name": row["tenant_name"],
        "notes": row["notes"],
    }


def _entitlement_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "entitlement_uuid": row["entitlement_uuid"],
        "installation_uuid": row["installation_uuid"],
        "application_key": row["application_key"],
        "approved_owner_email": row["approved_owner_email"],
        "owner_enabled": bool(row["owner_enabled"]),
        "licence_status": row["licence_status"],
        "offline_grace_days": row["offline_grace_days"],
        "tenant_name": row["tenant_name"],
        "activation_status": row["activation_status"],
        "notes": row["notes"],
    }