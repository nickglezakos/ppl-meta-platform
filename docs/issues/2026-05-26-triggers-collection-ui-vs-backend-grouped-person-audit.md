# Triggers Collection UI vs Backend Grouped Person Audit

Date: 2026-05-26
Collection: Triggers
Collection UUID: `386bd146-24a4-4454-a4ed-158e0bafb398`
Scope: Audit all videos currently in the Triggers collection and compare live backend grouped-person results per video.

## Goal

Verify whether the current Triggers collection problem is purely a frontend issue by listing every video in the collection and capturing the current backend results for:

- Orchestrator grouped person count from `/api/v1/orchestrator/person-objects/{media_id}`
- Raw MVR result count from `/api/v1/mvr-people/search/by-videos` with `auto_merge=false`

## Collection Inventory And Live Backend Results

| Video Name | Media UUID | Orchestrator Grouped Persons | Raw MVR Results |
|---|---|---:|---:|
| girl-fashion.mp4 | 00a31a51-f916-45bb-903a-d41fb88b16de | 2 | 3 |
| girls-outdoors.mp4 | 5762c9ae-2cbb-4712-b0eb-9c9e57300dd5 | 0 | 0 |
| man-sports.mp4 | 422cd560-d848-4316-b591-159cf9b6c707 | 0 | 0 |
| one_man_office.mp4 | 573219bd-e621-4ab1-a4b4-5290dc271c24 | 0 | 0 |
| one_man_one_woman_jogging.mp4 | 0211f8d4-78ad-467a-8e85-d0e5e1b27ba4 | 2 | 3 |
| one_woman_one_man_office.mp4 | 1844b795-4789-4baa-9f5e-a98c899aecc9 | 3 | 18 |
| one_woman_tech_02.mp4 | 5ad73d3b-efd6-4279-ac12-94fccf8c7577 | 1 | 2 |
| one_woman_tech_03.mp4 | 3a0e395d-e63b-4396-a266-cc318b67dc42 | 0 | 0 |
| people-office.mp4 | a824a416-a234-4d18-b9d3-e39cbcf8c5e6 | 1 | 6 |
| three_men_office.mp4 | cf3cbf74-8516-4bc7-a0b3-6b27b1331eb1 | 1 | 1 |
| three_women_one_man_laughing_outdoors.mp4 | 2886beb9-5166-45a2-a82d-1b91c0babd3d | 4 | 4 |
| three_women_outdoors.mp4 | 59209bfd-f1d1-4ee1-8616-e4586190f07d | 6 | 10 |
| tow_eman_one_woman_tech.mp4 | 65c2e3e7-c9ea-442f-8c29-94d715c974bf | 3 | 18 |
| two_men_one_woman_office.mp4 | a62ddfb0-bb54-4a7f-83f3-985177409114 | 4 | 5 |
| two_men_outdoors.mp4 | ce2b28f6-b2b9-43da-87cf-64e4b3665e40 | 7 | 19 |
| two_men_two_women.mp4 | ca4723c3-e594-4943-b772-0dd3ff08529b | 2 | 12 |
| two_women_oudoors.mp4 | a03739e8-39fa-4a8a-8bb3-22668c14134d | 2 | 6 |
| two_women_two_men_office.mp4 | fe755aae-f3de-430a-a81e-2023e66211f3 | 3 | 4 |
| woman-fashion.mp4 | 773d94b5-71dd-4f77-be28-61446d8dc639 | 7 | 3 |
| woman-flowers.mp4 | 75da4379-9981-4602-80bd-5037b90f6cc9 | 15 | 15 |

## Immediate Observations

- The Triggers collection currently contains 20 videos.
- The known good video `three_women_one_man_laughing_outdoors.mp4` (`2886beb9-5166-45a2-a82d-1b91c0babd3d`) is aligned at `4` grouped persons and `4` raw MVR results.
- The collection is not uniformly backend-aligned.
- Several videos already show large backend discrepancies between orchestrator grouped persons and raw MVR results, for example:
  - `one_woman_one_man_office.mp4`: `3` vs `18`
  - `tow_eman_one_woman_tech.mp4`: `3` vs `18`
  - `two_men_outdoors.mp4`: `7` vs `19`
  - `two_men_two_women.mp4`: `2` vs `12`
  - `woman-fashion.mp4`: `7` vs `3`
- Some videos are aligned at zero or near-zero, and some are aligned exactly, so the backend state across this collection is mixed rather than consistently healthy.

## Current Conclusion

This Triggers collection issue cannot yet be classified as frontend-only.

At least for the current live backend state, the collection contains a mixture of:

- videos where backend grouped-person and MVR counts align
- videos where backend grouped-person and MVR counts diverge materially
- videos with no persisted grouped/MVR results at all

That means the next debugging step should use this table as the source of truth and split the remaining work into:

1. backend-divergent videos
2. backend-aligned but UI-wrong videos

## Data Collection Method

The counts above were collected live on 2026-05-26 using:

- `GET /api/v1/media/search?collection_id=386bd146-24a4-4454-a4ed-158e0bafb398&skip=0&limit=200`
- `GET /api/v1/orchestrator/person-objects/{media_id}`
- `POST /api/v1/mvr-people/search/by-videos` with body:

```json
{
  "video_uuids": ["<media_uuid>"],
  "auto_merge": false,
  "ignore_existing_hierarchy": true
}
```
