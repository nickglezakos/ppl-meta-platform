# PPL Meta Media Service - API Documentation

**Version:** 1.0.0  
**Service:** ppl-meta-media  
**Port:** 8000  
**Base URL:** `http://localhost:8000/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Health & Monitoring](#health--monitoring)
   - [Core Service](#core-service)
   - [Media Management](#media-management)
   - [Collections](#collections)
   - [Media Variants](#media-variants)
   - [Media Details & Metadata](#media-details--metadata)
   - [Streaming & Download](#streaming--download)
   - [Face Detection Workflows](#face-detection-workflows)
   - [Storage Management](#storage-management)
   - [Security](#security)
   - [User](#user)
   - [VMeta Proxy](#vmeta-proxy)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Best Practices](#best-practices)

---

## Overview

The PPL Meta Media Service is a comprehensive FastAPI-based microservice responsible for:

- **Media Management**: Upload, storage, and retrieval of images and videos
- **Collections**: Organization of media into user-defined collections
- **Streaming**: Efficient video streaming with range request support
- **Face Detection**: Integration with Vision Service for facial recognition workflows
- **Metadata Management**: Advanced metadata handling and EXIF extraction
- **Storage Management**: Multi-tier storage with cloud integration
- **User Management**: Profile and permission handling
- **Security**: JWT authentication and rate limiting

### Key Features

- RESTful API design
- JWT-based authentication
- Real-time streaming support
- Bulk operations
- Advanced search and filtering
- Cloud storage integration
- Prometheus metrics
- Service discovery integration
- Comprehensive error handling

---

## Authentication

All endpoints (except health checks) require JWT authentication.

### Authentication Header

```http
Authorization: Bearer <jwt_token>
```

### Obtaining a Token

Authentication is handled by the Gateway service. Include the JWT token in all requests.

**Example:**

```bash
curl -X GET http://localhost:8000/api/v1/media/search \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## API Endpoints

### Health & Monitoring

#### 1. Basic Health Check

**GET** `/health`

Get basic service health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1699876543.21,
  "service": "ppl-meta-media"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/health
```

---

#### 2. Detailed Health Check

**GET** `/health/detailed`

Get detailed health information including database and system metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1699876543.21,
  "service": "ppl-meta-media",
  "version": "v1",
  "database": "healthy",
  "system": {
    "cpu_percent": 23.5,
    "memory_percent": 45.2,
    "disk_percent": 67.8
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/health/detailed
```

---

#### 3. Readiness Check

**GET** `/health/ready`

Kubernetes readiness probe - checks if service is ready to accept traffic.

**Response:**
```json
{
  "status": "ready",
  "version": "v1"
}
```

---

#### 4. Liveness Check

**GET** `/health/live`

Kubernetes liveness probe - checks if service is alive.

**Response:**
```json
{
  "status": "alive",
  "version": "v1"
}
```

---

### Core Service

#### 5. Get Service Info

**GET** `/core/info`

Get comprehensive service information.

**Response:**
```json
{
  "service": "ppl-meta-media",
  "version": "1.0.0",
  "api_version": "v1",
  "description": "Media processing and management service",
  "capabilities": [
    "media_upload",
    "video_streaming",
    "face_detection",
    "metadata_management"
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/core/info \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 6. Get Service Status

**GET** `/core/status`

Get operational status and feature list.

**Response:**
```json
{
  "service": "ppl-meta-media",
  "api_version": "v1",
  "status": "operational",
  "features": [
    "health_monitoring",
    "database_integration",
    "microservice_ready",
    "nuitka_compatible"
  ]
}
```

---

### Media Management

#### 7. Register Media

**POST** `/media/register`

Register media metadata without file upload (for pre-existing files).

**Request Body:**
```json
{
  "filename": "video.mp4",
  "filepath": "/storage/videos/video.mp4",
  "media_type": "video",
  "size": 15728640,
  "duration": 120.5,
  "width": 1920,
  "height": 1080
}
```

**Response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "video.mp4",
  "media_type": "video",
  "size": 15728640,
  "duration": 120.5,
  "created_at": "2025-11-12T10:30:00Z",
  "user_id": "user123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/media/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "video.mp4",
    "filepath": "/storage/videos/video.mp4",
    "media_type": "video",
    "size": 15728640
  }'
```

---

#### 8. Upload Media

**POST** `/media/upload`

Upload a new media file (image or video).

**Request:**
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: File to upload (required)
  - `description`: Optional description
  - `tags`: Optional comma-separated tags

**Response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "vacation.mp4",
  "media_type": "video",
  "size": 25165824,
  "upload_complete": true,
  "thumbnail_url": "/api/v1/media/thumbnail/550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/media/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/video.mp4" \
  -F "description=Family vacation" \
  -F "tags=vacation,family,2025"
