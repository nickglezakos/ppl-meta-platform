from __future__ import annotations

import uuid
import json
import secrets
import hashlib
from typing import Any

from core.database import connect_database, get_database_settings


def _connect():
    return connect_database()


def _database_backend() -> str:
    return get_database_settings().backend


def _future_timestamp_expression(quantity: int, unit: str) -> tuple[str, tuple[Any, ...]]:
    return "CURRENT_TIMESTAMP + %s::interval", (f"{quantity} {unit}",)


def _expired_expression(column_name: str) -> str:
    return f"{column_name} <= CURRENT_TIMESTAMP"


def _not_expired_expression(column_name: str) -> str:
    return f"{column_name} > CURRENT_TIMESTAMP"


def _schema_statements() -> list[str]:
    return [
        """
        CREATE TABLE IF NOT EXISTS entitlements (
            entitlement_uuid TEXT PRIMARY KEY,
            application_key TEXT NOT NULL UNIQUE,
            approved_owner_email TEXT NOT NULL,
            owner_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            licence_status TEXT NOT NULL,
            offline_grace_days INTEGER NOT NULL DEFAULT 14,
            tenant_name TEXT,
            installation_uuid TEXT,
            activation_status TEXT NOT NULL DEFAULT 'pending_activation',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS installations (
            installation_uuid TEXT PRIMARY KEY,
            application_key TEXT NOT NULL,
            approved_owner_email TEXT NOT NULL,
            owner_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            licence_status TEXT NOT NULL,
            offline_grace_days INTEGER NOT NULL DEFAULT 14,
            tenant_name TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS installation_state_reports (
            report_uuid TEXT PRIMARY KEY,
            installation_uuid TEXT NOT NULL,
            current_release_version TEXT NOT NULL,
            deployment_mode TEXT,
            health_state TEXT,
            components_json TEXT NOT NULL DEFAULT '{}',
            reported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (installation_uuid) REFERENCES installations(installation_uuid)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS update_events (
            update_event_uuid TEXT PRIMARY KEY,
            installation_uuid TEXT NOT NULL,
            from_release_version TEXT,
            to_release_version TEXT NOT NULL,
            status TEXT NOT NULL,
            failure_reason TEXT,
            components_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (installation_uuid) REFERENCES installations(installation_uuid)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS authority_users (
            user_uuid TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role_name TEXT NOT NULL DEFAULT 'owner',
            status TEXT NOT NULL DEFAULT 'active',
            distributor_uuid TEXT,
            reseller_uuid TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS authority_sessions (
            session_token TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            FOREIGN KEY (user_uuid) REFERENCES authority_users(user_uuid)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS authority_invitations (
            invitation_uuid TEXT PRIMARY KEY,
            invitation_token TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            role_name TEXT NOT NULL,
            distributor_uuid TEXT,
            reseller_uuid TEXT,
            issued_by_user_uuid TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            email_delivery_attempted BOOLEAN NOT NULL DEFAULT FALSE,
            email_delivered BOOLEAN NOT NULL DEFAULT FALSE,
            email_delivery_message TEXT,
            accepted_by_user_uuid TEXT,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS authority_user_installations (
            assignment_uuid TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            entitlement_uuid TEXT NOT NULL,
            assigned_by_user_uuid TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_uuid, entitlement_uuid),
            FOREIGN KEY (user_uuid) REFERENCES authority_users(user_uuid),
            FOREIGN KEY (entitlement_uuid) REFERENCES entitlements(entitlement_uuid)
        )
        """,
    ]


def initialize_database() -> None:
    with _connect() as connection:
        for statement in _schema_statements():
            connection.execute(statement)
        _ensure_column(connection, "authority_users", "distributor_uuid", "TEXT")
        _ensure_column(connection, "authority_invitations", "distributor_uuid", "TEXT")
        _ensure_column(connection, "authority_invitations", "email_delivery_attempted", "BOOLEAN NOT NULL DEFAULT FALSE")
        _ensure_column(connection, "authority_invitations", "email_delivered", "BOOLEAN NOT NULL DEFAULT FALSE")
        _ensure_column(connection, "authority_invitations", "email_delivery_message", "TEXT")
        connection.commit()

    _migrate_installations_to_entitlements()


