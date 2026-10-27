"""Compile proprietary Mini modules to native extensions and verify/strip sources.

Extension names are import paths (`core.face_detection`), not on-disk `src/...`
paths. With `package_dir={"": "src"}`, `build_ext --inplace` writes `*.so` next
to the original `.py` under `src/`, which the runtime image copies.

Plain Python kept for the FastAPI shell: `main.py`, `api/`, and package
`__init__.py` / schema modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup

PROTECTED = [
    "core.face_detection",
    "core.face_grouping",
    "core.visualization",
    "services.temp_storage",
    "services.video_preprocessor",
    "services.usb_camera_manager",
    "services.enhanced_camera_manager",
]

SRC = Path("src")


def _module_py(mod: str) -> Path:
    return SRC / f"{mod.replace('.', '/')}.py"


def extension_for(mod: str) -> Extension:
    rel = _module_py(mod)
    if not rel.is_file():
        raise FileNotFoundError(rel)
    return Extension(name=mod, sources=[str(rel)])


def verify_protected_so(root: Path = SRC) -> list[str]:
    missing: list[str] = []
    found: list[str] = []
    for mod in PROTECTED:
        stem = mod.rsplit(".", 1)[-1]
        parent = (root / mod.replace(".", "/")).parent
        hits = sorted(parent.glob(f"{stem}*.so")) if parent.is_dir() else []
        if not hits:
            missing.append(mod)
        else:
            found.extend(str(path) for path in hits)
    if missing:
        raise SystemExit(f"protected .so missing for {missing}")
    print("protected so ok:", ", ".join(found))
    return found


def strip_protected_py(root: Path = SRC) -> None:
    """Remove .py sources only after matching .so files are present."""
    verify_protected_so(root)
    removed: list[str] = []
    for mod in PROTECTED:
        py = root / f"{mod.replace('.', '/')}.py"
        if py.is_file():
            py.unlink()
            removed.append(str(py))
    print("stripped py:", ", ".join(removed) if removed else "(none)")


def smoke_import_protected() -> None:
    """Import protected modules from .so (no .py fallback)."""
    sys.path.insert(0, str(SRC.resolve()))
    for mod in PROTECTED:
        __import__(mod)
        print(f"import ok: {mod}")


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["verify"]:
        verify_protected_so()
        raise SystemExit(0)
    if cmd == ["strip"]:
        strip_protected_py()
        raise SystemExit(0)
    if cmd == ["smoke"]:
        smoke_import_protected()
        raise SystemExit(0)

from Cython.Build import cythonize  # noqa: E402

setup(
    name="ppl-meta-mini-protected",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=cythonize(
        [extension_for(mod) for mod in PROTECTED],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
            "embedsignature": True,
        },
    ),
)
