"""SQLAlchemy catalog entities (Phase A + B)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MvModel(Base):
    __tablename__ = "mv_models"

    model_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="builtin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    versions: Mapped[list[MvModelVersion]] = relationship(back_populates="model")


class MvModelVersion(Base):
    __tablename__ = "mv_model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_mv_model_version"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("mv_models.model_id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime: Mapped[str] = mapped_column(String(64), nullable=False)
    output_schema_version: Mapped[str] = mapped_column(String(32), default="face-box-v1")
    latency_class: Mapped[str] = mapped_column(String(32), nullable=False)
    compatible_paths: Mapped[list] = mapped_column(JSON, nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")

    model: Mapped[MvModel] = relationship(back_populates="versions")


class MvArtifact(Base):
    __tablename__ = "mv_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MvRecipe(Base):
    __tablename__ = "mv_recipes"

    recipe_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # single | two_stage
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    steps: Mapped[list[MvRecipeStep]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class MvRecipeStep(Base):
    __tablename__ = "mv_recipe_steps"
    __table_args__ = (
        UniqueConstraint("recipe_id", "step_order", name="uq_mv_recipe_step_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("mv_recipes.recipe_id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # single|proposal|refine
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)

    recipe: Mapped[MvRecipe] = relationship(back_populates="steps")


class MvAssignment(Base):
    __tablename__ = "mv_assignments"
    __table_args__ = (
        UniqueConstraint(
            "capability",
            "scope_type",
            "scope_id",
            "path",
            name="uq_mv_assignment_scope_path",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    path: Mapped[str] = mapped_column(String(32), nullable=False)
    # XOR: recipe_id set OR (model_id + version) set. Empty strings mean unset.
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    recipe_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    shadow: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class MvAssignmentHistory(Base):
    __tablename__ = "mv_assignment_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    path: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    recipe_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    actor: Mapped[str] = mapped_column(String(128), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MvGoldenSet(Base):
    __tablename__ = "mv_golden_sets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    set_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="platform")
    site_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    items: Mapped[list[MvGoldenItem]] = relationship(
        back_populates="golden_set", cascade="all, delete-orphan"
    )


class MvGoldenItem(Base):
    __tablename__ = "mv_golden_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    set_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("mv_golden_sets.set_id"), nullable=False
    )
    media_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    baseline_boxes: Mapped[list] = mapped_column(JSON, default=list)
    frame_number: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    golden_set: Mapped[MvGoldenSet] = relationship(back_populates="items")


class MvValidationRun(Base):
    __tablename__ = "mv_validation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    golden_set_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # ready|failed|running
    mean_iou: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
