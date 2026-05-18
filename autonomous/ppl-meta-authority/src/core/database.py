from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class DatabaseSettings:
    backend: str
    connection_value: str


def get_database_settings() -> DatabaseSettings:
    database_url = os.getenv("AUTHORITY_DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("AUTHORITY_DATABASE_URL must be set for the PostgreSQL authority service")

    scheme = urlparse(database_url).scheme.lower()
    if scheme not in {"postgres", "postgresql"}:
        raise ValueError("AUTHORITY_DATABASE_URL must use a postgres:// or postgresql:// scheme")
    return DatabaseSettings(backend="postgres", connection_value=database_url)


class DatabaseConnection:
    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self.connection: psycopg.Connection[Any] | None = None

    def __enter__(self) -> "DatabaseConnection":
        self.connection = psycopg.connect(self.settings.connection_value, row_factory=dict_row)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.connection is None:
            return
        if exc_type is not None:
            self.connection.rollback()
        self.connection.close()
        self.connection = None

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> Any:
        if self.connection is None:
            raise RuntimeError("Database connection is not open")

        translated_query = translate_query(query, self.settings.backend)
        normalized_params = tuple(params)
        return self.connection.execute(translated_query, normalized_params)

    def commit(self) -> None:
        if self.connection is None:
            raise RuntimeError("Database connection is not open")
        self.connection.commit()


def connect_database() -> DatabaseConnection:
    return DatabaseConnection(get_database_settings())


def translate_query(query: str, backend: str) -> str:
    translated = query
    if backend == "postgres":
        translated = _translate_insert_or_ignore(translated)
        translated = translated.replace("?", "%s")
    return translated


def _translate_insert_or_ignore(query: str) -> str:
    if "INSERT OR IGNORE INTO" not in query:
        return query

    translated = query.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1)
    match = re.search(r"VALUES\s*\([^)]*\)", translated, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return translated

    insertion_end = match.end()
    return f"{translated[:insertion_end]} ON CONFLICT DO NOTHING{translated[insertion_end:]}"