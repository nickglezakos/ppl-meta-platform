# Media Preview Overlay No-Data Analysis

Date: 2026-05-08

Target media item: `f0e818be-6f57-4d02-8926-b1b82c5b8fd2`

## Summary

The current failure mode is no longer primarily a rectangle sync problem.

The current dominant issue is that the frontend preview flow reaches the video player without any face data, even though the backend does have stored face data for this media item.

At the same time, the media stream itself is valid and the stored video timing metadata is valid. That means:

1. The MP4 asset exists and streams correctly.
2. The video metadata used for FPS and frame count is present and internally consistent.
3. The overlay failure is in the face-data retrieval / flow-control layer, not in basic media playback.

## Backend Validation Results

### 1. Stream token endpoint

Validated URL:

`http://localhost:8080/api/v1/media/stream-token/f0e818be-6f57-4d02-8926-b1b82c5b8fd2?token=...`

Observed response:

- `HTTP/1.1 200 OK`
- `content-type: video/mp4`
- `content-length: 5895399`
- `accept-ranges: bytes`

Conclusion:

The underlying video stream is healthy and accessible.

### 2. Media metadata record

Validated endpoint with bearer token:

`GET /api/v1/media/f0e818be-6f57-4d02-8926-b1b82c5b8fd2`

Observed key fields:

- `processing_status: "completed"`
- `media_type: "video"`
- `mime_type: "video/mp4"`
- `uuid: "f0e818be-6f57-4d02-8926-b1b82c5b8fd2"`
- `collections[0].uuid: "360460d5-4c00-4f90-a623-42a71811b0b3"`

Technical metadata present:

- `total_frames: 893`
- `fps: 30.0`
- `duration_seconds: 29.766667`
- `frame_count_source: "ffprobe_exact"`
- `frame_count_confidence: "high"`
- `codec: "h264"`

Conclusion:

The media service has a fully populated record for the item. The video metadata looks healthy and should be sufficient for overlay frame calculations.

### 3. Video properties endpoint

Validated endpoint with bearer token:

`GET /api/v1/media/f0e818be-6f57-4d02-8926-b1b82c5b8fd2/video-properties`

Observed response:

```json
{
	"media_id": "f0e818be-6f57-4d02-8926-b1b82c5b8fd2",
	"video_properties": {
		"total_frames": 893,
		"fps": 30.0,
		"width": 1280,
		"height": 720,
		"duration_seconds": 29.766667,
		"frame_count_source": "ffprobe_exact",
		"frame_count_confidence": "high",
		"extraction_methods": ["ffprobe"]
	},
	"metadata_available": true,
	"preprocessing_required": false
}
```

Conclusion:

The timing metadata path used by the frontend is available and valid for this media item.

### 4. Workflow / face-data endpoints

Validated endpoints with bearer token:

- `GET /api/v1/processing-status/f0e818be-6f57-4d02-8926-b1b82c5b8fd2`
- `GET /api/v1/media/f0e818be-6f57-4d02-8926-b1b82c5b8fd2/faces/enhanced-v2`
- `GET /api/v1/vision/faces/media/f0e818be-6f57-4d02-8926-b1b82c5b8fd2`

Observed responses:

- `GET /api/v1/processing-status/<uuid>`
	- previously returned `404 Not Found`
	- root cause identified: gateway did not proxy the bare `processing-status/{media_uuid}` route even though Vision exposes it

- `GET /api/v1/media/<uuid>/faces/enhanced-v2`
	- now returns `success: true`
	- `source: "stored_faces"`
	- `total_faces: 128`

- `GET /api/v1/vision/faces/media/<uuid>`
	- now returns `success: true`
	- `has_stored_faces: true`
	- `total_faces: 128`
	- `faces_by_frame` populated

Conclusion:

For this media item, backend face data does exist and is reachable through gateway.

This shifts the root cause away from backend data absence and toward frontend load sequencing / cache / control flow.

## Frontend Chain Of Events

