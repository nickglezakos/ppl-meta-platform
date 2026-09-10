"""SQL helpers for catalog model provenance on sessions and detections."""

SESSION_PROVENANCE_COLUMNS = (
    "model_id VARCHAR(128)",
    "model_version VARCHAR(64)",
    "runtime VARCHAR(64)",
    "confidence_threshold REAL",
    "path VARCHAR(32)",
    "serving BOOLEAN DEFAULT TRUE",
)

COPY_DETECTION_PROVENANCE_SQL = """
UPDATE face_detections AS d
SET model_id = s.model_id,
    model_version = s.model_version,
    runtime = s.runtime,
    confidence_threshold = s.confidence_threshold,
    path = s.path,
    serving = s.serving
FROM face_detection_sessions AS s
WHERE d.id = %s
  AND s.session_uuid = %s
"""


def ensure_provenance_columns_sql() -> list[str]:
    """Return ALTER/CREATE statements.

    Columns are added first for both tables, then indexes. Creating the
    (model_id, model_version) index before model_version exists aborts
    VisionDatabase.init_database() and leaves connection=None.
    """
    statements: list[str] = []
    tables = ("face_detection_sessions", "face_detections")
    for table in tables:
        for column_def in SESSION_PROVENANCE_COLUMNS:
            statements.append(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_def}"
            )
    for table in tables:
        statements.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_model "
            f"ON {table} (model_id, model_version)"
        )
    return statements
