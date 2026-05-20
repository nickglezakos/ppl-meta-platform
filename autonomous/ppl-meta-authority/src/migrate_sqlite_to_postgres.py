from __future__ import annotations

import argparse
import os
import sqlite3
from typing import Any

import psycopg
from psycopg import sql

TABLES: list[tuple[str, list[str]]] = [
    ('authority_users', ['user_uuid', 'email', 'password_hash', 'display_name', 'role_name', 'status', 'distributor_uuid', 'reseller_uuid', 'created_at', 'updated_at']),
    ('entitlements', ['entitlement_uuid', 'application_key', 'approved_owner_email', 'owner_enabled', 'licence_status', 'offline_grace_days', 'tenant_name', 'installation_uuid', 'activation_status', 'notes', 'created_at', 'updated_at']),
    ('installations', ['installation_uuid', 'application_key', 'approved_owner_email', 'owner_enabled', 'licence_status', 'offline_grace_days', 'tenant_name', 'notes', 'created_at', 'updated_at']),
    ('authority_invitations', ['invitation_uuid', 'invitation_token', 'email', 'role_name', 'distributor_uuid', 'reseller_uuid', 'issued_by_user_uuid', 'status', 'accepted_by_user_uuid', 'expires_at', 'created_at', 'accepted_at']),
    ('authority_sessions', ['session_token', 'user_uuid', 'created_at', 'expires_at', 'revoked_at']),
    ('installation_state_reports', ['report_uuid', 'installation_uuid', 'current_release_version', 'deployment_mode', 'health_state', 'components_json', 'reported_at']),
    ('update_events', ['update_event_uuid', 'installation_uuid', 'from_release_version', 'to_release_version', 'status', 'failure_reason', 'components_json', 'created_at']),
    ('authority_user_installations', ['assignment_uuid', 'user_uuid', 'entitlement_uuid', 'assigned_by_user_uuid', 'created_at']),
]

TRUNCATE_STATEMENT = '''
TRUNCATE TABLE
    authority_user_installations,
    authority_sessions,
    authority_invitations,
    update_events,
    installation_state_reports,
    installations,
    entitlements,
    authority_users
RESTART IDENTITY CASCADE
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Migrate authority data from SQLite to PostgreSQL')
    parser.add_argument('--sqlite-path', required=True, help='Path to the source SQLite database file')
    parser.add_argument('--postgres-url', required=True, help='PostgreSQL connection URL for the target database')
    parser.add_argument('--keep-existing', action='store_true', help='Do not clear existing PostgreSQL data before import')
    return parser.parse_args()


def fetch_sqlite_rows(connection: sqlite3.Connection, table_name: str, columns: list[str]) -> list[tuple[Any, ...]]:
    rows = connection.execute(f"SELECT {', '.join(columns)} FROM {table_name}").fetchall()
    normalized: list[tuple[Any, ...]] = []
    for row in rows:
        values = list(row)
        if table_name in {'entitlements', 'installations'}:
            values[3] = bool(values[3])
        normalized.append(tuple(values))
    return normalized


def migrate_table(sqlite_connection: sqlite3.Connection, postgres_connection: psycopg.Connection[Any], table_name: str, columns: list[str]) -> int:
    rows = fetch_sqlite_rows(sqlite_connection, table_name, columns)
    if not rows:
        return 0

    statement = sql.SQL('INSERT INTO {table} ({fields}) VALUES ({placeholders}) ON CONFLICT DO NOTHING').format(
        table=sql.Identifier(table_name),
        fields=sql.SQL(', ').join(sql.Identifier(column) for column in columns),
        placeholders=sql.SQL(', ').join(sql.Placeholder() for _ in columns),
    )

    with postgres_connection.cursor() as cursor:
        cursor.executemany(statement, rows)
    postgres_connection.commit()
    return len(rows)


def main() -> None:
    args = parse_args()
    os.environ['AUTHORITY_DATABASE_URL'] = args.postgres_url

    from core.storage import initialize_database

    initialize_database()

    with sqlite3.connect(args.sqlite_path) as sqlite_connection, psycopg.connect(args.postgres_url) as postgres_connection:
        if not args.keep_existing:
            with postgres_connection.cursor() as cursor:
                cursor.execute(TRUNCATE_STATEMENT)
            postgres_connection.commit()

        for table_name, columns in TABLES:
            migrated = migrate_table(sqlite_connection, postgres_connection, table_name, columns)
            print(f'{table_name}: migrated {migrated} rows')


if __name__ == '__main__':
    main()