This section describes the current event chain in the frontend for media preview.

### 1. Media preview screen enters the restored preview path

Relevant code:

- `ppl-meta-frontend/lib/screens/media_preview_screen.dart`

Current behavior:

- `_buildVideoPreview(...)` constructs `SmartVideoPlayerWidget`
- preview now logs: `Media preview using pre-v2.24.80 SmartVideoPlayer path for ...`
- preview passes `enableWorkflowIntegration: false`

Reason for that change:

- the default workflow path was calling `processing-status`, which currently returns `404`
- disabling workflow integration avoids that dead branch

### 2. SmartVideoPlayerWidget starts in fallback playback mode

Relevant code:

- `ppl-meta-frontend/lib/widgets/smart_video_player_widget.dart`

Current behavior in `initState()`:

- if `enableWorkflowIntegration == false`, it sets fallback playback mode
- that fallback mode is currently `realtime_only`
- the player then builds a media URL of the form:

`/api/v1/media/stream/<uuid>?face_detection=false`

This is consistent with the logs:

- `SmartVideoPlayer: Using realtime_only Media Service URL with overlay (clean video)`

### 3. Widget attempts to find existing stored face data

Current decision chain in `_buildSmartVideoPlayer()`:

1. Check `_storedFaceData`
2. Check global face cache via `FaceDataMemoryManager`
3. If still empty, enter the no-data preview branch in `_buildVideoPlayerWithOverlay(...)`

Observed logs confirm this exact path:

- `_storedFaceData: null`
- `_faceDataSource: none`
- `GLOBAL CACHE CHECK ... has data: false`
- `NO FRAME DATA: No stored face data available for frame synchronization`

### 4. Preview branch now tries to trigger stored face loading directly

Recent local fixes changed the flow so that preview mode should start `_loadStoredFaceData()` directly instead of waiting for workflow status or falling immediately to the Enhanced Logic V2 loader.

This was necessary because:

- disabling workflow integration also disabled `_initializeSmartPlayback()`
- that meant `_loadStoredFaceData()` was not being called automatically

### 5. Frontend cache invalidation regression

Relevant code:

- `ppl-meta-frontend/lib/widgets/smart_video_player_widget.dart`

Two broad cache wipes were found:

1. `initState()` cleared:
	 - `FaceDataMemoryManager.instance.clearMediaData(widget.mediaItem.uuid)`
	 - `_faceDataCache.clear()`
2. `dispose()` cleared:
	 - `_faceDataCache.clear()`

Why this matters:

- `_faceDataCache.clear()` is global, not media-scoped
- this can remove face data for unrelated previews or for the active preview flow
- it creates a "load then disappear" failure mode that matches the user's theory

Current local mitigation:

- startup cache purge removed
- dispose cleanup narrowed to `_faceDataCache.remove(widget.mediaItem.uuid)`

## What Has Been Ruled Out

### Not ruled in as the primary cause anymore

- Basic MP4 playback corruption
- Missing media asset
- Missing video timing metadata
- FPS / frame-count extraction failure

### Still possible, but secondary

- Review overlay sync math
- Green rectangle frame mapping

These remain secondary because the current state is more fundamental: no face data reaches the overlay path.

## Most Likely Current Root Cause

The strongest current explanation is now a frontend flow bug.

Specifically:

1. Media playback and metadata endpoints work.
2. Stored face data exists and is available through gateway for this item.
3. The frontend preview flow still reaches the overlay with `_storedFaceData: null` and empty global cache.
4. Recent frontend regressions in cache invalidation and load sequencing remain the most likely reason the available backend data is not being rendered.

So the issue appears to be a combined failure:

- a gateway contract mismatch existed for some routes and has been identified
- frontend flow and cache handling became less robust in the preview no-data scenario
- the remaining blocker is frontend data-loading control flow

## Recommended Next Checks

### Backend

