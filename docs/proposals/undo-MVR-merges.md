# Proposal: Undo MVR Merges

**Status:** Draft  
**Date:** 2026-04-04  
**Scope:** ppl-meta-vmeta (backend) + ppl-meta-frontend (Flutter)

---

## Background

MVR (Most-Valuable-Record) people are merged in two ways:

| Trigger | Endpoint | Description |
|---|---|---|
| Post-search (automatic) | `POST /api/v1/mvr-people/merge/hierarchical` | After a cross-video search, `HierarchicalMVRMerger` groups similar MVR records using Union-Find and promotes the highest-quality one as the super-individual |
| Manual (add-to-group flow) | `POST /api/v1/individual-groups/{id}/merge-members` | User is shown a duplicate-detection dialog while adding an individual to a group and confirms a merge |

In both cases the **loser** MVR record is not deleted — it is marked `is_orphaned = TRUE` and its `merged_into_mvr_uuid` column points to the winner. Its individuals are re-linked to the winner via `individual_mvr_mapping`. The audit trail is preserved in `mvr_merge_audit_log` and the parent-child relationship is recorded in `mvr_merge_hierarchy`.

Currently there is **no undo path**. This proposal adds one for both scenarios, and adds representative-face thumbnails to child MVR cards (a prerequisite for scenario 2).

---

## Goals

1. Allow a user to undo a post-search automatic merge via a banner/action shown immediately after the search completes.
2. Allow a user to split a specific child MVR out of a super-individual from the Individuals tab expanded card, using per-child thumbnail images to confirm identity.

---

## Non-Goals

- Bulk undo of all merges in a session.
- Undo of merges older than the current session (history-level rollback is out of scope here).
- Changing the merge algorithm or thresholds.

---

## Part 1 — Post-Search Automatic Merge Undo

### User Flow

```
User runs cross-video search
          │
          ▼
Individuals tab loads
          │
          ├─ If hierarchical merge was applied:
          │    A yellow banner appears above the list:
          │    "⚠️ N individuals were automatically merged.
          │     Review merges  [Undo All]"
          │
          ▼
User taps "Review merges"
          │
          ▼
A bottom sheet lists each merge group:
  [Face thumb A]  →  [Face thumb B]  similarity: 87%  [Undo]
  [Face thumb C]  →  [Face thumb D]  similarity: 73%  [Undo]
          │
          ▼
User taps [Undo] on one row
          │
          ▼
Confirm dialog: "Split these two individuals? This cannot be re-merged automatically."
          │
          ▼
API call  →  backend restores orphaned MVR
          │
          ▼
Banner updates: "1 merge undone. N–1 remaining."
Screen refreshes individual list.
```

### Backend — New Endpoint

**`POST /api/v1/mvr-people/unmerge`**

```
Request:
{
  "orphaned_mvr_uuid": "<uuid>",   // the loser/child
  "user_id": "<uuid>"
}

Response:
{
  "success": true,
  "restored_mvr_uuid": "<uuid>",
  "individuals_reassigned": 3,       // count of individual_mvr_mapping rows restored
  "message": "MVR unmerged successfully"
}
```

**DB operations (all in a single transaction):**

1. Clear orphan status on the child:
   ```sql
   UPDATE mvr_people
   SET is_orphaned = FALSE,
       orphaned_at = NULL,
       merged_into_mvr_uuid = NULL,
       updated_at = NOW()
   WHERE mvr_people_uuid = :orphaned_mvr_uuid
     AND is_orphaned = TRUE;
   ```

2. Restore `individual_mvr_mapping` rows that were moved to the winner *at the time of this specific merge*. Use `mvr_merge_audit_log` to identify which rows were reassigned:
   ```sql
   UPDATE individual_mvr_mapping
   SET mvr_people_uuid = :orphaned_mvr_uuid,
       link_method = 'unmerge_restored',
       linked_at = NOW()
   WHERE individual_uuid = :reassigned_individual_uuid
     AND mvr_people_uuid = :winner_mvr_uuid;
   ```
   The `reassigned_individual_uuid` is read from `mvr_merge_audit_log.source_individual_uuid` for this merge event.

3. Delete the `mvr_merge_hierarchy` row:
   ```sql
   DELETE FROM mvr_merge_hierarchy
   WHERE super_individual_uuid = :winner_mvr_uuid
     AND merged_mvr_uuid = :orphaned_mvr_uuid;
   ```

4. Insert an audit log row with `merge_action = 'unmerged'`.