```

**Note:** This endpoint automatically triggers Enhanced Logic V2 face detection for video uploads.

---

#### 9. Search Media

**GET** `/media/search`

Search media with advanced filters.

**Query Parameters:**
- `query` (optional): Text search query
- `media_type` (optional): Filter by type (`image`, `video`)
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `tags` (optional): Comma-separated tags
- `collection_id` (optional): Filter by collection
- `sort_by` (optional): Sort field (default: `created_at`)
- `sort_order` (optional): `asc` or `desc` (default: `desc`)
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "beach.jpg",
    "media_type": "image",
    "size": 2048576,
    "created_at": "2025-11-12T10:00:00Z",
    "tags": ["vacation", "beach"],
    "thumbnail_url": "/api/v1/media/thumbnail/550e8400-e29b-41d4-a716-446655440000"
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/media/search?media_type=video&tags=vacation&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 10. Get Media by ID

**GET** `/media/{media_id}`

Retrieve detailed information about a specific media item.

**Path Parameters:**
- `media_id`: Media UUID

**Response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "video.mp4",
  "media_type": "video",
  "size": 15728640,
  "duration": 120.5,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "codec": "h264",
  "created_at": "2025-11-12T10:30:00Z",
  "user_id": "user123",
  "tags": ["vacation"],
  "description": "Family vacation video"
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/media/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 11. Update Media (Full)

**PUT** `/media/{media_id}`

Fully update media metadata.

**Request Body:**
```json
{
  "filename": "new_name.mp4",
  "description": "Updated description",
  "tags": ["new", "tags"]
}
```

**Response:** Updated MediaResponse object

**Example:**
```bash
curl -X PUT http://localhost:8000/api/v1/media/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename": "new_name.mp4", "description": "Updated"}'
```

---

#### 12. Update Media (Partial)

**PATCH** `/media/{media_id}`

Partially update media metadata.

**Request Body:**
```json
{
  "description": "Updated description only"
}
```

**Response:** Updated MediaResponse object

---

#### 13. Update Media Metadata

**PATCH** `/media/{media_id}/metadata`

Update specific metadata fields.

**Request Body:**
```json
{
  "custom_metadata": {
    "location": "Hawaii",
    "event": "Wedding"
  },
  "tags": ["wedding", "hawaii"]
}
```

---

#### 14. Delete Media

**DELETE** `/media/{media_id}`

Delete a media item permanently.

**Response:**
```json
{
  "message": "Media deleted successfully",
  "media_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/v1/media/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

---

### Collections

#### 15. List Collections

**GET** `/media/collections`

Get all collections for the current user.

**Query Parameters:**
- `include_items` (optional): Include item count (default: false)

**Response:**
```json
[
  {
    "id": "col-123",
    "name": "Vacation 2025",
    "description": "Summer vacation photos and videos",
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": "2025-11-12T14:30:00Z",
    "item_count": 45,
    "user_id": "user123"
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/media/collections?include_items=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 16. Collection Lookup by Name

**GET** `/media/collections/lookup`

Find collections by exact name match.

**Query Parameters:**
- `name`: Collection name (required)

**Response:**
```json
{
  "id": "col-123",
  "name": "Vacation 2025",
  "exists": true
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/media/collections/lookup?name=Vacation%202025" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 17. Search Collections

**GET** `/media/collections/search`

Search collections with filters.

**Query Parameters:**
- `query` (optional): Text search
- `sort_by` (optional): Sort field
- `limit` (optional): Results limit

**Response:** Array of MediaCollectionResponse objects

---

#### 18. Get Collection Statistics

**GET** `/media/collections/{collection_id}/stats`

Get detailed statistics for a collection.

**Response:**
```json
{
  "collection_id": "col-123",
  "total_items": 45,
  "media_types": {
    "image": 30,
    "video": 15
  },
  "total_size": 524288000,
  "date_range": {
    "earliest": "2025-06-01T00:00:00Z",
    "latest": "2025-08-31T23:59:59Z"
  }
}
```

---

#### 19. Get Collection by ID

**GET** `/media/collections/{collection_id}`

Retrieve detailed collection information.

**Example:**
```bash
curl http://localhost:8000/api/v1/media/collections/col-123 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 20. Get Collection Items

**GET** `/media/collections/{collection_id}/items`

Get all media items in a collection.

**Query Parameters:**
- `sort_by` (optional): Sort field
- `sort_order` (optional): `asc` or `desc`
- `limit` (optional): Results limit
- `offset` (optional): Pagination offset

**Response:** Array of MediaResponse objects

**Example:**
```bash
curl "http://localhost:8000/api/v1/media/collections/col-123/items?limit=20&sort_by=created_at" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 21. Get Collection Items with Details

**GET** `/media/collections/{collection_id}/items-with-details`

Get collection items with enhanced metadata.

**Response:** Array of enhanced MediaResponse objects with additional details

---

#### 22. Create Collection

**POST** `/media/collections`

Create a new media collection.

**Request Body:**
```json
{
  "name": "Summer Vacation",
  "description": "Our amazing summer trip",
  "is_public": false
}
```

**Response:**
```json
{
  "id": "col-456",
  "name": "Summer Vacation",
  "description": "Our amazing summer trip",
  "created_at": "2025-11-12T15:00:00Z",
  "item_count": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/media/collections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Summer Vacation", "description": "Our trip"}'
```

---

#### 23. Update Collection (Full)

**PUT** `/media/collections/{collection_id}`

Fully update collection metadata.

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "is_public": true
}
```

---

#### 24. Update Collection (Partial)

**PATCH** `/media/collections/{collection_id}`

Partially update collection.

**Request Body:**
```json
{
  "description": "New description"
}
```

---

#### 25. Delete Collection

**DELETE** `/media/collections/{collection_id}`

Delete a collection (media items remain).

**Response:**
```json
{
  "message": "Collection deleted successfully",
  "collection_id": "col-123"
}
```

---

#### 26. Add Media to Collection

**POST** `/media/collections/{collection_id}/add/{media_id}`

Add a media item to a collection.

**Response:**
```json
{
  "message": "Media added to collection",
  "collection_id": "col-123",
  "media_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/media/collections/col-123/add/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 27. Remove Media from Collection

**DELETE** `/media/collections/{collection_id}/remove/{media_id}`

Remove a media item from a collection.

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/v1/media/collections/col-123/remove/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 28. Bulk Add to Collection

**POST** `/media/collections/{collection_id}/bulk-add`

Add multiple media items to a collection.

**Request Body:**
```json
{
  "media_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response:**
```json
{
  "added_count": 2,
  "failed_count": 0,
  "collection_id": "col-123"
}
```

---

#### 29. Bulk Remove from Collection

**POST** `/media/collections/{collection_id}/bulk-remove`

Remove multiple media items from a collection.

**Request Body:**
```json
{
  "media_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

---

#### 30. Reorder Collection Items

**PATCH** `/media/collections/{collection_id}/reorder`

Change the order of items in a collection.

**Request Body:**
```json
{
  "item_order": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

---

### Media Variants

#### 31. List Media Variants

**GET** `/media/{media_id}/variants`

Get all variants of a media item (thumbnails, compressed versions, etc.).

**Response:**
```json
[
  {
    "id": "var-123",
    "media_id": "550e8400-e29b-41d4-a716-446655440000",
    "variant_type": "thumbnail",
    "size": 102400,
    "created_at": "2025-11-12T10:31:00Z"
  }
]
```

---

#### 32. Create Media Variant

**POST** `/media/{media_id}/variants`

Create a new variant of a media item.

**Request Body:**
```json
{
  "variant_type": "compressed",
  "quality": 80,
  "max_dimension": 1280
}
```

---

#### 33. Generate Media Variants

**POST** `/media/{media_id}/variants/generate`

Automatically generate standard variants (thumbnail, preview, compressed).

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_variants": ["thumbnail", "preview", "compressed"],
  "total_variants": 3
}
```

---

#### 34. Get Variant Statistics

**GET** `/media/{media_id}/variants/statistics`

Get statistics about media variants.

**Response:**
```json
{
  "total_variants": 3,
  "total_size": 5242880,
  "variants_by_type": {
    "thumbnail": 1,
    "compressed": 2
  }
}
```

---

#### 35. Get Variant by ID

**GET** `/media/{media_id}/variants/{variant_id}`

Retrieve a specific variant.

---

#### 36. Update Variant

**PUT** `/media/{media_id}/variants/{variant_id}`

Update variant metadata.

---

#### 37. Delete Variant

**DELETE** `/media/{media_id}/variants/{variant_id}`

Delete a specific variant.

---

#### 38. Get Variant Types

**GET** `/media/variants/types`

List all available variant types.

**Response:**
```json
[
  "thumbnail",
  "preview",
  "compressed",
  "watermarked",
  "cropped"
]
```

---

### Media Details & Metadata

#### 39. Get Media Details

**GET** `/media/{media_id}/details`

Get comprehensive media details including technical metadata.

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "video.mp4",
  "technical_metadata": {
    "duration": 120.5,
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "codec": "h264",
    "bitrate": 5000000
  },
  "user_metadata": {
    "description": "Family vacation",
    "location": "Hawaii"
  },
  "exif_data": {}
}
```

---

#### 40. Update Media Details (Full)

**PUT** `/media/{media_id}/details`

Fully update media details.

---

#### 41. Update Technical Metadata

**PATCH** `/media/{media_id}/details/technical`

Update only technical metadata fields.

**Request Body:**
```json
{
  "codec": "h265",
  "bitrate": 3000000
}
```

---

#### 42. Update User Metadata

**PATCH** `/media/{media_id}/details/user`

Update user-defined metadata.

**Request Body:**
```json
{
  "description": "Updated description",
  "location": "Maui, Hawaii",
  "tags": ["vacation", "beach", "2025"]
}
```

---

#### 43. Get Custom Metadata

**GET** `/media/{media_id}/metadata/custom`

Get all custom metadata fields.

**Response:**
```json
{
  "event": "Wedding",
  "photographer": "John Doe",
  "camera_model": "Sony A7III"
}
```

---

#### 44. Add Custom Metadata

**POST** `/media/{media_id}/metadata/custom`

Add new custom metadata fields.

**Request Body:**
```json
{
  "field_name": "event",
  "field_value": "Wedding",
  "field_type": "string"
}
```

---

#### 45. Update Custom Metadata Field

**PUT** `/media/{media_id}/metadata/custom/{field_name}`

Update a specific custom metadata field.

---

#### 46. Delete Custom Metadata Field

**DELETE** `/media/{media_id}/metadata/custom/{field_name}`

Remove a custom metadata field.

---

#### 47. Bulk Update Metadata

**POST** `/media/metadata/bulk-update`

Update metadata for multiple media items.

**Request Body:**
```json
{
  "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "metadata_updates": {
    "tags": ["vacation", "2025"],
    "custom": {
      "event": "Summer Trip"
    }
  }
}
```

**Response:**
```json
{
  "updated_count": 1,
  "failed_count": 0,
  "errors": []
}
```

---

#### 48. Bulk Export Metadata

**POST** `/media/metadata/bulk-export`

Export metadata for multiple media items.

**Request Body:**
```json
{
  "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "format": "json",
  "include_fields": ["technical", "user", "exif"]
}
```

**Response:**
```json
{
  "export_id": "exp-123",
  "format": "json",
  "item_count": 1,
  "download_url": "/api/v1/media/metadata/export/exp-123"
}
```

---

#### 49. Bulk Import Metadata

**POST** `/media/metadata/bulk-import`

Import metadata from a file.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: Metadata file (JSON/CSV)
  - `overwrite`: Boolean (default: false)

---

#### 50. Search Metadata

**GET** `/media/metadata/search`

Search across all metadata fields.

**Query Parameters:**
- `query`: Search query
- `fields`: Comma-separated fields to search
- `exact_match`: Boolean

**Response:**
```json
{
  "total_results": 10,
  "results": [
    {
      "media_id": "550e8400-e29b-41d4-a716-446655440000",
      "matching_fields": ["description", "tags"],
      "relevance_score": 0.95
    }
  ]
}
```

---

#### 51. Get Metadata Analytics

**GET** `/media/metadata/analytics`

Get analytics about metadata usage.

**Response:**
```json
{
  "total_media_items": 1000,
  "items_with_custom_metadata": 750,
  "most_common_tags": ["vacation", "family", "2025"],
  "metadata_completeness": 0.85
}
```

---

#### 52. Validate Metadata

**POST** `/media/metadata/validation`

Validate metadata against schema.

**Request Body:**
```json
{
  "metadata": {
    "description": "Test",
    "duration": 120
  },
  "schema_name": "video_metadata_v1"
}
```

---

#### 53. Get Metadata Schema

**GET** `/media/metadata/schemas/{media_type}`

Get metadata schema for a media type.

**Path Parameters:**
- `media_type`: `image` or `video`

**Response:**
```json
{
  "media_type": "video",
  "version": "1.0",
  "required_fields": ["filename", "duration"],
  "optional_fields": ["description", "tags"],
  "field_types": {
    "duration": "float",
    "tags": "array"
  }
}
```

---

#### 54. List Metadata Templates

**GET** `/media/metadata/templates`

Get all available metadata templates.

**Response:**
```json
[
  {
    "id": "tmpl-123",
    "name": "Event Video Template",
    "fields": ["event_name", "date", "location"],
    "media_types": ["video"]
  }
]
```

---

#### 55. Create Metadata Template

**POST** `/media/metadata/templates`

Create a new metadata template.

**Request Body:**
```json
{
  "name": "Wedding Video Template",
  "description": "Template for wedding videos",
  "fields": {
    "event_type": "Wedding",
    "venue": "",
    "photographer": ""
  }
}
```

---

#### 56. Apply Metadata Template

**POST** `/media/{media_id}/metadata/apply-template`

Apply a template to a media item.

**Request Body:**
```json
{
  "template_id": "tmpl-123",
  "overwrite_existing": false
}
```

---

### EXIF & Technical Data

#### 57. Get EXIF Data

**GET** `/media/exif/{media_id}`

Extract and return EXIF data from media file.

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "exif_data": {
    "Make": "Canon",
    "Model": "EOS R5",
    "DateTime": "2025:06:15 14:30:22",
    "GPS": {
      "Latitude": 21.3099,
      "Longitude": -157.8581
    }
  }
}
```

---

#### 58. Extract EXIF Data

**POST** `/media/exif/extract/{media_id}`

Force extraction and storage of EXIF data.

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "extracted_fields": 25,
  "timestamp": "2025-11-12T15:30:00Z"
}
```

---

#### 59. Bulk Extract EXIF

**POST** `/media/exif/bulk-extract`

Extract EXIF data for multiple media items.

**Request Body:**
```json
{
  "media_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response:**
```json
{
  "processed_count": 2,
  "success_count": 2,
  "failed_count": 0
}
```

---

#### 60. Get Video Properties

**GET** `/media/{media_id}/video-properties`

Get detailed video technical properties.

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "duration": 120.5,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "codec": "h264",
  "bitrate": 5000000,
  "audio_codec": "aac",
  "audio_bitrate": 128000,
  "total_frames": 3615
}
```

---

#### 61. Refresh Metadata

**POST** `/media/refresh-metadata`

Refresh cached metadata for media items.

**Request Body:**
```json
{
  "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "force": true
}
```

---

### Streaming & Download

#### 62. Download Media

**GET** `/media/download/{media_id}`

Download original media file.

**Response:** Binary file stream

**Example:**
```bash
curl http://localhost:8000/api/v1/media/download/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN" \
  -o video.mp4
