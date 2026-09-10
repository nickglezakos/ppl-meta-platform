# Fact-Finding Report: Assigning Merged MVR Results to Individual Groups

Date: 2026-05-08

## Question examined

Whether a user who sees a merged MVR person in the Individuals tab can add that item to an Individual Group, and whether doing so actually persists the merged identity as a group member under the new MVR flow where some search-time merges are preview-only and not stored.

## Executive conclusion

The answer is split into two cases.

1. Persisted manual merge: yes, the user can assign it to a group.
2. Ephemeral search-time merge preview: only partially, and not in the full semantic sense the UI suggests.

More precisely:

- If the merged result comes from the persistent hierarchical merge endpoint, the winner UUID is a real stored `mvr_people` row, so adding it to a group can succeed.
- If the merged result comes from the in-memory search preview flow, no new stored super-individual is created. The UI can still surface a grouped result using the winner's existing MVR UUID, but adding it to a group only stores that winner UUID. It does not persist the full preview-only merged grouping.
- Therefore, for preview-only merged search results, the user is not actually storing the merged MVR object as a durable grouped identity. They are storing only the existing winner MVR record.

## Primary findings

### 1. The add-to-group UI sends a single raw selected UUID without converting it first

In the cross-video Individuals tab, selection is tracked with `_selectedIndividuals`, and the Add to Group action passes `_selectedIndividuals.first` directly into `AddToGroupDialog` as `individualId`.

Relevant code:

- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- `ppl-meta-frontend/lib/widgets/individual_groups/add_to_group_dialog.dart`

Inside `AddToGroupDialog`, `_performAdd()` posts this value as:

```json
{
  "individual_ids": ["<selected uuid>"]
}
```

to:

`POST /api/v1/individual-groups/{groupId}/members`

There is no frontend-side conversion from a preview-only merged entity into a stored MVR entity before posting.

### 2. The backend add-members path only persists entries that already exist in `individuals` or `mvr_people`

`IndividualGroupsManager.add_members()` checks membership candidates in this order:

1. If UUID exists in `individuals`, it proceeds.
2. Else if UUID exists in `mvr_people`, it creates a lightweight `individuals` row for it and proceeds.
3. Else it skips the UUID.

This means the backend can only group an already-persisted identity. It does not create a new durable merged MVR entity from a preview-only grouped result during add-to-group.

Relevant code:

- `ppl-meta-vmeta/src/services/individual_groups_manager.py`

Important behavior in that method:

- it explicitly says it will persist `individuals` appearance data "if needed"
- but the actual persistence fallback is only for UUIDs that already exist in `mvr_people`
- if the UUID exists in neither table, the member is skipped

### 3. Manual hierarchical merge is persistent

The manual merge path used by the frontend when merging MVRs calls:

`POST /api/v1/mvr-people/merge/hierarchical`

This endpoint runs `HierarchicalMVRMerger.merge_hierarchical(...)`, which is the persistent merge path.

Relevant code:

- `ppl-meta-frontend/lib/services/media_api_client.dart`
- `ppl-meta-vmeta/src/api/routes/mvr_people.py`
- `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`

This path returns real winning super-individual UUIDs and updates persisted hierarchy state. A UUID returned from this path is a stored MVR UUID, so it satisfies the backend add-members gate described above.

### 4. Search-time auto-merge preview is explicitly non-persistent

The search flow also has an auto-merge path, but it is preview-only.

In `ppl-meta-vmeta/src/api/routes/mvr_people.py`, the search path calls:

`preview_hierarchical_merge(...)`

and the code comment is explicit:

"Build an in-memory merge preview only. Do not mutate persisted hierarchy state during search."

This means search-time grouped results are presentation-layer merged results, not newly stored super-individual records.

### 5. The preview merge does not mint a new UUID; it reuses an existing winner UUID

`preview_hierarchical_merge(...)` chooses a winner from the provided MVR rows and reports that winner as `super_individual_uuid`, but it does not write hierarchy rows.

So a preview-only grouped result is represented by an existing MVR UUID plus a list of merged children in response metadata.

That matters because Add to Group can store the winner UUID, but that does not make the preview grouping durable.

### 6. Some individual-tab payload builders normalize to the winner MVR UUID, which makes add-to-group appear to work

There are data-building paths in `mvr_people.py` that emit:

- `individual_uuid = super_uuid`
- `individual_id = super_uuid`

for hierarchy-backed merged results.

There are also frontend loaders that use MVR UUIDs directly, for example `_loadSingleMVRPerson(...)` sets:

- `individualUuid = data['mvr_person_uuid']`

In those paths, Add to Group receives a persisted MVR UUID and can succeed.

This is why the feature can appear operational in some merged scenarios.

### 7. But preview-only merged children are not made durable by add-to-group

In the preview search flow, grouped results are assembled from:

- winner MVR UUID
- merged child MVR UUIDs
- combined appearances

