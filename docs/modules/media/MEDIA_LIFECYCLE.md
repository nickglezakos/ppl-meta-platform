# Media Lifecycle (CRUD)

This document describes the full lifecycle of a media object in the PPL Meta platform — from creation through retrieval, modification, and deletion.

---

## Data Model

Every media record tracks:

| Field Group | Key Fields |
|---|---|
| **Identity** | `uuid`, `id`, `filename`, `original_filename`, `checksum` (SHA256) |
| **File** | `file_path`, `file_extension`, `mime_type`, `file_size` |
| **Type** | `media_type` — `VIDEO`, `PICTURE`, `SOUND`, `STREAMING`, `DOCUMENT` |
| **Storage** | `storage_provider` — `LOCAL`, `AWS_S3`, `AZURE_BLOB`, `GOOGLE_CLOUD` |
| **Processing** | `processing_status` — `PENDING → PROCESSING → COMPLETED / FAILED / ARCHIVED` |
| **Ownership** | `uploaded_by` (user UUID) |
| **Device** | `device_name`, `device_model`, `device_manufacturer`, `device_os`, `app_name`, `app_version` |
| **Timing** | `capture_timestamp`, `start_timestamp`, `end_timestamp`, `created_at`, `updated_at` |
| **Location** | `location_data` (JSON — GPS, city, etc.) |
| **Metadata** | `title`, `description`, `tags`, `categories`, `technical_metadata` |
| **Access** | `is_public`, `access_permissions` |
| **Archive** | `is_archived`, `archived_at`, `archived_by_user_id`, `archive_source`, `archive_reason` |

### Related Entities

- **MediaDetails** — type-specific metadata (video codec/bitrate, image DPI, audio channels)
- **MediaVariant** — derived versions (thumbnails, quality variants, poster frames)
- **MediaCollection** — albums, playlists, camera-linked collections
- **MediaShare** — sharing links with permissions, expiration, and view limits

---

## Create

**Endpoint:** `POST /api/v1/media/upload`

**Parameters:** `file` (multipart), `user_id`, `title`, `description`, `tags`, `categories`, `is_public`, device fields, `location_data`, `capture_timestamp`

### Upload Pipeline

```
1.  Read file content → compute SHA256 checksum
2.  Detect media type from MIME type
3.  Check for duplicates (same user + checksum)
4.  Generate unique filename
5.  Build storage path: media/{user_id}/{media_type}/{YYYY}/{MM}/{filename}
6.  Create DB record with status = PENDING
7.  Save file to storage (async)
8.  Trigger async processing
```

### Async Processing

After the file is persisted, background tasks run depending on media type:

| Media Type | Processing |
|---|---|
| **IMAGE** | EXIF extraction (camera, GPS, orientation), thumbnail generation (150×150, 300×300, 600×600) |
| **VIDEO** | Frame extraction for thumbnails (via FFmpeg), metadata extraction (duration, resolution, frame rate, bitrate, codecs, exact frame count) |
| **AUDIO** | Channels, sample rate, bitrate, codec extraction |
| **DOCUMENT** | Page count, word count, language detection |

Processing status transitions: `PENDING → PROCESSING → COMPLETED` (or `FAILED` with error recorded in `processing_error`).

### File Type Resolution

```
video/*         → VIDEO
image/*         → PICTURE
audio/*         → SOUND
application/pdf → DOCUMENT
text/plain      → DOCUMENT
*               → DOCUMENT (fallback)
```

Allowed extensions (configurable): `jpg`, `jpeg`, `png`, `gif`, `mp4`, `avi`, `mov`.  
Max file size: 50 MB (default).

---

## Read