```

---

#### 63. Stream Media

**GET** `/media/stream/{media_id}`

Stream media with range request support (for video playback).

**Headers:**
- `Range`: `bytes=0-1023` (optional)

**Response:** Binary stream with range support

**Example:**
```bash
curl http://localhost:8000/api/v1/media/stream/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Range: bytes=0-1048576"
```

---

#### 64. Get Stream Token

**GET** `/media/stream-token/{media_id}`

Get a temporary token for streaming (for clients that can't handle JWT).

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream_token": "tmp_abc123xyz",
  "expires_at": "2025-11-12T16:00:00Z",
  "stream_url": "/api/v1/streaming/video/550e8400-e29b-41d4-a716-446655440000?token=tmp_abc123xyz"
}
```

---

#### 65. Get Media Thumbnail

**GET** `/media/thumbnail/{media_id}`

Get or generate thumbnail for media.

**Query Parameters:**
- `width` (optional): Thumbnail width (default: 200)
- `height` (optional): Thumbnail height (default: 200)

**Response:** Image binary data (JPEG)

**Example:**
```bash
curl http://localhost:8000/api/v1/media/thumbnail/550e8400-e29b-41d4-a716-446655440000?width=400 \
  -H "Authorization: Bearer $TOKEN" \
  -o thumbnail.jpg
```

