# Cross-Video Statistics Tab Data Integrity Issue

Status: Open
Date: 2026-05-06
Scope: Cross-video individual analysis screen, Statistics tab

## Problem

The Statistics tab in the cross-video individual analysis screen mixes real backend-owned analysis fields with frontend-computed placeholders and guessed aggregates.

This makes some cards trustworthy and others misleading in the same screen.

## Verified Good Fields

The following values are currently expected to be real when they come from the backend analysis payload and the current search flow:

- Individual count
- Total appearances
- First appearance
- Last appearance

These are backed by the analysis payload and matched the recent search behavior observed during debugging.

## Verified Bad Or Untrusted Fields

### Unique videos

Observed issue:

- Recent search covered 2 videos
- Statistics tab showed 1 unique video

Root cause in frontend:

- At least one fallback construction path sets `uniqueVideos` from `appearancesData?.length ?? 1`
- The stats tab also aggregates unique videos using `math.max(...)` across individuals instead of a true union of appearance video UUIDs

This can undercount or otherwise drift from the real backend value.

### Average confidence

Observed issue:

- Real confidence values were visible in terminal responses
- The stats tab still behaved like it was showing a placeholder or derived fallback

Root cause in frontend:

- Multiple `AggregatedIndividualAnalysis` construction paths set `averageConfidence: 0.0`
- The stats tab then falls back to alternate sources instead of trusting `analysis.averageConfidence`

### Average appearance frequency

Observed issue:

- This metric is not part of the trustworthy backend contract for the current screen
- The current value is derived entirely in the frontend from time spans and appearance counts

Decision:

- Omit this card from the Statistics tab until the backend owns and returns a clearly defined metric

### Total duration

Observed issue:

- The tab showed `1 minute 0 seconds`
- It is unclear whether that was a true sum of appearance durations or just a synthetic segment total

Backend state:

- The backend-owned MVR analysis path currently returns `total_duration_seconds = 0.0`

Frontend state:

- Multiple analysis construction paths hardcode `totalDurationSeconds: 0.0`
- The stats tab also computes a separate `totalVideoDurationSeconds` from session search results, which is not the same thing as individual total appearance duration

Decision:

- Treat total duration as untrusted in this screen and omit it unless the backend returns a real non-zero value for the active analysis payload

### MVR age and gender rendering

Observed issue:

- MVR age and gender values exist in backend analysis payloads
- The Statistics tab does not reliably render them

Root cause in frontend:

- The tab currently reads demographics from `sessionData['search_results']` using `estimated_gender` and `estimated_age`
- It does not use the parsed `analysis.demographics` values already attached to each `AggregatedIndividualAnalysis`

This means the screen can ignore real backend-owned MVR demographics even when they are already fetched and parsed.

## Required Fix

1. Trust backend-owned `unique_videos`, `average_confidence`, `first_seen`, `last_seen`, and `demographics` from the analysis payload.
2. Remove or hide cards whose values are still placeholder-only in the current backend path.
3. Aggregate unique videos from actual appearance video UUID unions, not `max(...)` and not `appearances.length`.
4. Render demographics from `analysis.demographics`, not from legacy search-result fields.
5. Include seconds in first/last appearance timestamps for this screen.

## Backend Follow-Up

The backend-owned MVR analysis endpoint should eventually return a real `total_duration_seconds` if that metric is intended to remain in the UI.

Until then, the frontend should not present duration as if it were authoritative.