def _ensure_column(connection: Any, table_name: str, column_name: str, column_definition: str) -> None:
    if _column_exists(connection, table_name, column_name):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def _column_exists(connection: Any, table_name: str, column_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = ? AND column_name = ?
        LIMIT 1
        """,
        (table_name, column_name),
    ).fetchone()
    return row is not None


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


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1)
    return f"scrypt${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, expected = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "scrypt":
        return False
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1)
    return secrets.compare_digest(derived.hex(), expected)


def create_authority_user(
    email: str,
    password: str,
    display_name: str | None = None,
    role_name: str = "owner",
    distributor_uuid: str | None = None,
    reseller_uuid: str | None = None,
) -> dict[str, Any]:
    user_uuid = str(uuid.uuid4())
    password_hash = hash_password(password)
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO authority_users (
                user_uuid,
                email,
                password_hash,
                display_name,
                role_name,
                distributor_uuid,
                reseller_uuid
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_uuid, email.lower(), password_hash, display_name, role_name, distributor_uuid, reseller_uuid),
        )
        connection.commit()

    user = get_authority_user_by_uuid(user_uuid)
    if user is None:
        raise RuntimeError("Authority user creation failed")
    return user


def update_authority_user_from_invitation(
    user_uuid: str,
    password: str,
    role_name: str,
    distributor_uuid: str | None = None,
    reseller_uuid: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    password_hash = hash_password(password)
    with _connect() as connection:
        connection.execute(
            """
            UPDATE authority_users
            SET password_hash = ?,
                display_name = COALESCE(?, display_name),
                role_name = ?,
                distributor_uuid = ?,
                reseller_uuid = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_uuid = ?
            """,
            (password_hash, display_name, role_name, distributor_uuid, reseller_uuid, user_uuid),
        )
        connection.commit()

    user = get_authority_user_by_uuid(user_uuid)
    if user is None:
        raise RuntimeError("Authority user update failed")
    return user


def create_authority_user_from_invitation(
    invitation_token: str,
    password: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    invitation = get_invitation_by_token(invitation_token)
    if invitation is None:
        raise ValueError("Invitation not found")
    if invitation["status"] != "pending":
        raise ValueError("Invitation is not pending")
    if invitation["is_expired"]:
        raise ValueError("Invitation expired")

    existing = get_authority_user_by_email(invitation["email"])
    if existing is not None:
        user = update_authority_user_from_invitation(
            user_uuid=existing["user_uuid"],
            password=password,
            display_name=display_name,
            role_name=invitation["role_name"],
            distributor_uuid=invitation.get("distributor_uuid"),
            reseller_uuid=invitation["reseller_uuid"],
        )
    else:
        user = create_authority_user(
            email=invitation["email"],
            password=password,
            display_name=display_name,
            role_name=invitation["role_name"],
            distributor_uuid=invitation.get("distributor_uuid"),
            reseller_uuid=invitation["reseller_uuid"],
        )

    mark_invitation_accepted(invitation["invitation_uuid"], user["user_uuid"])
    return user


def get_authority_user_by_email(email: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM authority_users WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()

    return _authority_user_row_to_dict(row)


def get_authority_user_by_uuid(user_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM authority_users WHERE user_uuid = ?",
            (user_uuid,),
        ).fetchone()

    return _authority_user_row_to_dict(row)


def authenticate_authority_user(email: str, password: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM authority_users WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()

    if row is None:
        return None
    if row["status"] != "active":
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return _authority_user_row_to_dict(row)


def create_authority_session(user_uuid: str, expires_in_hours: int = 24) -> dict[str, Any]:
    session_token = secrets.token_urlsafe(32)
    expires_expr, expires_params = _future_timestamp_expression(expires_in_hours, "hours")
    with _connect() as connection:
        connection.execute(
            f"""
            INSERT INTO authority_sessions (
                session_token,
                user_uuid,
                expires_at
            ) VALUES (?, ?, {expires_expr})
            """,
            (session_token, user_uuid, *expires_params),
        )
        connection.commit()

    session = get_authority_session(session_token)
    if session is None:
        raise RuntimeError("Authority session creation failed")
    return session


def get_authority_session(session_token: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
                        f"""
            SELECT s.*, u.email, u.display_name, u.role_name, u.status, u.reseller_uuid
            , u.distributor_uuid
            FROM authority_sessions s
            JOIN authority_users u ON u.user_uuid = s.user_uuid
            WHERE s.session_token = ?
              AND s.revoked_at IS NULL
                            AND {_not_expired_expression('s.expires_at')}
            """,
            (session_token,),
        ).fetchone()

    return _authority_session_row_to_dict(row)


def revoke_authority_session(session_token: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE authority_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE session_token = ? AND revoked_at IS NULL
            """,
            (session_token,),
        )
        connection.commit()
    return cursor.rowcount > 0