> **Note:** The winner's `face_embedding` and demographics may have been updated to the loser's values at merge time (if the loser had higher quality). The unmerge does **not** attempt to revert these fields — they contain valid biometric data and reverting them without the original values stored is unsafe. This is an acceptable limitation noted explicitly to the user.

**Implementation file:** `ppl-meta-vmeta/src/database/mvr_repository.py` — add `async def unmerge_mvr_people(orphaned_mvr_uuid, user_id)`.  
**Route file:** `ppl-meta-vmeta/src/api/routes/mvr_people.py` — add endpoint handler.

### Frontend Changes

**Files affected:**
- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- `ppl-meta-frontend/lib/services/media_api_client.dart` (or `individual_groups_api_client.dart`)

**New state in `_PersonObjectsDetailScreenState`:**
```dart
bool _hierarchicalMergeWasApplied = false;
List<MergeGroupSummary> _mergeGroups = [];   // NEW model — see below
```

**`_loadCrossVideoData()` change:** after loading `_aggregatedAnalyses`, check `sessionData['hierarchical_merge_applied'] == true` and store merge group summaries from the hierarchical merge response (the `merge_groups` array already comes back from `POST /api/v1/mvr-people/merge/hierarchical`).

**New widget: merge banner**
```dart
Widget _buildMergeBanner() {
  if (!_hierarchicalMergeWasApplied || _mergeGroups.isEmpty) return const SizedBox.shrink();
  return Container(
    color: Colors.amber.shade100,
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
    child: Row(
      children: [
        const Icon(Icons.merge_type, color: Colors.orange),
        const SizedBox(width: 8),
        Expanded(
          child: Text('${_mergeGroups.fold(0, (s, g) => s + g.mergedCount)} individuals were automatically merged.'),
        ),
        TextButton(onPressed: _showMergeReviewSheet, child: const Text('Review')),
        TextButton(
          onPressed: _undoAllMerges,
          child: const Text('Undo All', style: TextStyle(color: Colors.red)),
        ),
      ],
    ),
  );
}
```

**New: `MergeGroupSummary` model (`cross_video_analysis_models.dart`):**
```dart
class MergeGroupSummary {
  final String superIndividualUuid;
  final List<String> mergedMvrUuids;
  final Map<String, double> similarities;   // mergedUuid → similarity score
  final int mergedCount;
}
```

**New API client method:**
```dart
Future<ApiResponse<Map<String, dynamic>>> unmergeMvr({
  required String orphanedMvrUuid,
}) async {
  // POST /api/v1/mvr-people/unmerge
}
```

---

## Part 2 — Individuals Tab Child MVR Undo (Split from Super-Individual)

This covers the use case where the user expands a super-individual card in the Individuals tab, sees the child MVR records, identifies a wrong merge, and taps "Split" on that child.

### Prerequisite: Child MVR Thumbnails

Currently `_buildMergedMVRCard` shows a generic `Icons.badge` icon. Child identities are impossible to verify without a face image. The prerequisite is loading a best-face image per child.

**How to load images for children:**

The endpoint `GET /api/v1/mvr-people/{mvr_uuid}/best-image` already exists and returns the same `BestImageResponse` shape used for super-individuals. It just needs to be called for each child UUID.

**New method in `MvrImageService`:**
```dart
Future<Map<String, BestImageResponse?>> getBestImagesForMergedChildren(
  List<String> childMvrUuids,
) async {
  // Calls GET /api/v1/mvr-people/{uuid}/best-image for each uuid in parallel
  // Returns map keyed by child mvr_people_uuid
}
```

**Where to call it:**  
In `_PersonObjectsDetailScreenState._loadBestImagesForIndividuals()`, after populating `_bestImages` for super-individuals, collect all `analysis.mergedMVRPeople.map((m) => m.mvrPeopleUuid)` across all analyses and call `getBestImagesForMergedChildren`. Store results in a new field:
```dart
Map<String, BestImageResponse?> _childMvrImages = {};
```

**`_buildMergedMVRCard` update:** replace the `Icons.badge` container with the same `Image.network` pattern used in `_buildIndividualThumbnail`:
```dart
// Replace Icons.badge Container with:
Container(
  width: 40,
  height: 40,
  decoration: BoxDecoration(
    color: Colors.blue.shade50,
    borderRadius: BorderRadius.circular(6),
    border: Border.all(color: Colors.blue.shade200),
  ),
  child: ClipRRect(
    borderRadius: BorderRadius.circular(6),
    child: _buildChildMvrThumbnail(mvr.mvrPeopleUuid),
  ),
),
```