However, only the winner UUID is sent to the group-members API when a user adds the selected item.

No code in the add-to-group flow:

- writes the preview hierarchy to `mvr_merge_hierarchy`
- marks preview child MVRs as orphaned
- creates a new stored super-individual record
- persists the full `merged_mvr_uuids` set as group membership state

So the act of adding the item to a group does not convert the preview-only merge into a durable merged identity.

## Detailed answer to the question

### Can the user add a merged MVR result from the Individuals tab to a group?

Yes, sometimes.

It depends on what UUID is behind the selected row.

- If the selected row carries a real stored MVR UUID, add-to-group can succeed.
- If the selected row carries only a preview grouping concept but still uses a real winner UUID, add-to-group can also succeed, but it stores only the winner UUID.
- If a selected UUID were ever purely synthetic and absent from both `individuals` and `mvr_people`, the backend would skip it.

### Does that mean the merged MVR object itself is being stored and assigned to the group?

Not for preview-only merge results.

What gets stored is the winner UUID that already exists in `mvr_people` or `individuals`. The merged preview grouping itself is not persisted by the add-to-group flow.

That means the user is not reliably storing "this new merged search result as a durable super-individual". They are storing only one persisted identity that happened to be chosen as the preview winner.

## Important nuance: persistent merge versus preview merge

### Case A: user-triggered persistent merge

Flow:

1. User merges MVRs through the manual merge endpoint.
2. Backend persists hierarchy state.
3. Winner super-individual UUID exists durably.
4. User adds that item to a group.

Result:

- Group assignment is durable.
- Downstream normalization logic that resolves merged children to super-individuals can work correctly.

### Case B: search-time preview merge only

Flow:

1. Search returns preview-grouped merged results.
2. Backend has not persisted the hierarchy.
3. UI shows the grouped result using the winner's UUID.
4. User adds that item to a group.

Result:

- Add may succeed.
- But only the winner UUID is stored.
- The full merged preview identity is not persisted.
- Group semantics do not become equivalent to "store this merged search result as a super-individual".

## Additional risk found

There is a contract mismatch risk in the Individual Groups subsystem.

Some Individual Groups logic assumes `group.member_ids` are MVR UUIDs. For example, camera-search normalization in `IndividualGroupsManager` treats group member IDs as MVR people UUIDs and normalizes them via `mvr_merge_hierarchy`.

But `add_members()` can also accept UUIDs that already exist in `individuals` and store them as-is.

That means the system can end up with mixed membership semantics:

- some `member_ids` are MVR UUIDs
- some `member_ids` are raw individual UUIDs

This is not the main question you asked, but it increases the chance of inconsistent downstream behavior when groups are later used for camera search, duplicate detection, or merge resolution.

## Evidence summary

### Frontend add-to-group path

- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- `ppl-meta-frontend/lib/widgets/individual_groups/add_to_group_dialog.dart`

Observed behavior:

- selected analysis UUID is posted directly
- no persistence step for preview-only merge groups

### Backend group membership path

- `ppl-meta-vmeta/src/api/routes/individual_groups.py`
- `ppl-meta-vmeta/src/services/individual_groups_manager.py`

Observed behavior:

- accepts only persisted `individuals` or persisted `mvr_people`
- creates a lightweight `individuals` row only when the UUID already exists in `mvr_people`
- does not persist preview merge hierarchy during add-to-group

### Persistent merge path

- `ppl-meta-frontend/lib/services/media_api_client.dart`
- `ppl-meta-vmeta/src/api/routes/mvr_people.py`
- `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`

Observed behavior:

- manual hierarchical merge is durable
- returned winner UUID is a real stored identity

### Preview merge path

- `ppl-meta-vmeta/src/api/routes/mvr_people.py`
- `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`

Observed behavior:

- search preview explicitly does not mutate persisted state
- winner UUID is reused for display
- merged children remain response metadata only

## Final conclusion

Under the new MVR structure, a user can still sometimes click Add to Group on a merged-looking MVR result from the Individuals tab, but that does not necessarily mean the platform has stored the merged MVR object as a durable group member.

The current implementation supports durable group assignment only for identities that already exist in persistent storage.

For preview-only merge results from search:

- the UI may show a merged person
- the user may be able to add it
- but the system stores only the persisted winner UUID
- the preview-only merged grouping itself is not persisted as a durable super-individual during add-to-group

So the answer to the business question is:

No, not in the full intended sense. The current flow does not reliably convert a preview-only merged MVR result into a stored super-individual and then assign that durable merged identity to the group.

It only stores what is already persisted.

## Recommended follow-up checks

1. Confirm which Individuals-tab flows currently produce `individualUuid = super_uuid` versus raw `individual_uuid` before add-to-group.
2. Decide whether group membership should be normalized to MVR UUIDs only.
3. If preview-merge results should be group-assignable as durable identities, add an explicit backend promotion step before group membership is written.