def bootstrap_authority_admin(email: str, password: str, display_name: str | None = None) -> dict[str, Any]:
    existing = get_authority_user_by_email(email)
    if existing is not None:
        return existing
    return create_authority_user(
        email=email,
        password=password,
        display_name=display_name,
        role_name="platform_admin",
    )


def create_invitation(
    email: str,
    role_name: str,
    issued_by_user_uuid: str | None,
    distributor_uuid: str | None = None,
    reseller_uuid: str | None = None,
    expires_in_days: int = 7,
) -> dict[str, Any]:
    invitation_uuid = str(uuid.uuid4())
    invitation_token = secrets.token_urlsafe(24)
    normalized_reseller_uuid = (reseller_uuid or "").strip() or None
    if role_name == "reseller" and not normalized_reseller_uuid:
        normalized_reseller_uuid = f"reseller-{invitation_uuid[:8]}"
    expires_expr, expires_params = _future_timestamp_expression(expires_in_days, "days")
    with _connect() as connection:
        connection.execute(
            f"""
            INSERT INTO authority_invitations (
                invitation_uuid,
                invitation_token,
                email,
                role_name,
                distributor_uuid,
                reseller_uuid,
                issued_by_user_uuid,
                expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, {expires_expr})
            """,
            (
                invitation_uuid,
                invitation_token,
                email.lower(),
                role_name,
                distributor_uuid,
                normalized_reseller_uuid,
                issued_by_user_uuid,
                *expires_params,
            ),
        )
        connection.commit()

    invitation = get_invitation_by_uuid(invitation_uuid)
    if invitation is None:
        raise RuntimeError("Invitation creation failed")
    return invitation


def get_invitation_by_uuid(invitation_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT *, {_expired_expression('expires_at')} AS is_expired FROM authority_invitations WHERE invitation_uuid = ?",
            (invitation_uuid,),
        ).fetchone()
    return _invitation_row_to_dict(row)


def get_invitation_by_token(invitation_token: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT *, {_expired_expression('expires_at')} AS is_expired FROM authority_invitations WHERE invitation_token = ?",
            (invitation_token,),
        ).fetchone()
    return _invitation_row_to_dict(row)


def list_invitations() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT *, {_expired_expression('expires_at')} AS is_expired FROM authority_invitations ORDER BY created_at DESC"
        ).fetchall()
    return [_invitation_row_to_dict(row) for row in rows if row is not None]


