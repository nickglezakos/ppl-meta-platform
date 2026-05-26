# Camera Recordings And Media Storage Duplication

## Summary

Local disk usage is being inflated by a duplicate-storage pattern between the Cameras service and the Media service.

- Cameras service stores recorded video segments locally under `ppl-meta-cameras/recordings`
- Cameras service then uploads those same segments to Media service
- Media service writes a second local copy under `ppl-meta-media/media/...`
- Local camera cleanup after successful upload is currently disabled

This means the same video content can exist twice on disk at the same time.

## Measured Impact On This Machine

Measurements taken from the current workspace:

- `ppl-meta-cameras/recordings`: 1376 mp4 files, 5,366,250,234 bytes, about 5.0 GB
- `ppl-meta-media/media`: 852 mp4 files, 4,145,009,421 bytes, about 3.9 GB
- exact duplicate overlap across those two trees by SHA-256: 894 matching file pairs, 3,913,100,352 bytes, about 3.9 GB
- additional media-service storage outside the main `media` tree:
  - `ppl-meta-media/storage/media`: about 641 MB
  - `ppl-meta-media/storage/thumbnails`: about 2.3 MB
  - `ppl-meta-media/thumbnails`: about 33 MB

Interpretation:

- at least about 3.9 GB of video content is duplicated across Cameras and Media local storage
- the duplicate total is already large enough to explain a meaningful part of the storage pressure on this laptop
- the duplicate pair count is higher than the Media file count because repeated recordings with identical content hashes can map to multiple matching files on the Cameras side

## Root Cause

### 1. Cameras writes local recordings first

The Cameras service stores video segments in the local `recordings` directory before upload.

Relevant code:

- `ppl-meta-cameras/src/services/camera_detection.py`
- `ppl-meta-cameras/src/services/recording_service.py`

### 2. Cameras uploads the same bytes to Media

After recording, Cameras uploads the segment to Media using `POST /api/v1/media/upload`.

Relevant code path:

- `ppl-meta-cameras/src/services/camera_detection.py`
- `ppl-meta-cameras/src/services/camera_worker.py`

### 3. Media writes a second local copy

The Media service reads the uploaded bytes and writes them to a new local path under `media/<user>/video/<year>/<month>/...`.

Relevant code path:

- `ppl-meta-media/src/services/media_service.py`

The implementation computes a checksum for deduplication inside Media, but that only avoids duplicate Media records for the same uploaded content and user. It does not remove or reference the original Cameras-side file.

### 4. Cameras cleanup is explicitly disabled

The Cameras upload flow contains commented-out local file deletion after successful upload. The code states that cleanup is disabled because Gateway embedded streaming still needs local files for face detection overlay.

Relevant code path:

- `ppl-meta-cameras/src/services/camera_detection.py`

Current behavior in practice:

- upload succeeds
- media record exists
- local recording file remains on disk
- log message states the local file is preserved for Gateway streaming

## Additional Findings

### Recording session delete does not delete files

The recording-session delete endpoint stops the session but does not remove the underlying recording files from disk.

Relevant code path:

- `ppl-meta-cameras/src/api/v1/endpoints/recording_sessions.py`

### Media and storage are separate directories

`ppl-meta-media/media` and `ppl-meta-media/storage` are separate directories, not symlinks. They should be treated as independent disk consumers.

## Why This Matters

- duplicated video bytes reduce available disk headroom on development machines
- the current pattern likely scales badly on long-running local systems
- retention settings exist in the Cameras domain model, but no active post-upload cleanup path was confirmed for these local recording files
- the system currently mixes two responsibilities:
  - local operational recording/cache needs for Cameras or Gateway
  - canonical retained media library in Media service

## Likely Intended Behavior Vs Current Behavior

Likely intended long-term behavior:

- Cameras records locally only as a transient working buffer or short-lived operational cache
- Media service becomes the retained library of record after upload
- Cameras removes or rotates local segments after successful upload and after downstream consumers no longer need them

Current behavior:

- Cameras acts as both recorder and long-lived local store
- Media also stores retained copies
- no active cleanup path removes the first copy after upload

## Safe Immediate Cleanup Guidance

If the goal is to recover space on this laptop with low risk:

1. Preserve `ppl-meta-media/media` as the safer retained library.
2. Preserve `ppl-meta-media/storage/media` until its ownership is clarified.
3. Consider deleting or archiving older files from `ppl-meta-cameras/recordings` only after confirming no active Gateway or overlay workflow depends on those specific local files.
4. Do not assume session deletion APIs remove local files.

Low-risk order for reclaiming space:

1. old local camera recordings in `ppl-meta-cameras/recordings`
2. obsolete Flutter or Android build outputs elsewhere in the repo
3. stale development virtual environments and generated binaries

## Recommended Engineering Fix

### Short-term

- add an explicit retention or cleanup job for `ppl-meta-cameras/recordings`
- gate cleanup on successful Media upload and any required downstream processing completion
- add visibility in health or admin tooling for local recording-cache size

### Medium-term

- separate these concepts clearly:
  - transient recording cache
  - retained media library
- move Cameras local recordings to a cache policy with TTL
- make Gateway and face-detection consumers read from Media or from a controlled cache instead of requiring indefinite preservation of recorder output

### Validation Needed Before Automatic Cleanup

- confirm whether Gateway overlay still requires the original Cameras local path after Media upload
- confirm whether face detection can run from Media service paths only
- confirm whether any active polling, overlay, or replay workflows still depend on `ppl-meta-cameras/recordings`

## Conclusion

This is a real storage issue, not just a reporting artifact.

The current implementation stores substantial duplicate video content across:

- `ppl-meta-cameras/recordings`
- `ppl-meta-media/media`

On this machine, the confirmed exact duplicate overlap is about 3.9 GB. The cleanup code that would remove the Cameras-side copy after successful upload is present only as disabled commented logic, so the duplication currently persists by design.