| Endpoint | Method | Purpose |
|---|---|---|
| `/{media_id}` | GET | Single media by UUID or integer ID |
| `/search` | GET | Filtered search (see below) |
| `/bulk` | GET | Bulk retrieve up to 100 items |
| `/user/{user_id}/grouped` | GET | Group by `device_name`, `media_type`, or `month` |
| `/user/{user_id}/stats` | GET | Analytics: counts, sizes, device breakdown, popular tags, access patterns |
| `/{media_id}/variants` | GET | All variants (thumbnails, quality levels) |

### Search Filters

- `user_id`, `media_type`, `tags`, `categories`
- `device_name`, `device_manufacturer`
- `collection` (single or multiple IDs)
- `date_from` / `date_to` — uses `start_timestamp` for camera recordings, `created_at` otherwise
- `is_public`
- `exclude_camera_collections` — omit auto-created camera collections
- Pagination: `page`, `page_size` (default 50)

### Access Control

- **Public media** (`is_public=True`): accessible by any authenticated user
- **Private media** (`is_public=False`): accessible only by the owner (`uploaded_by`)
- **System user UUID** (`00000000-...`): inter-service access bypass

---

## Gallery Search

The gallery search spans three layers: the backend query engine, the gateway proxy, and the Flutter frontend.

### Backend — `GET /api/v1/media/search`

#### Query Parameters

| Parameter | Type | Example | Notes |
|---|---|---|---|
| `query` | string (max 500) | `vacation` | Free-text (reserved, not full-text indexed) |
| `media_types` | comma-separated | `video,picture` | OR across types |
| `tags` | comma-separated | `work,security` | OR — matches if **any** tag matches |
| `categories` | comma-separated | `surveillance,events` | OR — same logic as tags |
| `device_name` | string | `front_gate` | Exact match on camera/device |
| `device_manufacturer` | string | `Ring` | Exact match |
| `is_public` | boolean | `true` | Public/private filter |
| `start_date` | ISO 8601 | `2024-01-01T00:00:00Z` | Lower bound (see date logic below) |
| `end_date` | ISO 8601 | `2024-12-31T23:59:59Z` | Upper bound |
| `collection_id` | string | UUID, int, or name | Single collection |
| `collection_ids` | comma-separated | `uuid1,uuid2,name` | Multiple collections |
| `sort_by` | string | `created_at` | Default: `created_at` |
| `sort_order` | string | `desc` | Default: `desc` (newest first) |
| `page` | int | `1` | 1-indexed |
| `page_size` | int | `20` | Default 20, max 500 |

All results are scoped to the authenticated user (`uploaded_by = current_user`). Archived items are excluded.

#### Filter Execution Order

The backend applies filters in this order, from most to least selective:

```
1. User scope      →  WHERE uploaded_by = :user_id
2. Media type      →  AND media_type IN (:types)
3. Tags            →  AND (tags @> ARRAY[:tag1] OR tags @> ARRAY[:tag2] …)
4. Categories      →  AND (categories @> ARRAY[:cat1] OR …)
5. Date range      →  AND (smart date filter — see below)
6. Collection join →  INNER JOIN media_collection_items … WHERE collection_id IN (…)
7. Sort + paginate →  ORDER BY created_at DESC OFFSET :offset LIMIT :page_size
```

#### Smart Date Filtering

Date filters use a dual-field strategy so that camera recordings are queried by **recording time** while uploaded media are queried by **upload time**:

```sql
-- start_date filter
WHERE (
  (start_timestamp IS NOT NULL AND start_timestamp >= :start_date)
  OR
  (start_timestamp IS NULL AND created_at >= :start_date)
)

-- end_date filter (same pattern)
WHERE (
  (start_timestamp IS NOT NULL AND start_timestamp <= :end_date)
  OR
  (start_timestamp IS NULL AND created_at <= :end_date)
)
```

This means "show me recordings from January" will match camera videos recorded in January regardless of when they were uploaded.

#### Collection Resolution

Collection identifiers go through a fallback chain:

1. Parse as **UUID** → match `MediaCollection.uuid`
2. Parse as **integer** → match `MediaCollection.id`
3. Match against **`camera_device_id`**
4. Fall back to **collection name** (partial match via `ILIKE`)