def update_invitation_email_delivery(
    invitation_uuid: str,
    attempted: bool,
    delivered: bool,
    message: str | None,
) -> dict[str, Any]:
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE authority_invitations
            SET email_delivery_attempted = ?,
                email_delivered = ?,
                email_delivery_message = ?
            WHERE invitation_uuid = ?
            """,
            (attempted, delivered, message, invitation_uuid),
        )
        connection.commit()
    if cursor.rowcount <= 0:
        raise RuntimeError("Invitation email delivery update failed")

    invitation = get_invitation_by_uuid(invitation_uuid)
    if invitation is None:
        raise RuntimeError("Invitation email delivery update could not reload invitation")
    return invitation


def mark_invitation_accepted(invitation_uuid: str, user_uuid: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE authority_invitations
            SET status = 'accepted',
                accepted_by_user_uuid = ?,
                accepted_at = CURRENT_TIMESTAMP
            WHERE invitation_uuid = ? AND status = 'pending'
            """,
            (user_uuid, invitation_uuid),
        )
        connection.commit()
    return cursor.rowcount > 0


def assign_entitlement_to_user(
    entitlement_uuid: str,
    user_uuid: str,
    assigned_by_user_uuid: str | None = None,
) -> dict[str, Any]:
    assignment_uuid = str(uuid.uuid4())
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO authority_user_installations (
                assignment_uuid,
                user_uuid,
                entitlement_uuid,
                assigned_by_user_uuid
            ) VALUES (?, ?, ?, ?)
            """,
            (assignment_uuid, user_uuid, entitlement_uuid, assigned_by_user_uuid),
        )
        connection.commit()

    assignment = get_assignment_by_user_and_entitlement(user_uuid, entitlement_uuid)
    if assignment is None:
        raise RuntimeError("Assignment creation failed")
    return assignment


def get_assignment_by_user_and_entitlement(user_uuid: str, entitlement_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM authority_user_installations WHERE user_uuid = ? AND entitlement_uuid = ?",
            (user_uuid, entitlement_uuid),
        ).fetchone()
    return _assignment_row_to_dict(row)


def list_entitlements_for_user_uuid(user_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT e.*
            FROM authority_user_installations a
            JOIN entitlements e ON e.entitlement_uuid = a.entitlement_uuid
            WHERE a.user_uuid = ?
            ORDER BY e.updated_at DESC, e.tenant_name ASC
            """,
            (user_uuid,),
        ).fetchall()
    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def list_entitlements_for_reseller_uuid(reseller_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT e.*
            FROM authority_user_installations a
            JOIN authority_users u ON u.user_uuid = a.user_uuid
            JOIN entitlements e ON e.entitlement_uuid = a.entitlement_uuid
            WHERE u.reseller_uuid = ? AND u.role_name = 'owner'
            ORDER BY e.updated_at DESC, e.approved_owner_email ASC
            """,
            (reseller_uuid,),
        ).fetchall()
    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def list_entitlements_for_distributor_uuid(distributor_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT e.*
            FROM authority_user_installations a
            JOIN authority_users u ON u.user_uuid = a.user_uuid
            JOIN entitlements e ON e.entitlement_uuid = a.entitlement_uuid
            WHERE u.distributor_uuid = ? AND u.role_name = 'owner'
            ORDER BY e.updated_at DESC, e.approved_owner_email ASC
            """,
            (distributor_uuid,),
        ).fetchall()
    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def list_owner_users_by_reseller_uuid(reseller_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM authority_users
            WHERE reseller_uuid = ? AND role_name = 'owner'
            ORDER BY created_at DESC, email ASC
            """,
            (reseller_uuid,),
        ).fetchall()
    return [_authority_user_row_to_dict(row) for row in rows if row is not None]


def list_reseller_users_by_distributor_uuid(distributor_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM authority_users
            WHERE distributor_uuid = ? AND role_name = 'reseller'
            ORDER BY created_at DESC, email ASC
            """,
            (distributor_uuid,),
        ).fetchall()
    return [_authority_user_row_to_dict(row) for row in rows if row is not None]