```dart
Widget _buildChildMvrThumbnail(String childMvrUuid) {
  final bestImage = _childMvrImages[childMvrUuid];
  if (bestImage?.bestFace == null || bestImage!.bestFace!.imageUrl.isEmpty) {
    return Icon(Icons.badge, size: 24, color: Colors.blue[700]);
  }
  final rawUrl = bestImage.bestFace!.imageUrl;
  final uri = Uri.tryParse(rawUrl);
  final resolvedUrl = (uri != null && uri.hasScheme)
      ? rawUrl
      : '${Config.gatewayServiceUrl}${rawUrl.startsWith('/') ? rawUrl : '/$rawUrl'}';
  final apiClient = ref.read(apiClientProvider);
  return Image.network(
    resolvedUrl,
    fit: BoxFit.cover,
    headers: apiClient.authToken != null
        ? {'Authorization': 'Bearer ${apiClient.authToken}'}
        : const {},
    errorBuilder: (_, __, ___) => Icon(Icons.badge, size: 24, color: Colors.blue[700]),
  );
}
```

### User Flow — Split from Card

```
User expands super-individual card
          │
          ▼
"Merged MVR People (N)" section shows N child cards,
each now showing a cropped face thumbnail
          │
          ▼
Each child card has a  [⋮]  menu icon (or a small "Split" button)
          │
          ▼
User taps [Split] on a child card
          │
          ▼
Confirm dialog:
  "Remove this individual from the merged group?
   They will appear as a separate individual.
   [Cancel]  [Split]"
          │
          ▼
Same API call as Part 1:
  POST /api/v1/mvr-people/unmerge
  { "orphaned_mvr_uuid": "<child_uuid>", "user_id": "..." }
          │
          ▼
On success: screen reloads cross-video data.
Child disappears from the super-individual's expanded section
and re-appears as its own standalone card in the individuals list.
```

**`_buildMergedMVRCard` UI addition:**
```dart
// In the Row's trailing position:
IconButton(
  icon: const Icon(Icons.call_split, size: 18),
  tooltip: 'Split this individual',
  color: Colors.red[400],
  onPressed: () => _confirmSplitMvr(mvr),
),
```

```dart
void _confirmSplitMvr(MergedMVRPerson mvr) {
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Split individual?'),
      content: const Text(
        'This will remove the individual from the merged group. '
        'They will appear as a separate individual. '
        'Note: the representative face embedding of the group may not revert.',
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: () {
            Navigator.pop(context);
            _performUnmerge(mvr.mvrPeopleUuid);
          },
          style: FilledButton.styleFrom(backgroundColor: Colors.red),
          child: const Text('Split'),
        ),
      ],
    ),
  );
}

Future<void> _performUnmerge(String orphanedMvrUuid) async {
  try {
    final apiClient = ref.read(apiClientProvider);
    // call POST /api/v1/mvr-people/unmerge
    await apiClient.unmergeMvr(orphanedMvrUuid: orphanedMvrUuid);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Individual split successfully.')),
      );
      _loadCrossVideoData();   // reload everything
    }
  } catch (e) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Split failed: $e')),
      );
    }
  }
}
```

---

## Summary of Changes Required

### Backend (`ppl-meta-vmeta`)

| File | Change |
|---|---|
| `src/database/mvr_repository.py` | Add `async def unmerge_mvr_people(orphaned_mvr_uuid, user_id)` |
| `src/api/routes/mvr_people.py` | Add `POST /api/v1/mvr-people/unmerge` handler |

### Frontend (`ppl-meta-frontend`)

| File | Change |
|---|---|
| `lib/models/cross_video_analysis_models.dart` | Add `MergeGroupSummary` model |
| `lib/services/media_api_client.dart` (or `individual_groups_api_client.dart`) | Add `unmergeMvr()` method |
| `lib/services/mvr_image_service.dart` | Add `getBestImagesForMergedChildren()` |
| `lib/screens/person_objects_detail_screen.dart` | Add banner, review sheet, `_childMvrImages` map, thumbnail in child card, split button + confirm dialog, `_performUnmerge()` |

---

## Known Limitations

- **Embedding not reverted:** if the winner's face embedding was replaced with the loser's (because the loser had higher quality), the unmerge does not restore the original embedding. The data is not stored anywhere for rollback. The user is informed of this via copy in both the confirm dialog and the banner.
- **Cascading merges:** if child A was first merged into B, and B was then merged into C, undoing A from C requires undoing in reverse order. The UI should detect this by checking `mvr_merge_hierarchy.merge_level` and warn accordingly.
- **Group membership:** if the winner's UUID was used for a group membership and the unmerge splits out individuals, the group membership stays on the winner. The user may need to manually re-add the split individual to a group.