1. Verify the actual gateway route that should serve `Enhanced Logic V2` face data for a completed camera recording.
2. Confirm whether the media item has corresponding face detections stored in orchestrator / vision / media services.
3. Check whether the current route was renamed or moved and the frontend client was not updated.
4. Confirm whether camera-recording segments are now skipping the path that materializes face data used by preview overlays.

### Frontend

1. Keep the preview path on `enableWorkflowIntegration: false` until the `processing-status` route is verified.
2. Keep cache cleanup media-scoped only.
3. Add one-time logs around `_loadStoredFaceData()` entry and provider response.

## Full-Range Overlay Plan

The preview overlay must stop using any representative-face summary as its rendering source.

For the current implementation direction, there is now only one accepted source for preview rectangles:

1. Enhanced V2 `detection_result.faces_by_frame`

Everything else is considered invalid for preview playback overlay:

1. `representative_faces`
2. `best_face`
3. top-level Enhanced V2 summary faces
4. synthetic or approximated rectangle data
5. fallback sources that do not provide the same full per-frame contract

The requirement for the green rectangles is:

1. Use the full temporal range of detections for the active video.
2. Render rectangles from real per-frame face boxes.
3. Never collapse the playback overlay to `representative_faces`, `best_face`, or any per-person summary subset.

There are two possible backend-driven designs in theory, but for the preview player we are explicitly choosing Option A only.

### Option A: Use Enhanced V2 Stored Face Data As The Overlay Source

This is the cleanest option for the preview player because the data shape already matches what the overlay needs.

Relevant evidence:

- `mediaFaceDataProvider` already calls Enhanced V2 and flattens `detection_result.faces_by_frame` into `FaceDetection` records.
- The provider already distinguishes between representative data and full data and explicitly prefers `detection_result.faces_by_frame`.
- Each returned face record contains real bounding boxes plus `frame_number` metadata.

Why this fits the rectangle overlay:

1. The player sync logic already expects `FaceDetection` objects with `boundingBox` and `metadata['frame_number']`.
2. The overlay renderer already groups by frame and renders rectangles from those boxes.
3. No translation from route-point semantics into rectangle semantics is required.

Required implementation shape:

1. Preview screen must not pass `initialFaceData` from `_previewMvrFaces`.
2. Preview player must call the stored-face load path immediately on entry.
3. That load path must consume only `detection_result.faces_by_frame` when available.
4. The returned full frame map must be cached per media UUID.
5. `_setupFaceFrameSync(...)` must always build `_facesByFrame` from the full detection list.
6. Rectangle rendering must use that frame map directly with no representative-face fallback.
7. If `detection_result.faces_by_frame` is missing, preview must fail explicitly instead of substituting a different payload.

Required guards:

1. If Enhanced V2 does not return `detection_result.faces_by_frame`, do not use top-level `faces`, top-level `faces_by_frame`, or any other summary payload.
2. Do not clear the face cache globally during preview startup.
3. Do not replace full-frame detections with MVR preview data after the player has loaded.
4. Do not allow any delayed fallback path to overwrite or substitute full-frame data.
5. Do not generate synthetic rectangles, synthetic timestamps, or synthetic frame mappings for preview playback.

Validation target:

For media `f0e818be-6f57-4d02-8926-b1b82c5b8fd2`, preview logs should show the full loaded count from Enhanced V2 rather than `10` representative faces, and the frame map should span the real frame range of the video.

Conclusion:

If the goal is full-range green rectangles synchronized to playback, Enhanced V2 stored face data is the correct primary source.

### Option B: Use Route Data To Drive Preview Overlay

Route data can be useful, but it is not currently rectangle-ready data.

For preview playback, route data is out of scope for the rectangle renderer and should remain on MVR analysis screens only.

Relevant evidence from the current frontend route normalization:

- normalized route points contain `sequence_number`, `timestamp`, `frame_number`, `center_x`, `center_y`, velocity fields, camera identifiers, and UUIDs
- normalized route points do not contain face bounding boxes
- current route normalization sets `frame_number` from `sequence_number`, which is route ordering, not necessarily the original video frame index