def list_owner_users_by_distributor_uuid(distributor_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM authority_users
            WHERE distributor_uuid = ? AND role_name = 'owner'
            ORDER BY created_at DESC, email ASC
            """,
            (distributor_uuid,),
        ).fetchall()
    return [_authority_user_row_to_dict(row) for row in rows if row is not None]


def list_recent_assignment_activity(
    limit: int = 5,
    reseller_uuid: str | None = None,
    distributor_uuid: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            a.assignment_uuid,
            a.user_uuid,
            a.entitlement_uuid,
            a.assigned_by_user_uuid,
            a.created_at,
            u.email AS owner_email,
            u.reseller_uuid,
            e.application_key,
            e.tenant_name,
            e.activation_status
        FROM authority_user_installations a
        JOIN authority_users u ON u.user_uuid = a.user_uuid
        JOIN entitlements e ON e.entitlement_uuid = a.entitlement_uuid
    """
    params: tuple[Any, ...]
    if distributor_uuid:
        query += " WHERE u.distributor_uuid = ? AND u.role_name = 'owner'"
        params = (distributor_uuid, limit)
    elif reseller_uuid:
        query += " WHERE u.reseller_uuid = ? AND u.role_name = 'owner'"
        params = (reseller_uuid, limit)
    else:
        params = (limit,)
    query += " ORDER BY a.created_at DESC LIMIT ?"

    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()

    return [_assignment_activity_row_to_dict(row) for row in rows if row is not None]


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
                bool(record["owner_enabled"]),
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
                    bool(record["owner_enabled"]),
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


def get_entitlement_by_installation_uuid(installation_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM entitlements WHERE installation_uuid = ?",
            (installation_uuid,),
        ).fetchone()

    return _entitlement_row_to_dict(row)


def list_entitlements() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM entitlements ORDER BY updated_at DESC, approved_owner_email ASC"
        ).fetchall()

    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def list_entitlements_for_owner_email(email: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM entitlements
            WHERE lower(approved_owner_email) = lower(?)
            ORDER BY updated_at DESC, tenant_name ASC
            """,
            (email,),
        ).fetchall()

    return [_entitlement_row_to_dict(row) for row in rows if row is not None]


def list_authority_users_by_reseller_uuid(reseller_uuid: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM authority_users
            WHERE reseller_uuid = ?
            ORDER BY created_at DESC, email ASC
            """,
            (reseller_uuid,),
        ).fetchall()

    return [_authority_user_row_to_dict(row) for row in rows if row is not None]


def list_authority_users() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM authority_users
            ORDER BY distributor_uuid ASC NULLS FIRST, reseller_uuid ASC NULLS FIRST, role_name ASC, email ASC
            """
        ).fetchall()

    return [_authority_user_row_to_dict(row) for row in rows if row is not None]


def list_entitlements_for_owner_emails(emails: list[str]) -> list[dict[str, Any]]:
    if not emails:
        return []

    placeholders = ",".join("?" for _ in emails)
    normalized_emails = [email.lower() for email in emails]
    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM entitlements
            WHERE lower(approved_owner_email) IN ({placeholders})
            ORDER BY updated_at DESC, approved_owner_email ASC
            """,
            normalized_emails,
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


def record_installation_state(report: dict[str, Any]) -> dict[str, Any]:
    report_uuid = str(uuid.uuid4())
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO installation_state_reports (
                report_uuid,
                installation_uuid,
                current_release_version,
                deployment_mode,
                health_state,
                components_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report_uuid,
                report["installation_uuid"],
                report["current_release_version"],
                report.get("deployment_mode"),
                report.get("health_state"),
                json.dumps(report.get("components", {}), sort_keys=True),
            ),
        )
        connection.commit()

    stored_report = get_latest_installation_state(report["installation_uuid"])
    if stored_report is None:
        raise RuntimeError("Installation state report insert failed")
    return stored_report