---

#### 66. Get Video Frame

**GET** `/media/{media_id}/frame/{frame_number}`

Extract a specific frame from a video.

**Path Parameters:**
- `media_id`: Video UUID
- `frame_number`: Frame index

**Response:** Image binary data (JPEG)

**Example:**
```bash
curl http://localhost:8000/api/v1/media/550e8400-e29b-41d4-a716-446655440000/frame/150 \
  -H "Authorization: Bearer $TOKEN" \
  -o frame.jpg
```

---

#### 67. Stream Video (Dedicated Endpoint)

**GET** `/streaming/video/{media_id}`

Advanced video streaming with quality selection.

**Query Parameters:**
- `quality` (optional): `low`, `medium`, `high`
- `start_time` (optional): Start position in seconds

---

#### 68. Test Stream Video

**GET** `/streaming/test/video/{media_id}`

Test streaming endpoint with diagnostics.

---

#### 69. Get Video Frame with Faces

**GET** `/streaming/faces/{media_id}/frame/{frame_number}`

Get video frame with face detection overlays.

**Response:** Image with face bounding boxes drawn

---

#### 70. Get Video Face Info

**GET** `/streaming/info/{media_id}/faces`

Get face detection information for all frames.

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_frames": 3615,
  "frames_with_faces": 1245,
  "total_faces_detected": 3892,
  "faces_by_frame": [
    {
      "frame_number": 0,
      "face_count": 2,
      "detection_confidence": 0.95
    }
  ]
}
```

---

### Face Detection Workflows

#### 71. Start Bulk Face Detection

**POST** `/workflow/face-detection/bulk-process`

Start a workflow to process multiple videos for face detection.

**Request Body:**
```json
{
  "media_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "method": "two_stage",
  "confidence_threshold": 0.5,
  "store_results": true,
  "processing_priority": "normal",
  "frames_per_second": 3
}
```

**Response:**
```json
{
  "workflow_id": "wf-abc123",
  "status": "queued",
  "media_count": 2,
  "created_at": "2025-11-12T15:00:00Z",
  "estimated_completion_time": "2025-11-12T15:10:00Z",
  "processing_options": {
    "method": "two_stage",
    "fps": 3
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/workflow/face-detection/bulk-process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "method": "two_stage",
    "frames_per_second": 3
  }'
```

---

#### 72. Get Workflow Status

**GET** `/workflow/face-detection/{workflow_id}/status`

Get the status of a face detection workflow.

**Response:**
```json
{
  "workflow_id": "wf-abc123",
  "status": "processing",
  "progress": 0.45,
  "processed_count": 9,
  "total_count": 20,
  "current_media_id": "660e8400-e29b-41d4-a716-446655440001",
  "started_at": "2025-11-12T15:00:00Z",
  "results_summary": {
    "total_faces": 127,
    "unique_individuals": 8
  }
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/workflow/face-detection/wf-abc123/status \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 73. Get Workflow Results

**GET** `/workflow/face-detection/{workflow_id}/results`

Get complete results of a finished workflow.

**Response:**
```json
{
  "workflow_id": "wf-abc123",
  "status": "completed",
  "total_media": 20,
  "total_faces": 456,
  "unique_individuals": 15,
  "completed_at": "2025-11-12T15:08:00Z",
  "results_by_media": [
    {
      "media_id": "550e8400-e29b-41d4-a716-446655440000",
      "faces_detected": 23,
      "processing_time": 12.5
    }
  ]
}
```

---

#### 74. Cancel Workflow

**POST** `/workflow/face-detection/{workflow_id}/cancel`

Cancel a running workflow.

**Response:**
```json
{
  "workflow_id": "wf-abc123",
  "status": "cancelled",
  "processed_count": 5,
  "total_count": 20
}
```

---

#### 75. List User Workflows

**GET** `/workflow/face-detection/user/workflows`

Get all workflows for the current user.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Results limit
- `offset` (optional): Pagination offset

**Response:** Array of WorkflowStatusResponse objects

---

### Storage Management

#### 76. Get Storage Preferences

**GET** `/storage/storage-preferences`

Get user's storage preferences.

**Response:**
```json
{
  "user_id": "user123",
  "default_tier": "standard",
  "auto_archive_enabled": true,
  "archive_after_days": 90,
  "cloud_sync_enabled": false
}
```

---

#### 77. Update Storage Preferences

**PUT** `/storage/storage-preferences`

Update storage preferences.

**Request Body:**
```json
{
  "default_tier": "premium",
  "auto_archive_enabled": true,
  "archive_after_days": 60
}
```

---

#### 78. Get Storage Usage

**POST** `/storage/storage-usage`

Get detailed storage usage information.

**Request Body:**
```json
{
  "include_archived": true,
  "group_by": "media_type"
}
```

**Response:**
```json
{
  "user_id": "user123",
  "total_used": 5368709120,
  "quota": 107374182400,
  "usage_percentage": 5.0,
  "by_media_type": {
    "video": 4294967296,
    "image": 1073741824
  },
  "by_tier": {
    "standard": 5368709120,
    "archive": 0
  }
}
```

---

#### 79. Get Storage Summary

**GET** `/storage/storage-summary`

Get summary of storage usage.

**Response:**
```json
{
  "total_used_bytes": 5368709120,
  "total_used_readable": "5.0 GB",
  "quota_bytes": 107374182400,
  "quota_readable": "100 GB",
  "percentage_used": 5.0,
  "available_bytes": 102005473280
}
```

---

#### 80. Get Storage Recommendations

**GET** `/storage/storage-recommendations`

Get AI-powered storage optimization recommendations.

**Response:**
```json
{
  "recommendations": [
    {
      "type": "archive_old_media",
      "description": "Archive 45 media items older than 90 days",
      "potential_savings": 2147483648,
      "impact": "medium"
    }
  ],
  "total_potential_savings": 2147483648
}
```

---

#### 81. Get Collection Storage Config

**GET** `/storage/collections/{collection_id}/storage-config`

Get storage configuration for a collection.

**Response:**
```json
{
  "collection_id": "col-123",
  "tier": "standard",
  "compression_enabled": false,
  "cloud_backup_enabled": true
}
```

---

#### 82. Initialize Collection Storage

**POST** `/storage/collections/{collection_id}/initialize-storage`

Initialize storage settings for a collection.

**Request Body:**
```json
{
  "tier": "premium",
  "enable_compression": false,
  "enable_cloud_backup": true
}
```

---

#### 83. Storage Cleanup

**POST** `/storage/storage-cleanup`

Perform storage cleanup operations.

**Request Body:**
```json
{
  "remove_duplicates": true,
  "remove_temporary": true,
  "compress_old_media": false
}
```

**Response:**
```json
{
  "freed_bytes": 536870912,
  "operations_performed": {
    "duplicates_removed": 15,
    "temporary_files_removed": 43
  }
}
```

---

#### 84. Get Storage Analytics

**GET** `/storage/storage-analytics`

Get detailed storage analytics and trends.

**Response:**
```json
{
  "growth_trend": {
    "daily_average": 104857600,
    "weekly_average": 734003200,
    "monthly_projection": 3145728000
  },
  "quota_forecast": {
    "estimated_full_date": "2026-08-15",
    "days_remaining": 276
  }
}
```

---

#### 85. Get Storage Health

**GET** `/storage/storage-health`

Get storage system health status.

**Response:**
```json
{
  "status": "healthy",
  "disk_usage": 67.5,
  "fragmentation": "low",
  "issues": []
}
```

---

#### 86. Optimize Collection Storage

**POST** `/storage/collections/{collection_id}/optimize-storage`

Optimize storage for a specific collection.

**Request Body:**
```json
{
  "enable_compression": true,
  "generate_variants": false,
  "remove_duplicates": true
}
```

---

#### 87. Get Storage Notifications

**GET** `/storage/storage-notifications`

Get storage-related notifications.

**Response:**
```json
{
  "notifications": [
    {
      "id": "notif-123",
      "type": "quota_warning",
      "message": "Storage usage is at 85%",
      "severity": "warning",
      "created_at": "2025-11-12T14:00:00Z"
    }
  ]
}
```

---

#### 88. Dismiss Storage Notification

**POST** `/storage/storage-notifications/{notification_id}/dismiss`

Dismiss a storage notification.

---

### Security

#### 89. Get Security Status

**GET** `/security/status`

Get security configuration and status.

**Response:**
```json
{
  "service": "ppl-meta-media",
  "security_enabled": true,
  "jwt_validation": "active",
  "rate_limiting": "enabled",
  "file_validation": "strict"
}
```

---

#### 90. Test Validation

**GET** `/security/validation/test`

Test security validation mechanisms.

---

#### 91. Get Rate Limit Status

**GET** `/security/rate-limit/status`

Get current rate limit status for the user.

**Response:**
```json
{
  "user_id": "user123",
  "requests_remaining": 450,
  "limit": 500,
  "window": "1 hour",
  "reset_at": "2025-11-12T16:00:00Z"
}
```

---

#### 92. Get File Security Capabilities

**GET** `/security/file-security/capabilities`

Get file security scanning capabilities.

**Response:**
```json
{
  "antivirus_enabled": true,
  "file_type_validation": true,
  "size_limits": {
    "image": 52428800,
    "video": 5368709120
  }
}
```

---

#### 93. Get Auth Info

**GET** `/security/auth/info`

Get authentication information for current user.

**Response:**
```json
{
  "user_id": "user123",
  "username": "john.doe",
  "token_expires_at": "2025-11-12T18:00:00Z",
  "permissions": ["read", "write", "delete"]
}
```

---

### User

#### 94. Get User Profile

**GET** `/user/profile`

Get current user's profile information.

**Response:**
```json
{
  "user_id": "user123",
  "username": "john.doe",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-11-12T10:00:00Z"
}
```

---

#### 95. Get User Permissions

**GET** `/user/permissions`

Get user's permissions and access levels.

**Response:**
```json
{
  "user_id": "user123",
  "role": "user",
  "permissions": [
    "media.read",
    "media.write",
    "media.delete",
    "collections.manage"
  ],
  "is_admin": false
}
```

---

#### 96. Get Media Access Info

**GET** `/user/media/access`

Get user's media access information.

**Response:**
```json
{
  "user_id": "user123",
  "owned_media_count": 145,
  "shared_media_count": 23,
  "collections_count": 8,
  "storage_used": 5368709120
}
```

---

#### 97. Get Admin Status

**GET** `/user/admin/status`

Check if user has admin privileges.

**Response:**
```json
{
  "user_id": "user123",
  "is_admin": false,
  "admin_since": null
}
```

---

#### 98. Get Public User Info

**GET** `/user/public/info`

Get public information about the user (no authentication required for public profiles).

**Response:**
```json
{
  "user_id": "user123",
  "username": "john.doe",
  "public_collections_count": 2,
  "profile_picture_url": "/api/v1/media/thumbnail/profile-pic-uuid"
}
```

---

### User Statistics

#### 99. Get User Media Grouped

**GET** `/media/user/{user_id}/grouped`

Get user's media grouped by type.

**Response:**
```json
{
  "user_id": "user123",
  "total_items": 145,
  "by_type": {
    "video": 87,
    "image": 58
  },
  "by_month": {
    "2025-11": 23,
    "2025-10": 34
  }
}
```

---

#### 100. Get User Media Stats

**GET** `/media/user/{user_id}/stats`

Get comprehensive statistics about user's media.

**Response:**
```json
{
  "user_id": "user123",
  "total_media": 145,
  "total_storage": 5368709120,
  "collections_count": 8,
  "most_used_tags": ["vacation", "family", "2025"],
  "upload_trend": {
    "this_month": 23,
    "last_month": 34
  }
}
```

---

### Sharing

#### 101. Share Media

**POST** `/media/share/{media_id}`

Create a share link for media.

**Request Body:**
```json
{
  "expires_at": "2025-12-31T23:59:59Z",
  "password_protected": false,
  "allow_download": true
}
```

**Response:**
```json
{
  "share_id": "shr-abc123",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "share_url": "https://app.pplmeta.com/shared/shr-abc123",
  "expires_at": "2025-12-31T23:59:59Z",
  "created_at": "2025-11-12T15:00:00Z"
}
```

---

### VMeta Proxy

#### 102. Batch Match and Merge

**POST** `/mvr-people/batch-match-and-merge`

Proxy endpoint to vmeta service for batch matching and merging individuals.

**Request Body:**
```json
{
  "individual_uuids": [
    "ind-abc123",
    "ind-def456",
    "ind-ghi789"
  ],
  "threshold": 0.85,
  "triggered_by": "cross_video_tracking_session",
  "session_uuid": "session-xyz"
}
```

**Response:**
```json
{
  "original_count": 3,
  "unique_count": 2,
  "merged_groups": [
    {
      "primary_uuid": "ind-abc123",
      "merged_uuids": ["ind-def456"],
      "confidence": 0.92
    }
  ],
  "processing_time": 1.25
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/mvr-people/batch-match-and-merge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "individual_uuids": ["ind-abc123", "ind-def456"],
    "threshold": 0.85
  }'
```

---

## Data Models

### MediaResponse

```json
{
  "uuid": "string",
  "filename": "string",
  "media_type": "image | video",
  "size": 0,
  "duration": 0.0,
  "width": 0,
  "height": 0,
  "created_at": "datetime",
  "updated_at": "datetime",
  "user_id": "string",
  "tags": ["string"],
  "description": "string"
}
```

### MediaCollectionResponse

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "user_id": "string",
  "item_count": 0,
  "is_public": false
}
```

### WorkflowStatusResponse

```json
{
  "workflow_id": "string",
  "status": "queued | processing | completed | failed",
  "progress": 0.0,
  "processed_count": 0,
  "total_count": 0,
  "current_media_id": "string",
  "started_at": "datetime",
  "completed_at": "datetime",
  "error_message": "string",
  "results_summary": {}
}
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_type": "ValidationError"
}
```

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no content to return
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required or failed
- **403 Forbidden**: User lacks permission for this resource
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict (e.g., duplicate)
- **413 Payload Too Large**: File size exceeds limit
- **415 Unsupported Media Type**: Invalid file type
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Examples

**Authentication Error:**
```json
{
  "detail": "Invalid authentication credentials",
  "status_code": 401
}
```

**Validation Error:**
```json
{
  "detail": "Invalid media_type. Must be 'image' or 'video'",
  "status_code": 400,
  "field": "media_type"
}
```

**Not Found Error:**
```json
{
  "detail": "Media with UUID 550e8400-e29b-41d4-a716-446655440000 not found",
  "status_code": 404
}
```

---

## Rate Limiting

### Default Limits

- **Standard users**: 500 requests per hour
- **Premium users**: 2000 requests per hour
- **Upload endpoints**: 50 uploads per hour
- **Streaming**: No rate limit (bandwidth limited)

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 450
X-RateLimit-Reset: 1699880400
```