Why route data is not sufficient by itself for green rectangles:

1. Green rectangles need `bbox` coordinates for each displayed detection.
2. Route points provide trajectory centers, not rectangle extents.
3. Route sequence numbers are not guaranteed to equal source video frame numbers.
4. Even with dense route coverage, the route payload is semantically tracking data, not rendering data.

That means route data can only support rectangles in one of these two ways:

1. Join route points with a second source that contains per-frame `bbox` values.
2. Expand the route endpoint contract so each point carries real `bbox` and source-frame information.

#### Route-Based Plan B1: Join Route Data With Stored Face Detections

Use route data for temporal filtering and identity grouping, but use stored detections for actual box rendering.

Implementation shape:

1. Fetch full route data for the selected media / individual context.
2. Fetch full stored face detections from Enhanced V2 for the same media.
3. Build an index keyed by `frame_number`.
4. Use route data to decide which identity or track is relevant.
5. Use Enhanced V2 detections to draw the actual rectangles.

When to use this:

Use this if the preview must remain aware of route context or person grouping while still rendering true boxes.

Tradeoff:

This keeps route semantics, but it still depends on Enhanced V2 for the actual rectangle geometry.

#### Route-Based Plan B2: Expand The Route API Contract

If route data itself must become the only overlay source, then the backend contract needs to change.

Required route payload additions:

1. `bbox` for every point
2. original source `frame_number` for every point
3. `video_uuid` guaranteed for every point
4. enough density to cover the full playback timeline, not just sparse motion samples

Only after those fields exist can route data directly power a full rectangle overlay.

Tradeoff:

This is a larger contract change and duplicates data already available in stored detections.

Conclusion:

Route data alone is not the best source for the green rectangles unless the API is extended. In the current system, route data is better treated as contextual tracking data, not as the primary rectangle-rendering payload.

## Recommended Direction

For the current preview overlay bug, the required implementation is:

1. Use Enhanced V2 `detection_result.faces_by_frame` as the only primary rectangle source.
2. Keep MVR / route data on MVR analysis screens only, not in preview playback overlay rendering.
3. Remove any path that feeds `representative_faces` into playback overlay rendering.
4. Remove all preview overlay fallbacks that substitute a different backend payload.
5. Reject synthetic data paths entirely.

## Concrete Acceptance Criteria

The preview overlay implementation is only correct when all of the following are true:

1. The player loads full per-frame detections for the active media item.
2. The loaded face count is close to backend stored detections, not a tiny representative subset.
3. `_facesByFrame` spans the real video timeline.
4. Rectangles appear across the full playback duration, not only in the first few seconds.
5. No preview code path injects `mvr_preview_overlay` into the player as if it were frame-accurate playback data.
6. If Enhanced V2 full per-frame data is unavailable, preview shows an explicit failure state rather than using fallback or synthetic data.

## Evidence Snapshot

Media item:

- `f0e818be-6f57-4d02-8926-b1b82c5b8fd2`

Validated working endpoints:

- `GET /api/v1/media/stream-token/<uuid>?token=...` -> `200 OK`
- `GET /api/v1/media/<uuid>` -> media record present
- `GET /api/v1/media/<uuid>/video-properties` -> metadata present

Validated endpoints with stored face data:

- `GET /api/v1/media/<uuid>/faces/enhanced-v2` -> `200` and `total_faces: 128`
- `GET /api/v1/vision/faces/media/<uuid>` -> `200` and `has_stored_faces: true`

Validated problematic route:

- `GET /api/v1/processing-status/<uuid>` -> gateway mismatch previously observed

## Conclusion

At the time of this analysis, the most important fact is this:

The frontend can play the video, can read valid timing metadata, and backend face data is present for the target media item.

That means the next decisive step is frontend load-path repair, not backend face-generation investigation and not further overlay synchronization changes.