This allows the frontend to pass a camera device ID or a human-readable name and still resolve the correct collection.

#### Tag / Category Logic

- **Within a dimension**: OR — `tags=work,security` matches items with `work` **or** `security`
- **Across dimensions**: AND — an item must satisfy all active filter dimensions (type AND tags AND date range AND collection)

### Gateway Layer

The gateway at `GET /api/v1/media/search` transparently proxies all query parameters and authentication headers to `{MEDIA_SERVICE_URL}/api/v1/media/search`. No transformation occurs.

### Frontend — Flutter Gallery

#### Search Service

`UnifiedSearchService` orchestrates all search operations:

| Method | Purpose |
|---|---|
| `searchAllCollections(query, filters)` | Search across camera + user collections |
| `searchCameraMedia(query, cameraId, filters)` | Camera-specific search |
| `filterByDateRange(start, end, cameraOnly)` | Pure date filtering |
| `filterByCamera(cameraId)` | Single camera filter |
| `getSearchSuggestions(partialQuery)` | Auto-complete from recent searches, tags, camera names |
| `saveRecentSearch(query)` | Persist to local storage |
| `clearSearch()` | Reset all state |

#### Filter Model

```dart
class MediaSearchFilters {
  final String? query;
  final MediaType? mediaType;       // VIDEO, PICTURE, SOUND, etc.
  final DateTime? startDate;
  final DateTime? endDate;
  final List<String>? tags;
  final String? collectionId;
  final List<String>? collectionIds;
  final String? sortBy;             // 'created_at', 'filename', etc.
  final String? sortOrder;          // 'asc' or 'desc'
  final int? minFileSize;           // client-side only
  final int? maxFileSize;           // client-side only
  final bool? hasThumbnail;         // client-side only

  bool get hasFilters => /* true if any filter is active */;
}
```

`minFileSize`, `maxFileSize`, and `hasThumbnail` are applied client-side after the API response.

#### API Call Construction

The `MediaApiClient.searchMedia()` method builds query parameters from the filter model:

```dart
queryParams = {
  'page': page,
  'page_size': limit,
  'query': query,
  'media_type': mediaType?.apiValue,
  'start_date': startDate?.toUtc().toIso8601String(),
  'end_date': endDate?.toUtc().toIso8601String(),
  'tags': tags?.join(','),
  'collection_id': collectionId,
  'collection_ids': collectionIds?.join(','),
  'sort_by': sortBy ?? 'created_at',
  'sort_order': sortOrder ?? 'desc',
};
```

Null values are omitted. The response list is further filtered to exclude archived items (`item.isArchived == false`).

#### Infinite Scroll Pagination

`ResponsiveMediaGallery` implements infinite scroll:

- **Trigger**: user scrolls past 80% of the current scroll extent
- **Load**: calls `searchMedia()` with incremented `page`
- **Has-more detection**: `items.length == page_size` → more pages exist
- **Filter change**: clears items, resets `page` to 1, reloads

#### Responsive Grid Layout

| Screen Width | Grid Columns |
|---|---|
| < 600 px | 2 (mobile) |
| 600–899 px | 3 (tablet) |
| 900–1199 px | 4 (desktop) |
| ≥ 1200 px | 5 (large desktop) |

When filters change (detected in `didUpdateWidget`), the gallery clears its item list and re-fetches from page 1.

---

## Update

| Endpoint | Method | Purpose |
|---|---|---|
| `/{media_id}` | PUT | Full replacement of editable fields |
| `/{media_id}` | PATCH | Partial update |
| `/{media_id}/metadata` | PATCH | Update title, description, tags, categories only |
| `/{media_id}/privacy` | PATCH | Toggle `is_public` |
| `/{media_id}/location` | PATCH | Update GPS / location JSON |
| `/bulk-update` | POST | Bulk metadata update across multiple media IDs |