### Handling Rate Limits

When rate limit is exceeded, the API returns:

```json
{
  "detail": "Rate limit exceeded. Try again in 15 minutes.",
  "status_code": 429,
  "retry_after": 900
}
```

---

## Best Practices

### 1. Authentication

- Always include the JWT token in the `Authorization` header
- Refresh tokens before expiration
- Handle 401 errors by redirecting to login

### 2. Pagination

Use `limit` and `offset` for large result sets:

```bash
curl "http://localhost:8000/api/v1/media/search?limit=20&offset=40"
```

### 3. Error Handling

Implement proper error handling:

```python
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Media not found")
    elif e.response.status_code == 401:
        print("Authentication failed")
```

### 4. File Uploads

For large files, use chunked upload:

```python
with open('large_video.mp4', 'rb') as f:
    files = {'file': f}
    response = requests.post(url, files=files, headers=headers)
```

### 5. Streaming

For video playback, use range requests:

```python
headers = {
    'Authorization': f'Bearer {token}',
    'Range': 'bytes=0-1048576'
}
response = requests.get(stream_url, headers=headers, stream=True)
```

### 6. Bulk Operations

Use bulk endpoints for efficiency:

```python
# Instead of multiple single requests
for media_id in media_ids:
    update_media(media_id, metadata)

# Use bulk update
bulk_update_metadata(media_ids, metadata)
```