def get_latest_installation_state(installation_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM installation_state_reports
            WHERE installation_uuid = ?
            ORDER BY reported_at DESC, report_uuid DESC
            LIMIT 1
            """,
            (installation_uuid,),
        ).fetchone()

    return _installation_state_row_to_dict(row)


def evaluate_update_eligibility(
    installation_uuid: str,
    target_release_version: str,
) -> dict[str, Any]:
    entitlement = get_entitlement_by_installation_uuid(installation_uuid)
    if entitlement is None:
        return {"allowed": False, "reason": "unknown_installation"}
    if entitlement["activation_status"] != "active":
        return {"allowed": False, "reason": "installation_not_active"}
    if entitlement["owner_enabled"] is not True:
        return {"allowed": False, "reason": "owner_disabled"}
    if entitlement["licence_status"] not in {"active", "grace"}:
        return {"allowed": False, "reason": "licence_inactive"}

    latest_state = get_latest_installation_state(installation_uuid)
    current_release_version = None if latest_state is None else latest_state["current_release_version"]

    if current_release_version == target_release_version:
        return {
            "allowed": False,
            "reason": "target_matches_current",
            "current_release_version": current_release_version,
            "target_release_version": target_release_version,
        }

    return {
        "allowed": True,
        "reason": "eligible",
        "current_release_version": current_release_version,
        "target_release_version": target_release_version,
        "installation_uuid": installation_uuid,
    }


def record_update_event(event: dict[str, Any]) -> dict[str, Any]:
    update_event_uuid = str(uuid.uuid4())
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO update_events (
                update_event_uuid,
                installation_uuid,
                from_release_version,
                to_release_version,
                status,
                failure_reason,
                components_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update_event_uuid,
                event["installation_uuid"],
                event.get("from_release_version"),
                event["to_release_version"],
                event["status"],
                event.get("failure_reason"),
                json.dumps(event.get("components", {}), sort_keys=True),
            ),
        )
        connection.commit()

    stored_event = get_update_event(update_event_uuid)
    if stored_event is None:
        raise RuntimeError("Update event insert failed")
    return stored_event


def get_update_event(update_event_uuid: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM update_events WHERE update_event_uuid = ?",
            (update_event_uuid,),
        ).fetchone()

    return _update_event_row_to_dict(row)


def list_recent_update_events_for_owner(
    owner_email: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                u.update_event_uuid,
                u.installation_uuid,
                u.from_release_version,
                u.to_release_version,
                u.status,
                u.failure_reason,
                u.components_json,
                u.created_at,
                e.entitlement_uuid,
                e.application_key,
                e.tenant_name,
                e.approved_owner_email,
                e.activation_status,
                e.licence_status
            FROM update_events u
            JOIN entitlements e ON e.installation_uuid = u.installation_uuid
            WHERE lower(e.approved_owner_email) = lower(?)
            ORDER BY u.created_at DESC
            LIMIT ?
            """,
            (owner_email, limit),
        ).fetchall()

    return [_owner_update_activity_row_to_dict(row) for row in rows if row is not None]


def list_recent_state_reports_for_owner(
    owner_email: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                r.report_uuid,
                r.installation_uuid,
                r.current_release_version,
                r.deployment_mode,
                r.health_state,
                r.components_json,
                r.reported_at,
                e.entitlement_uuid,
                e.application_key,
                e.tenant_name,
                e.approved_owner_email,
                e.activation_status,
                e.licence_status
            FROM installation_state_reports r
            JOIN entitlements e ON e.installation_uuid = r.installation_uuid
            WHERE lower(e.approved_owner_email) = lower(?)
            ORDER BY r.reported_at DESC, r.report_uuid DESC
            LIMIT ?
            """,
            (owner_email, limit),
        ).fetchall()

    return [_state_activity_row_to_dict(row) for row in rows if row is not None]


def list_recent_state_reports_for_reseller(
    reseller_uuid: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT
                r.report_uuid,
                r.installation_uuid,
                r.current_release_version,
                r.deployment_mode,
                r.health_state,
                r.components_json,
                r.reported_at,
                e.entitlement_uuid,
                e.application_key,
                e.tenant_name,
                e.approved_owner_email,
                e.activation_status,
                e.licence_status
            FROM installation_state_reports r
            JOIN entitlements e ON e.installation_uuid = r.installation_uuid
            JOIN authority_user_installations a ON a.entitlement_uuid = e.entitlement_uuid
            JOIN authority_users u ON u.user_uuid = a.user_uuid
            WHERE u.reseller_uuid = ? AND u.role_name = 'owner'
            ORDER BY r.reported_at DESC, r.report_uuid DESC
            LIMIT ?
            """,
            (reseller_uuid, limit),
        ).fetchall()

    return [_state_activity_row_to_dict(row) for row in rows if row is not None]


