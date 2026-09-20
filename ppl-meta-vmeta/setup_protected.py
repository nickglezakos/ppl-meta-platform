"""Compile selected vmeta modules to native extensions.

Extension *names* must be the import paths (`services.mvr_service`), not the
on-disk `src/...` paths. Combined with `package_dir={"": "src"}`,
`build_ext --inplace` then writes `*.so` next to the original `.py` files
under `src/services/`, which is what the runtime image copies.
"""

from __future__ import annotations

import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup

PROTECTED = [
    "services.embedding_service",
    "services.workflow_service",
    "services.mvr_service",
    "services.hierarchical_mvr_merger",
    "services.quality_selector",
]

SRC = Path("src")


def extension_for(mod: str) -> Extension:
    rel = SRC / f"{mod.replace('.', '/')}.py"
    if not rel.is_file():
        raise FileNotFoundError(rel)
    return Extension(name=mod, sources=[str(rel)])


def verify_protected_so(root: Path = SRC) -> None:
    services = root / "services"
    missing: list[str] = []
    found: list[str] = []
    for mod in PROTECTED:
        stem = mod.rsplit(".", 1)[-1]
        hits = sorted(services.glob(f"{stem}*.so")) if services.is_dir() else []
        if not hits:
            missing.append(mod)
        else:
            found.extend(str(path) for path in hits)
    if missing:
        listing = (
            ", ".join(sorted(p.name for p in services.iterdir()))
            if services.is_dir()
            else "<missing dir>"
        )
        raise SystemExit(
            f"protected .so missing for {missing}; src/services contains: {listing}"
        )
    print("protected so ok:", ", ".join(found))


if __name__ == "__main__" and sys.argv[1:] == ["verify"]:
    verify_protected_so()
    raise SystemExit(0)

from Cython.Build import cythonize  # noqa: E402

setup(
    name="ppl-meta-vmeta-protected",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=cythonize(
        [extension_for(mod) for mod in PROTECTED],
        compiler_directives={"language_level": "3"},
    ),
)