**Editable fields:** `title`, `description`, `tags`, `categories`, `is_public`, `is_archived`, `location_data`

Only the owner (`uploaded_by`) can update a media record.

---

## Delete

**The platform uses soft deletion exclusively — files are never removed from storage.**

| Endpoint | Method | Purpose |
|---|---|---|
| `/{media_id}` | DELETE | Soft-delete single media |
| `/bulk-delete` | DELETE | Soft-delete multiple items (returns success/failure counts) |

### What Happens on Delete

```
is_archived       = True
processing_status = ARCHIVED
archived_at       = now()
archive_source    = "api_delete_media"
archive_reason    = "soft_delete"
```

The file remains on disk. The record remains in the database but is excluded from normal queries (`WHERE is_archived = FALSE`).

### Archive / Restore

| Endpoint | Method | Purpose |
|---|---|---|
| `/{media_id}/archive` | POST | Archive with optional reason |
| `/{media_id}/restore` | POST | Restore to live state |

Archiving records: `archived_by_user_id`, `archive_source`, and `archive_reason` for audit.

---

## Collections

Collections group media into albums, playlists, or camera-linked sets.

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /collections` | POST | Create collection |
| `POST /collections/{id}/add/{media_id}` | POST | Add item |
| `POST /collections/{id}/remove/{media_id}` | POST | Remove item |
| `POST /bulk-add` | POST | Bulk add |
| `POST /bulk-remove` | POST | Bulk remove |
| `GET /collections/{id}/items` | GET | List items (paginated) |
| `GET /collections/{id}/stats` | GET | Collection statistics |
| `PUT /collections/{id}` | PUT | Update collection |
| `DELETE /collections/{id}` | DELETE | Delete collection |
| `PATCH /collections/{id}/reorder` | PATCH | Reorder items |

Camera collections are auto-created with `camera_device_id` set and named after the camera.

---

## Sharing

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /share/{media_id}` | POST | Create share link (params: `can_download`, `expires_hours`) |
| `GET /share/{share_token}` | GET | Access via token |
| `DELETE /share/{share_id}` | DELETE | Revoke link |

Share links support: `can_view`, `can_download`, `can_share` permissions, optional expiration, and view count limits.

---

## Variants

Derived versions of a media file (thumbnails, quality tiers, poster frames).

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /{media_id}/variants` | GET | List all variants |
| `POST /{media_id}/variants` | POST | Create variant |
| `GET /{media_id}/variants/{variant_id}` | GET | Get single variant |
| `PATCH /{media_id}/variants/{variant_id}` | PATCH | Update variant |
| `DELETE /{media_id}/variants/{variant_id}` | DELETE | Delete variant |

Variant types: `thumbnail`, `low_quality`, `high_quality`, `poster`.

---

## Service Integrations

| Service | Interaction |
|---|---|
| **Vision** | Processes media for face detection; media service queries vision for face metadata |
| **Camera** | Creates media records for recordings; sets `start_timestamp`/`end_timestamp`; auto-creates collections |
| **Edge Camera** | Uploads video as media with device information |
| **Gateway** | Routes and proxies media requests |
| **Communications** | Notifications on media sharing/storage events |
| **Node** | User management and ownership resolution |

---

## Storage Layout

```
media/
  {user_uuid}/
    video/
      2025/
        07/
          {unique_filename}.mp4
    picture/
      2025/
        07/
          {unique_filename}.jpg
thumbnails/
  {media_uuid}_small.jpg
  {media_uuid}_medium.jpg
  {media_uuid}_large.jpg
```

- **File storage base path:** `/tmp/ppl-meta-uploads` (configurable via `STORAGE_PATH`)
- **Thumbnail cache:** Redis (24h TTL) + filesystem
- **Metadata:** PostgreSQL
- **Deduplication:** SHA256 checksum per user
