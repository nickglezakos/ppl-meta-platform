# Vision And vmeta Source Protection Plan

**Date**: May 12, 2026  
**Status**: Draft  
**Scope**: Practical source-protection approach for `ppl-meta-vision` and `ppl-meta-vmeta` when shipping Docker images to customer-controlled environments

---

## Purpose

This document defines a realistic protection strategy for the two services that contain the most sensitive proprietary logic in the first packaging batch:

- `ppl-meta-vision`
- `ppl-meta-vmeta`

The goal is to make image-based delivery possible while reducing direct access to the underlying Python implementation.

This is an IP-hardening plan, not a claim of full secrecy.

---

## Important Constraint

If a customer can run a Docker image, they have the executable artifact.

That means:

- plain Python source inside the image is directly recoverable
- compiled native extensions are harder to inspect, but still reversible with enough effort
- obfuscation only raises effort; it does not provide strong cryptographic protection

The correct goal for this phase is therefore:

- make source extraction materially harder for shipped services
- avoid shipping the most sensitive logic as plain `.py` files
- keep truly business-critical logic off customer-hosted images where possible

---

## Recommended Protection Model

For both services, use a split model.

### Keep As Plain Python

Keep the following in plain Python for maintainability and operational clarity:

- FastAPI entrypoints
- route registration
- startup and dependency wiring
- health endpoints
- basic configuration loading
- integration glue that is not proprietary by itself

### Compile With Cython

Compile the proprietary processing and decision logic into native extension modules and ship only the compiled artifacts in the final runtime image.

This should be done with:

- Cython compilation to `.so`
- multi-stage Docker builds
- deletion of original `.py` files for protected modules from the runtime stage
- optional symbol stripping in the builder stage where practical

### Do Not Ship If It Must Stay Secret

If a module would create unacceptable IP exposure when reverse engineered, that module should not be shipped at all. It should move behind a private service boundary under operator control.

---

## Vision Protection Boundary

### Vision Modules To Keep In Plain Python

- `src/main.py`
- API/request-response shells
- service registration and startup code
- non-sensitive config and logging glue

### Vision First Modules To Compile

These modules are the best first protection targets because they are likely to contain the valuable processing logic while staying reasonably isolated from framework glue:

- `src/extracted_face_detector.py`
- `src/distance_calculator.py`
- `src/media_processor.py`
- `src/person_objects/face_grouping_engine.py`

### Why The Vision Split Works

`ppl-meta-vision` has a relatively heavy runtime shell and external-library surface. Compiling the whole service would increase build fragility without adding much protection to the public-facing API layer.

Compiling the detection, distance, media, and grouping internals protects the algorithmic core while preserving a debuggable shell.

---

## vmeta Protection Boundary

### vmeta Modules To Keep In Plain Python

- `src/main.py`
- API routers
- lifecycle wiring
- database bootstrapping glue
- non-sensitive orchestration glue

### vmeta First Modules To Compile

These modules are strong initial candidates because they likely encode the proprietary matching, embedding, ranking, and merge behavior:

- `src/services/embedding_service.py`
- `src/services/workflow_service.py`
- `src/services/mvr_service.py`
- `src/services/hierarchical_mvr_merger.py`
- `src/services/quality_selector.py`

### Why The vmeta Split Works

`ppl-meta-vmeta` already has a thin entry shell with most value concentrated in the service layer. That makes it a better fit for selective compilation than full-service compilation.

---

## Packaging Pattern

The recommended packaging pattern for both services is:

1. install build dependencies in a builder image
2. compile selected modules with Cython
3. copy the service into a runtime image
4. delete original `.py` files for the protected modules in the runtime image
5. keep entrypoints and non-sensitive glue as plain Python

This preserves the current deployment model while reducing exposure.

---

## Docker Output Rule

For protected images:

- do copy compiled extension modules into the final image
- do keep package directories and `__init__.py` where import resolution requires them
- do not copy the original `.py` for protected modules into the final image
- do not treat this as complete source secrecy

---

## Operational Tradeoffs

### Benefits

- raises the effort required to inspect shipped code
- preserves current deployment boundaries
- allows incremental rollout on a module-by-module basis
- avoids destabilizing the whole service during the first packaging pass

### Costs

- more complex builds
- native compilation requirements
- harder debugging for protected modules
- some imports may need small refactors to compile cleanly
- no guarantee against reverse engineering

---

## Recommended First Implementation

### Phase 1

Protect only the first-pass modules listed above for `vision` and `vmeta`.

### Phase 2

Run integration and health checks against the protected images.

### Phase 3

Only after the selective-compilation path is stable, consider whether additional modules should move into the protected set.

---

## Recommended Conclusion

The right first move is not to try to hide all Python from `ppl-meta-vision` and `ppl-meta-vmeta`.

The right first move is to:

- keep the service shell readable and maintainable
- compile the proprietary processing modules with Cython
- ship only compiled artifacts for those protected modules in the final Docker image
- move any truly non-distributable logic behind a private service boundary instead of packaging it

That gives a practical first protection layer without pretending Docker image delivery can provide perfect source secrecy.