def list_recent_state_reports_for_distributor(
    distributor_uuid: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT
                r.report_uuid,
                r.installation_uuid,
                r.current_release_version,
                r.deployment_mode,
                r.health_state,
                r.components_json,
                r.reported_at,
                e.entitlement_uuid,
                e.application_key,
                e.tenant_name,
                e.approved_owner_email,
                e.activation_status,
                e.licence_status
            FROM installation_state_reports r
            JOIN entitlements e ON e.installation_uuid = r.installation_uuid
            JOIN authority_user_installations a ON a.entitlement_uuid = e.entitlement_uuid
            JOIN authority_users u ON u.user_uuid = a.user_uuid
            WHERE u.distributor_uuid = ? AND u.role_name = 'owner'
            ORDER BY r.reported_at DESC, r.report_uuid DESC
            LIMIT ?
            """,
            (distributor_uuid, limit),
        ).fetchall()

    return [_state_activity_row_to_dict(row) for row in rows if row is not None]


def list_recent_state_reports(limit: int = 5) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                r.report_uuid,
                r.installation_uuid,
                r.current_release_version,
                r.deployment_mode,
                r.health_state,
                r.components_json,
                r.reported_at,
                e.entitlement_uuid,
                e.application_key,
                e.tenant_name,
                e.approved_owner_email,
                e.activation_status,
                e.licence_status
            FROM installation_state_reports r
            JOIN entitlements e ON e.installation_uuid = r.installation_uuid
            ORDER BY r.reported_at DESC, r.report_uuid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [_state_activity_row_to_dict(row) for row in rows if row is not None]


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


def _timestamp_value(value: Any) -> Any:
    if value is None:
        return None
    return str(value)


def _row_to_dict(row: Any | None) -> dict[str, Any] | None:
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


def _entitlement_row_to_dict(row: Any | None) -> dict[str, Any] | None:
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


def _authority_user_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "user_uuid": row["user_uuid"],
        "email": row["email"],
        "display_name": row["display_name"],
        "role_name": row["role_name"],
        "status": row["status"],
        "distributor_uuid": row["distributor_uuid"],
        "reseller_uuid": row["reseller_uuid"],
        "created_at": _timestamp_value(row["created_at"]),
        "updated_at": _timestamp_value(row["updated_at"]),
    }
def _authority_session_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "session_token": row["session_token"],
        "user_uuid": row["user_uuid"],
        "email": row["email"],
        "display_name": row["display_name"],
        "role_name": row["role_name"],
        "status": row["status"],
        "distributor_uuid": row["distributor_uuid"],
        "reseller_uuid": row["reseller_uuid"],
        "created_at": _timestamp_value(row["created_at"]),
        "expires_at": _timestamp_value(row["expires_at"]),
    }
def _invitation_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    stored_status = row["status"]
    is_expired = bool(row["is_expired"])
    if stored_status == "accepted":
        effective_status = "accepted"
    elif is_expired:
        effective_status = "expired"
    else:
        effective_status = stored_status

    return {
        "invitation_uuid": row["invitation_uuid"],
        "invitation_token": row["invitation_token"],
        "email": row["email"],
        "role_name": row["role_name"],
        "distributor_uuid": row["distributor_uuid"],
        "reseller_uuid": row["reseller_uuid"],
        "issued_by_user_uuid": row["issued_by_user_uuid"],
        "status": stored_status,
        "effective_status": effective_status,
        "accepted_by_user_uuid": row["accepted_by_user_uuid"],
        "expires_at": _timestamp_value(row["expires_at"]),
        "created_at": _timestamp_value(row["created_at"]),
        "accepted_at": _timestamp_value(row["accepted_at"]),
        "is_expired": is_expired,
        "email_delivery_attempted": bool(row.get("email_delivery_attempted", False)),
        "email_delivered": bool(row.get("email_delivered", False)),
        "email_delivery_message": row.get("email_delivery_message"),
    }
def _assignment_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "assignment_uuid": row["assignment_uuid"],
        "user_uuid": row["user_uuid"],
        "entitlement_uuid": row["entitlement_uuid"],
        "assigned_by_user_uuid": row["assigned_by_user_uuid"],
        "created_at": _timestamp_value(row["created_at"]),
    }
def _assignment_activity_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "assignment_uuid": row["assignment_uuid"],
        "user_uuid": row["user_uuid"],
        "entitlement_uuid": row["entitlement_uuid"],
        "assigned_by_user_uuid": row["assigned_by_user_uuid"],
        "created_at": _timestamp_value(row["created_at"]),
        "owner_email": row["owner_email"],
        "reseller_uuid": row["reseller_uuid"],
        "application_key": row["application_key"],
        "tenant_name": row["tenant_name"],
        "activation_status": row["activation_status"],
    }


def _installation_state_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "report_uuid": row["report_uuid"],
        "installation_uuid": row["installation_uuid"],
        "current_release_version": row["current_release_version"],
        "deployment_mode": row["deployment_mode"],
        "health_state": row["health_state"],
        "components": json.loads(row["components_json"] or "{}"),
        "reported_at": _timestamp_value(row["reported_at"]),
    }
def _update_event_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "update_event_uuid": row["update_event_uuid"],
        "installation_uuid": row["installation_uuid"],
        "from_release_version": row["from_release_version"],
        "to_release_version": row["to_release_version"],
        "status": row["status"],
        "failure_reason": row["failure_reason"],
        "components": json.loads(row["components_json"] or "{}"),
        "created_at": _timestamp_value(row["created_at"]),
    }
def _owner_update_activity_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "update_event_uuid": row["update_event_uuid"],
        "installation_uuid": row["installation_uuid"],
        "from_release_version": row["from_release_version"],
        "to_release_version": row["to_release_version"],
        "status": row["status"],
        "failure_reason": row["failure_reason"],
        "components": json.loads(row["components_json"] or "{}"),
        "created_at": _timestamp_value(row["created_at"]),
        "entitlement_uuid": row["entitlement_uuid"],
        "application_key": row["application_key"],
        "tenant_name": row["tenant_name"],
        "approved_owner_email": row["approved_owner_email"],
        "activation_status": row["activation_status"],
        "licence_status": row["licence_status"],
    }


def _state_activity_row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None

    return {
        "report_uuid": row["report_uuid"],
        "installation_uuid": row["installation_uuid"],
        "current_release_version": row["current_release_version"],
        "deployment_mode": row["deployment_mode"],
        "health_state": row["health_state"],
        "components": json.loads(row["components_json"] or "{}"),
        "reported_at": _timestamp_value(row["reported_at"]),
        "entitlement_uuid": row["entitlement_uuid"],
        "application_key": row["application_key"],
        "tenant_name": row["tenant_name"],
        "approved_owner_email": row["approved_owner_email"],
        "activation_status": row["activation_status"],
        "licence_status": row["licence_status"],
    }