### 7. Caching

Implement client-side caching for:
- Thumbnails
- Media metadata
- Collection lists
- User preferences

### 8. Idempotency

For critical operations, implement retry logic with exponential backoff:

```python
import time

def upload_with_retry(file, max_retries=3):
    for attempt in range(max_retries):
        try:
            return upload_media(file)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
```

---

## Service Integration

### With Vision Service

The Media Service integrates with the Vision Service for face detection:

1. Upload video → Media Service
2. Media Service triggers → Vision Service (Enhanced Logic V2)
3. Vision Service processes → Stores results in Vision DB
4. Face detection results → Available via vmeta service

### With VMeta Service

For cross-video tracking and MVR-People operations:

1. Media Service proxies requests → vmeta service
2. Use `/mvr-people/batch-match-and-merge` for merging
3. vmeta handles individual tracking across videos

### With Gateway Service

All external requests should go through the Gateway:

```
Client → Gateway (8080) → Media Service (8000)
```

Gateway handles:
- Authentication
- Rate limiting
- Load balancing
- Request routing

---

## Performance Considerations

### 1. Thumbnail Generation

- Thumbnails are generated on-demand
- First request may be slower
- Subsequent requests are served from cache

### 2. Video Streaming

- Supports HTTP range requests
- Efficient for large video files
- Browser-compatible for HTML5 video

