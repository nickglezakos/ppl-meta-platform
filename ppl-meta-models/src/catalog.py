"""Builtin seed and catalog operations (Phase A + B pipelines)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    MvArtifact,
    MvAssignment,
    MvAssignmentHistory,
    MvGoldenItem,
    MvGoldenSet,
    MvModel,
    MvModelVersion,
    MvRecipe,
    MvRecipeStep,
    MvValidationRun,
)

BUILTIN_TWO_STAGE = "face-two-stage-builtin"
BUILTIN_HAAR = "face-haar-builtin"
BUILTIN_DLIB = "face-dlib-builtin"
BUILTIN_LANDMARKS = "face-landmarks-68-builtin"
BODY_PROPOSAL = "body-proposal-placeholder"
BODY_REFINE = "body-refine-placeholder"
FACE_YOLO = "face-yolo-onnx-os"
BODY_YOLO = "body-yolo-person-os"
BODY_YOLO_POSE = "body-yolo-pose-os"
DEFAULT_VERSION = "1.0.0"

RECIPE_HAAR_ONLY = "face-haar-only"
RECIPE_DLIB_ONLY = "face-dlib-only"
RECIPE_TWO_STAGE = "face-two-stage-haar-dlib"
RECIPE_BODY_SINGLE = "body-single-placeholder"
RECIPE_BODY_TWO_STAGE = "body-two-stage-placeholder"
RECIPE_FACE_YOLO = "face-yolo-onnx-only"
RECIPE_BODY_YOLO = "body-yolo-person-only"
RECIPE_BODY_YOLO_POSE = "body-yolo-pose-only"

# Opaque two_stage builtin expands to this recipe's stages.
BUILTIN_TO_RECIPE = {
    BUILTIN_TWO_STAGE: RECIPE_TWO_STAGE,
    BUILTIN_HAAR: RECIPE_HAAR_ONLY,
    BUILTIN_DLIB: RECIPE_DLIB_ONLY,
}

BUILTINS = [
    {
        "model_id": BUILTIN_HAAR,
        "display_name": "Haar cascade (builtin)",
        "capability": "face_detection",
        "runtime": "haar",
        "latency_class": "preview",
        "compatible_paths": ["preview", "instant", "bulk"],
        "hyperparameters": {"confidence": 0.5},
        "output_schema_version": "face-box-v1",
    },
    {
        "model_id": BUILTIN_DLIB,
        "display_name": "Dlib HOG (builtin)",
        "capability": "face_detection",
        "runtime": "dlib_hog",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {"confidence": 0.5},
        "output_schema_version": "face-box-v1",
    },
    {
        "model_id": BUILTIN_TWO_STAGE,
        "display_name": "Haar + Dlib two-stage (builtin)",
        "capability": "face_detection",
        "runtime": "two_stage",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {"confidence": 0.5},
        "output_schema_version": "face-box-v1",
    },
    {
        "model_id": BUILTIN_LANDMARKS,
        "display_name": "Dlib 68-point landmarks (builtin)",
        "capability": "face_landmarks",
        "runtime": "dlib_68",
        "latency_class": "bulk",
        "compatible_paths": ["bulk"],
        "hyperparameters": {},
        "output_schema_version": "landmarks-68-v1",
    },
    {
        "model_id": BODY_PROPOSAL,
        "display_name": "Body proposal placeholder",
        "capability": "body_detection",
        "runtime": "placeholder",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {},
        "output_schema_version": "body-box-v1",
        "status": "ready",
    },
    {
        "model_id": BODY_REFINE,
        "display_name": "Body refine placeholder",
        "capability": "body_detection",
        "runtime": "placeholder",
        "latency_class": "bulk",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {},
        "output_schema_version": "body-box-v1",
        "status": "ready",
    },
    {
        "model_id": FACE_YOLO,
        "display_name": "Face YOLO (open-source ONNX)",
        "capability": "face_detection",
        "runtime": "onnx",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {"confidence": 0.25, "imgsz": 640},
        "output_schema_version": "face-box-v1",
        "status": "ready",
    },
    {
        "model_id": BODY_YOLO,
        "display_name": "Body YOLO-person (open-source ONNX)",
        "capability": "body_detection",
        "runtime": "onnx",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {"confidence": 0.25, "imgsz": 640, "class_ids": [0]},
        "output_schema_version": "body-box-v1",
        "status": "ready",
    },
    {
        "model_id": BODY_YOLO_POSE,
        "display_name": "Body YOLO-pose (open-source ONNX)",
        "capability": "body_detection",
        "runtime": "onnx_pose",
        "latency_class": "instant",
        "compatible_paths": ["instant", "bulk"],
        "hyperparameters": {"confidence": 0.25, "imgsz": 640},
        "output_schema_version": "body-pose-v1",
        "status": "ready",
    },
]

FACE_RECIPES = [
    {
        "recipe_id": RECIPE_HAAR_ONLY,
        "display_name": "Face Haar only (single)",
        "capability": "face_detection",
        "kind": "single",
        "steps": [("single", BUILTIN_HAAR, DEFAULT_VERSION)],
    },
    {
        "recipe_id": RECIPE_DLIB_ONLY,
        "display_name": "Face Dlib only (single)",
        "capability": "face_detection",
        "kind": "single",
        "steps": [("single", BUILTIN_DLIB, DEFAULT_VERSION)],
    },
    {
        "recipe_id": RECIPE_TWO_STAGE,
        "display_name": "Face Haar → Dlib (two-stage)",
        "capability": "face_detection",
        "kind": "two_stage",
        "steps": [
            ("proposal", BUILTIN_HAAR, DEFAULT_VERSION),
            ("refine", BUILTIN_DLIB, DEFAULT_VERSION),
        ],
    },
    {
        "recipe_id": RECIPE_FACE_YOLO,
        "display_name": "Face YOLO ONNX (single)",
        "capability": "face_detection",
        "kind": "single",
        "steps": [("single", FACE_YOLO, DEFAULT_VERSION)],
    },
]

BODY_RECIPES = [
    {
        "recipe_id": RECIPE_BODY_SINGLE,
        "display_name": "Body single placeholder",
        "capability": "body_detection",
        "kind": "single",
        "steps": [("single", BODY_PROPOSAL, DEFAULT_VERSION)],
    },
    {
        "recipe_id": RECIPE_BODY_TWO_STAGE,
        "display_name": "Body two-stage placeholder",
        "capability": "body_detection",
        "kind": "two_stage",
        "steps": [
            ("proposal", BODY_PROPOSAL, DEFAULT_VERSION),
            ("refine", BODY_REFINE, DEFAULT_VERSION),
        ],
    },
    {
        "recipe_id": RECIPE_BODY_YOLO,
        "display_name": "Body YOLO-person (single)",
        "capability": "body_detection",
        "kind": "single",
        "steps": [("single", BODY_YOLO, DEFAULT_VERSION)],
    },
    {
        "recipe_id": RECIPE_BODY_YOLO_POSE,
        "display_name": "Body YOLO-pose (single)",
        "capability": "body_detection",
        "kind": "single",
        "steps": [("single", BODY_YOLO_POSE, DEFAULT_VERSION)],
    },
]


def seed_builtins(db: Session) -> None:
    for spec in BUILTINS:
        row = db.get(MvModel, spec["model_id"])
        if row is None:
            row = MvModel(
                model_id=spec["model_id"],
                display_name=spec["display_name"],
                capability=spec["capability"],
                origin="builtin",
            )
            db.add(row)
        existing = (
            db.query(MvModelVersion)
            .filter_by(model_id=spec["model_id"], version=DEFAULT_VERSION)
            .one_or_none()
        )
        if existing is None:
            db.add(
                MvModelVersion(
                    model_id=spec["model_id"],
                    version=DEFAULT_VERSION,
                    runtime=spec["runtime"],
                    output_schema_version=spec.get("output_schema_version", "face-box-v1"),
                    latency_class=spec["latency_class"],
                    compatible_paths=spec["compatible_paths"],
                    hyperparameters=spec["hyperparameters"],
                    status=spec.get("status", "ready"),
                )
            )

    for recipe_spec in FACE_RECIPES + BODY_RECIPES:
        _ensure_recipe(db, recipe_spec)

    golden = db.query(MvGoldenSet).filter_by(set_id="face-platform-default").one_or_none()
    if golden is None:
        db.add(
            MvGoldenSet(
                set_id="face-platform-default",
                display_name="Platform face golden set",
                capability="face_detection",
                scope="platform",
                site_id="",
            )
        )
        db.add(
            MvGoldenItem(
                set_id="face-platform-default",
                media_uri="builtin://synthetic-face-frame",
                baseline_boxes=[[100, 100, 200, 200]],
                frame_number=0,
                notes="Synthetic baseline for local validate smoke",
            )
        )

    # Prefer recipe-based platform defaults when creating fresh assignments.
    defaults = [
        ("face_detection", "platform", "", "instant", "", "", RECIPE_TWO_STAGE),
        ("face_detection", "platform", "", "bulk", "", "", RECIPE_TWO_STAGE),
        ("face_detection", "platform", "", "preview", "", "", RECIPE_HAAR_ONLY),
        ("face_landmarks", "platform", "", "bulk", BUILTIN_LANDMARKS, DEFAULT_VERSION, ""),
    ]
    for capability, scope_type, scope_id, path, model_id, version, recipe_id in defaults:
        found = (
            db.query(MvAssignment)
            .filter_by(
                capability=capability,
                scope_type=scope_type,
                scope_id=scope_id,
                path=path,
            )
            .one_or_none()
        )
        if found is None:
            db.add(
                MvAssignment(
                    capability=capability,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    path=path,
                    model_id=model_id,
                    version=version,
                    recipe_id=recipe_id,
                    shadow=False,
                )
            )
        elif not getattr(found, "recipe_id", "") and found.model_id in BUILTIN_TO_RECIPE:
            # Migrate Phase A model-only platform rows to recipes when safe.
            if found.scope_type == "platform" and found.scope_id == "":
                found.recipe_id = BUILTIN_TO_RECIPE[found.model_id]
                found.model_id = ""
                found.version = ""
    _attach_yolo_artifacts_if_present(db)
    db.commit()


def _attach_yolo_artifacts_if_present(db: Session) -> None:
    """Register ONNX files under artifact_store/{model_id}/1.0.0/*.onnx if present."""
    from pathlib import Path

    from config import config

    for model_id in (FACE_YOLO, BODY_YOLO, BODY_YOLO_POSE):
        existing = (
            db.query(MvArtifact)
            .filter_by(model_id=model_id, version=DEFAULT_VERSION)
            .first()
        )
        if existing is not None:
            continue
        folder = config.ARTIFACT_ROOT / model_id / DEFAULT_VERSION
        if not folder.is_dir():
            continue
        files = sorted(folder.glob("*.onnx"))
        if not files:
            continue
        path = files[0]
        data = path.read_bytes()
        import hashlib

        digest = hashlib.sha256(data).hexdigest()
        db.add(
            MvArtifact(
                model_id=model_id,
                version=DEFAULT_VERSION,
                filename=path.name,
                sha256=digest,
                size_bytes=len(data),
                uri=str(path.resolve()),
                content_type="application/octet-stream",
            )
        )
        version_row = (
            db.query(MvModelVersion)
            .filter_by(model_id=model_id, version=DEFAULT_VERSION)
            .one_or_none()
        )
        if version_row is not None:
            version_row.status = "ready"


def _ensure_recipe(db: Session, spec: dict) -> None:
    row = db.get(MvRecipe, spec["recipe_id"])
    if row is None:
        row = MvRecipe(
            recipe_id=spec["recipe_id"],
            display_name=spec["display_name"],
            capability=spec["capability"],
            kind=spec["kind"],
            status="ready",
        )
        db.add(row)
        db.flush()
    else:
        row.display_name = spec["display_name"]
        row.kind = spec["kind"]
        row.capability = spec["capability"]

    existing_steps = (
        db.query(MvRecipeStep).filter_by(recipe_id=spec["recipe_id"]).all()
    )
    if existing_steps:
        return
    for order, (role, model_id, version) in enumerate(spec["steps"]):
        db.add(
            MvRecipeStep(
                recipe_id=spec["recipe_id"],
                step_order=order,
                role=role,
                model_id=model_id,
                version=version,
            )
        )


def _match(
    db: Session, capability: str, scope_type: str, scope_id: str, path: str
) -> MvAssignment | None:
    return (
        db.query(MvAssignment)
        .filter_by(
            capability=capability,
            scope_type=scope_type,
            scope_id=scope_id or "",
            path=path,
        )
        .one_or_none()
    )


def _stage_from_version(version_row: MvModelVersion | None, role: str, model_id: str, version: str) -> dict:
    return {
        "role": role,
        "model_id": model_id,
        "version": version,
        "runtime": version_row.runtime if version_row else "unknown",
        "hyperparameters": version_row.hyperparameters if version_row else {},
        "latency_class": version_row.latency_class if version_row else "instant",
        "compatible_paths": version_row.compatible_paths if version_row else [],
    }


def _expand_recipe(db: Session, recipe: MvRecipe) -> tuple[str, list[dict], dict]:
    steps = (
        db.query(MvRecipeStep)
        .filter_by(recipe_id=recipe.recipe_id)
        .order_by(MvRecipeStep.step_order)
        .all()
    )
    stages: list[dict] = []
    for step in steps:
        version_row = (
            db.query(MvModelVersion)
            .filter_by(model_id=step.model_id, version=step.version)
            .one_or_none()
        )
        stages.append(
            _stage_from_version(version_row, step.role, step.model_id, step.version)
        )

    kind = recipe.kind
    # Legacy summary fields for Cameras/Orchestrator method= mapping.
    if kind == "two_stage" and len(stages) >= 2:
        legacy_model_id = BUILTIN_TWO_STAGE
        legacy_runtime = "two_stage"
        legacy_version = DEFAULT_VERSION
        hyper = stages[0].get("hyperparameters") or {}
        latency = "instant"
        paths = ["instant", "bulk"]
    elif stages:
        legacy_model_id = stages[0]["model_id"]
        legacy_runtime = stages[0]["runtime"]
        legacy_version = stages[0]["version"]
        hyper = stages[0].get("hyperparameters") or {}
        latency = stages[0].get("latency_class") or "instant"
        paths = stages[0].get("compatible_paths") or []
    else:
        legacy_model_id = BUILTIN_TWO_STAGE
        legacy_runtime = "two_stage"
        legacy_version = DEFAULT_VERSION
        hyper = {}
        latency = "instant"
        paths = ["instant", "bulk"]

    legacy = {
        "model_id": legacy_model_id,
        "version": legacy_version,
        "runtime": legacy_runtime,
        "hyperparameters": hyper,
        "latency_class": latency,
        "compatible_paths": paths,
    }
    return kind, stages, legacy


def _expand_model(db: Session, model_id: str, version: str) -> tuple[str, list[dict], dict]:
    # Prefer known builtin → recipe expansion so Vision gets explicit stages.
    mapped = BUILTIN_TO_RECIPE.get(model_id)
    if mapped:
        recipe = db.get(MvRecipe, mapped)
        if recipe is not None:
            return _expand_recipe(db, recipe)

    version_row = (
        db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    )
    role = "single"
    stages = [_stage_from_version(version_row, role, model_id, version)]
    legacy = {
        "model_id": model_id,
        "version": version,
        "runtime": version_row.runtime if version_row else "unknown",
        "hyperparameters": version_row.hyperparameters if version_row else {},
        "latency_class": version_row.latency_class if version_row else "instant",
        "compatible_paths": version_row.compatible_paths if version_row else [],
    }
    return "single", stages, legacy


def resolve_assignment(
    db: Session,
    *,
    capability: str,
    path: str,
    camera_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    candidates = []
    if camera_id:
        candidates.append(("camera", camera_id, path))
    if tenant_id:
        candidates.append(("tenant", tenant_id, path))
    candidates.append(("platform", "", path))

    assignment = None
    for scope_type, scope_id, p in candidates:
        assignment = _match(db, capability, scope_type, scope_id, p)
        if assignment:
            break

    if assignment is None:
        assignment = MvAssignment(
            capability=capability,
            scope_type="platform",
            scope_id="",
            path=path,
            model_id="" if capability == "face_detection" else BUILTIN_LANDMARKS,
            version="" if capability == "face_detection" else DEFAULT_VERSION,
            recipe_id=RECIPE_TWO_STAGE if capability == "face_detection" else "",
            shadow=False,
        )

    recipe_id = (getattr(assignment, "recipe_id", None) or "").strip()
    if recipe_id:
        recipe = db.get(MvRecipe, recipe_id)
        if recipe is None:
            raise KeyError("unknown_recipe")
        kind, stages, legacy = _expand_recipe(db, recipe)
    else:
        kind, stages, legacy = _expand_model(db, assignment.model_id, assignment.version)
        recipe_id = BUILTIN_TO_RECIPE.get(assignment.model_id, "")

    return {
        "capability": capability,
        "path": path,
        "kind": kind,
        "recipe_id": recipe_id or None,
        "stages": stages,
        "model_id": legacy["model_id"],
        "version": legacy["version"],
        "runtime": legacy["runtime"],
        "compatible_paths": legacy["compatible_paths"],
        "latency_class": legacy["latency_class"],
        "hyperparameters": legacy["hyperparameters"],
        "shadow": bool(assignment.shadow),
        "serving": not bool(assignment.shadow),
        "scope_type": assignment.scope_type,
        "fallback": assignment.scope_type == "platform"
        and (recipe_id == RECIPE_TWO_STAGE or assignment.model_id == BUILTIN_TWO_STAGE),
    }


def list_catalog(db: Session) -> list[dict]:
    from models import MvArtifact

    items = []
    for model in db.query(MvModel).order_by(MvModel.model_id).all():
        versions = (
            db.query(MvModelVersion)
            .filter_by(model_id=model.model_id)
            .order_by(MvModelVersion.version)
            .all()
        )
        version_payload = []
        for v in versions:
            arts = (
                db.query(MvArtifact)
                .filter_by(model_id=model.model_id, version=v.version)
                .all()
            )
            version_payload.append(
                {
                    "version": v.version,
                    "runtime": v.runtime,
                    "latency_class": v.latency_class,
                    "compatible_paths": v.compatible_paths,
                    "status": v.status,
                    "hyperparameters": v.hyperparameters,
                    "artifacts": [
                        {
                            "filename": a.filename,
                            "sha256": a.sha256,
                            "size_bytes": a.size_bytes,
                            "uri": a.uri,
                            "content_type": a.content_type,
                        }
                        for a in arts
                    ],
                }
            )
        items.append(
            {
                "model_id": model.model_id,
                "display_name": model.display_name,
                "capability": model.capability,
                "origin": model.origin,
                "versions": version_payload,
            }
        )
    return items


def list_assignments(db: Session) -> list[dict]:
    rows = db.query(MvAssignment).order_by(MvAssignment.capability, MvAssignment.path).all()
    return [
        {
            "capability": r.capability,
            "scope_type": r.scope_type,
            "scope_id": r.scope_id,
            "path": r.path,
            "model_id": r.model_id or None,
            "version": r.version or None,
            "recipe_id": (getattr(r, "recipe_id", None) or None) or None,
            "shadow": r.shadow,
        }
        for r in rows
    ]


def list_recipes(db: Session, capability: str | None = None) -> list[dict]:
    query = db.query(MvRecipe).order_by(MvRecipe.capability, MvRecipe.recipe_id)
    if capability:
        query = query.filter_by(capability=capability)
    out = []
    for recipe in query.all():
        kind, stages, _legacy = _expand_recipe(db, recipe)
        out.append(
            {
                "recipe_id": recipe.recipe_id,
                "display_name": recipe.display_name,
                "capability": recipe.capability,
                "kind": kind,
                "status": recipe.status,
                "stages": stages,
            }
        )
    return out


def _normalize_recipe_steps(kind: str, steps: list[dict]) -> list[dict]:
    if kind not in ("single", "two_stage"):
        raise ValueError("invalid_kind")
    if kind == "single":
        if len(steps) != 1 or steps[0].get("role") not in ("single", None):
            raise ValueError("single_requires_one_step")
        return [{**steps[0], "role": "single"}]
    roles = [s.get("role") for s in steps]
    if roles != ["proposal", "refine"]:
        raise ValueError("two_stage_requires_proposal_refine")
    return steps


def create_recipe(
    db: Session,
    *,
    recipe_id: str,
    display_name: str,
    capability: str,
    kind: str,
    steps: list[dict],
) -> dict:
    if db.get(MvRecipe, recipe_id) is not None:
        raise ValueError("recipe_exists")
    steps = _normalize_recipe_steps(kind, steps)

    db.add(
        MvRecipe(
            recipe_id=recipe_id,
            display_name=display_name,
            capability=capability,
            kind=kind,
            status="ready",
        )
    )
    for order, step in enumerate(steps):
        version_row = (
            db.query(MvModelVersion)
            .filter_by(model_id=step["model_id"], version=step["version"])
            .one_or_none()
        )
        if version_row is None:
            raise KeyError("unknown_version")
        if version_row.runtime == "onnx":
            # Stored but not loadable yet — still allow recipe composition for catalog.
            pass
        db.add(
            MvRecipeStep(
                recipe_id=recipe_id,
                step_order=order,
                role=step["role"],
                model_id=step["model_id"],
                version=step["version"],
            )
        )
    db.commit()
    recipe = db.get(MvRecipe, recipe_id)
    kind, stages, _ = _expand_recipe(db, recipe)
    return {
        "recipe_id": recipe_id,
        "display_name": display_name,
        "capability": capability,
        "kind": kind,
        "status": "ready",
        "stages": stages,
    }


def ensure_recipe(
    db: Session,
    *,
    recipe_id: str,
    display_name: str,
    capability: str,
    kind: str,
    steps: list[dict],
) -> dict:
    """Create or replace a recipe's kind/steps (for per-camera compositions)."""
    steps = _normalize_recipe_steps(kind, steps)
    for step in steps:
        version_row = (
            db.query(MvModelVersion)
            .filter_by(model_id=step["model_id"], version=step["version"])
            .one_or_none()
        )
        if version_row is None:
            raise KeyError("unknown_version")

    existing = db.get(MvRecipe, recipe_id)
    if existing is None:
        return create_recipe(
            db,
            recipe_id=recipe_id,
            display_name=display_name,
            capability=capability,
            kind=kind,
            steps=steps,
        )

    if existing.capability != capability:
        raise ValueError("capability_mismatch")
    existing.display_name = display_name
    existing.kind = kind
    existing.status = "ready"
    db.query(MvRecipeStep).filter_by(recipe_id=recipe_id).delete()
    for order, step in enumerate(steps):
        db.add(
            MvRecipeStep(
                recipe_id=recipe_id,
                step_order=order,
                role=step["role"],
                model_id=step["model_id"],
                version=step["version"],
            )
        )
    db.commit()
    recipe = db.get(MvRecipe, recipe_id)
    kind_out, stages, _ = _expand_recipe(db, recipe)
    return {
        "recipe_id": recipe_id,
        "display_name": display_name,
        "capability": capability,
        "kind": kind_out,
        "status": "ready",
        "stages": stages,
    }


def _upsert_assignment(
    db: Session,
    *,
    capability: str,
    scope_type: str,
    scope_id: str,
    path: str,
    model_id: str,
    version: str,
    recipe_id: str,
    shadow: bool,
    actor: str,
) -> dict:
    existing = _match(db, capability, scope_type, scope_id or "", path)
    if existing:
        db.add(
            MvAssignmentHistory(
                capability=capability,
                scope_type=scope_type,
                scope_id=scope_id or "",
                path=path,
                model_id=existing.model_id or "",
                version=existing.version or "",
                recipe_id=getattr(existing, "recipe_id", "") or "",
                actor=actor,
            )
        )
        existing.model_id = model_id
        existing.version = version
        existing.recipe_id = recipe_id
        existing.shadow = shadow
    else:
        db.add(
            MvAssignment(
                capability=capability,
                scope_type=scope_type,
                scope_id=scope_id or "",
                path=path,
                model_id=model_id,
                version=version,
                recipe_id=recipe_id,
                shadow=shadow,
            )
        )
    db.commit()
    return resolve_assignment(
        db,
        capability=capability,
        path=path,
        camera_id=scope_id if scope_type == "camera" else None,
    )


def activate_version(
    db: Session,
    *,
    model_id: str,
    version: str,
    capability: str,
    scope_type: str,
    scope_id: str,
    path: str,
    shadow: bool,
    actor: str,
) -> dict:
    version_row = (
        db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    )
    if version_row is None:
        raise KeyError("unknown_version")
    model = db.get(MvModel, model_id)
    if model is None:
        raise KeyError("unknown_model")
    if path not in (version_row.compatible_paths or []):
        raise ValueError("incompatible_path")
    if model.origin == "user" and version_row.status not in ("ready", "active"):
        raise ValueError("version_not_ready")
    if version_row.runtime == "onnx" and model.origin == "user" and version_row.status not in (
        "ready",
        "active",
    ):
        raise ValueError("version_not_ready")
    if model.capability == "body_detection" and model.origin != "builtin":
        # Body custom still gated at API layer; builtins placeholders ok.
        pass

    recipe_id = BUILTIN_TO_RECIPE.get(model_id, "")
    if recipe_id:
        return _upsert_assignment(
            db,
            capability=capability,
            scope_type=scope_type,
            scope_id=scope_id,
            path=path,
            model_id="",
            version="",
            recipe_id=recipe_id,
            shadow=shadow,
            actor=actor,
        )

    return _upsert_assignment(
        db,
        capability=capability,
        scope_type=scope_type,
        scope_id=scope_id,
        path=path,
        model_id=model_id,
        version=version,
        recipe_id="",
        shadow=shadow,
        actor=actor,
    )


# Back-compat alias
def activate_builtin(**kwargs):
    return activate_version(**kwargs)


def activate_recipe(
    db: Session,
    *,
    recipe_id: str,
    capability: str,
    scope_type: str,
    scope_id: str,
    path: str,
    shadow: bool,
    actor: str,
) -> dict:
    recipe = db.get(MvRecipe, recipe_id)
    if recipe is None:
        raise KeyError("unknown_recipe")
    if recipe.capability != capability:
        raise ValueError("capability_mismatch")
    kind, stages, legacy = _expand_recipe(db, recipe)
    paths = legacy.get("compatible_paths") or []
    # Two-stage face recipe is compatible with instant/bulk.
    if kind == "two_stage" and not paths:
        paths = ["instant", "bulk"]
    if path == "preview" and kind == "two_stage":
        raise ValueError("incompatible_path")
    if paths and path not in paths and kind == "single":
        if path not in (stages[0].get("compatible_paths") or []):
            raise ValueError("incompatible_path")
    for stage in stages:
        if stage.get("runtime") == "onnx":
            # ONNX is loadable when artifact is present; Vision fails soft if missing.
            continue
        if stage.get("runtime") == "placeholder" and capability == "body_detection":
            # Allow assignment of body stubs; Vision no-ops until Phase C.
            continue

    return _upsert_assignment(
        db,
        capability=capability,
        scope_type=scope_type,
        scope_id=scope_id,
        path=path,
        model_id="",
        version="",
        recipe_id=recipe_id,
        shadow=shadow,
        actor=actor,
    )


def deactivate_assignment(
    db: Session,
    *,
    capability: str,
    scope_type: str,
    scope_id: str,
    path: str,
    actor: str,
) -> dict:
    existing = _match(db, capability, scope_type, scope_id or "", path)
    if existing is None:
        raise KeyError("no_assignment")
    if existing.scope_type == "platform" and existing.scope_id == "":
        raise PermissionError("cannot_delete_platform_default")
    db.add(
        MvAssignmentHistory(
            capability=capability,
            scope_type=scope_type,
            scope_id=scope_id or "",
            path=path,
            model_id=existing.model_id or "",
            version=existing.version or "",
            recipe_id=getattr(existing, "recipe_id", "") or "",
            actor=actor,
        )
    )
    db.delete(existing)
    db.commit()
    return resolve_assignment(db, capability=capability, path=path)


def create_user_model(
    db: Session,
    *,
    model_id: str,
    display_name: str,
    capability: str = "face_detection",
) -> dict:
    if db.get(MvModel, model_id) is not None:
        raise ValueError("model_exists")
    db.add(
        MvModel(
            model_id=model_id,
            display_name=display_name,
            capability=capability,
            origin="user",
        )
    )
    db.commit()
    return {
        "model_id": model_id,
        "display_name": display_name,
        "capability": capability,
        "origin": "user",
        "versions": [],
    }


def create_user_version(
    db: Session,
    *,
    model_id: str,
    version: str,
    runtime: str,
    latency_class: str,
    compatible_paths: list[str],
    hyperparameters: dict | None = None,
    artifact: dict,
) -> dict:
    from models import MvArtifact

    model = db.get(MvModel, model_id)
    if model is None:
        raise KeyError("unknown_model")
    if model.origin == "builtin":
        raise PermissionError("cannot_upload_builtin")
    if runtime not in ("haar", "onnx", "dlib_hog", "dlib_68"):
        raise ValueError("unknown_runtime")
    existing = (
        db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    )
    if existing is not None:
        raise ValueError("version_exists")

    status = "uploaded"
    db.add(
        MvModelVersion(
            model_id=model_id,
            version=version,
            runtime=runtime,
            output_schema_version="face-box-v1"
            if model.capability == "face_detection"
            else "body-box-v1",
            latency_class=latency_class,
            compatible_paths=compatible_paths,
            hyperparameters=hyperparameters or {},
            status=status,
        )
    )
    db.add(
        MvArtifact(
            model_id=model_id,
            version=version,
            filename=artifact["filename"],
            sha256=artifact["sha256"],
            size_bytes=artifact["size_bytes"],
            uri=artifact["uri"],
            content_type=artifact["content_type"],
        )
    )
    db.commit()
    return {
        "model_id": model_id,
        "version": version,
        "runtime": runtime,
        "status": status,
        "latency_class": latency_class,
        "compatible_paths": compatible_paths,
        "artifact": artifact,
    }


def archive_version(db: Session, *, model_id: str, version: str) -> dict:
    row = db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    if row is None:
        raise KeyError("unknown_version")
    model = db.get(MvModel, model_id)
    if model and model.origin == "builtin":
        raise PermissionError("cannot_archive_builtin")
    # Serving assignments block archive.
    serving = (
        db.query(MvAssignment)
        .filter(
            ((MvAssignment.model_id == model_id) & (MvAssignment.version == version))
            | (MvAssignment.recipe_id != "")
        )
        .all()
    )
    for assignment in serving:
        if assignment.model_id == model_id and assignment.version == version:
            raise ValueError("version_in_use")
        if assignment.recipe_id:
            steps = (
                db.query(MvRecipeStep)
                .filter_by(recipe_id=assignment.recipe_id, model_id=model_id, version=version)
                .count()
            )
            if steps:
                raise ValueError("version_in_use")
    row.status = "archived"
    db.commit()
    return {"model_id": model_id, "version": version, "status": "archived"}


def delete_version(db: Session, *, model_id: str, version: str) -> dict:
    row = db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    if row is None:
        raise KeyError("unknown_version")
    model = db.get(MvModel, model_id)
    if model and model.origin == "builtin":
        raise PermissionError("cannot_delete_builtin")
    if row.status not in ("archived", "failed", "uploaded"):
        raise ValueError("must_archive_first")
    # Caller must check Vision provenance references (409).
    from models import MvArtifact

    arts = db.query(MvArtifact).filter_by(model_id=model_id, version=version).all()
    for art in arts:
        db.delete(art)
    db.delete(row)
    db.commit()
    return {"model_id": model_id, "version": version, "deleted": True}


def record_validation_run(
    db: Session,
    *,
    model_id: str,
    version: str,
    status: str,
    mean_iou: float,
    p95_latency_ms: float,
    details: dict,
    golden_set_id: str = "face-platform-default",
) -> dict:
    row = MvValidationRun(
        model_id=model_id,
        version=version,
        golden_set_id=golden_set_id,
        status=status,
        mean_iou=mean_iou,
        p95_latency_ms=p95_latency_ms,
        details=details,
    )
    db.add(row)
    version_row = (
        db.query(MvModelVersion).filter_by(model_id=model_id, version=version).one_or_none()
    )
    if version_row is not None:
        version_row.status = "ready" if status == "ready" else "failed"
    db.commit()
    return {
        "id": row.id,
        "model_id": model_id,
        "version": version,
        "status": status,
        "mean_iou": mean_iou,
        "p95_latency_ms": p95_latency_ms,
        "details": details,
    }


def list_golden_sets(db: Session) -> list[dict]:
    rows = db.query(MvGoldenSet).order_by(MvGoldenSet.set_id).all()
    out = []
    for g in rows:
        items = db.query(MvGoldenItem).filter_by(set_id=g.set_id).all()
        out.append(
            {
                "set_id": g.set_id,
                "display_name": g.display_name,
                "capability": g.capability,
                "scope": g.scope,
                "site_id": g.site_id,
                "items": [
                    {
                        "id": i.id,
                        "media_uri": i.media_uri,
                        "baseline_boxes": i.baseline_boxes,
                        "frame_number": i.frame_number,
                        "notes": i.notes,
                    }
                    for i in items
                ],
            }
        )
    return out


def list_validation_runs(db: Session, model_id: str, version: str) -> list[dict]:
    rows = (
        db.query(MvValidationRun)
        .filter_by(model_id=model_id, version=version)
        .order_by(MvValidationRun.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "mean_iou": r.mean_iou,
            "p95_latency_ms": r.p95_latency_ms,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