### 3. Bulk Operations

- Designed for processing up to 1000 items
- For larger batches, use workflow endpoints
- Monitor progress via status endpoints

### 4. Database Queries

- Search endpoints support pagination
- Use appropriate indexes
- Avoid fetching unnecessary fields

---

## Monitoring & Metrics

### Prometheus Metrics

Available at `/metrics`:

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration
- `media_uploads_total`: Total media uploads
- `storage_bytes_used`: Current storage usage
- `face_detection_workflows_active`: Active workflows

### Health Checks

Kubernetes-compatible health endpoints:

- `/health`: Basic health
- `/health/ready`: Readiness probe
- `/health/live`: Liveness probe
- `/health/detailed`: Comprehensive status

---

## Changelog

### Version 1.0.0 (Current)

**Features:**
- Complete media management API
- Collection organization
- Face detection workflows
- Storage management with multi-tier support
- Advanced metadata handling
- Video streaming with range support
- VMeta service integration
- Comprehensive security features

**Endpoints:** 102 total endpoints across 11 categories

---

## Support & Contact

For API support, issues, or questions:

- **Documentation**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc` (Alternative documentation)
- **OpenAPI Spec**: `/openapi.json`
- **GitHub**: [ppl-meta-platform](https://github.com/nickglezakos/ppl-meta-platform)

---

## Appendix

### Service Configuration

**Default Port:** 8000  
**API Version:** v1  
**Base Path:** `/api/v1`  
**Documentation:** `/docs`, `/redoc`

### Environment Variables

- `DATABASE_URL`: Database connection string
- `STORAGE_PATH`: Local storage path
- `CLOUD_STORAGE_ENABLED`: Enable cloud storage (true/false)
- `JWT_SECRET`: JWT signing secret
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Supported File Types

**Images:**
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- GIF (`.gif`)
- BMP (`.bmp`)
- WEBP (`.webp`)

**Videos:**
- MP4 (`.mp4`)
- AVI (`.avi`)
- MOV (`.mov`)
- MKV (`.mkv`)
- WEBM (`.webm`)

### Size Limits

- **Images**: 50 MB max
- **Videos**: 5 GB max
- **Metadata**: 1 MB max per item

---

**Last Updated:** November 12, 2025  
**API Version:** 1.0.0  
**Document Version:** 1.0
