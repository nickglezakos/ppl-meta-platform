# Proposal: Media Viewing Privacy Privilege

**Date:** 2026-03-17  
**Status:** Draft  
**Priority:** High  
**Affected Services:** ppl-meta-node, ppl-meta-gateway, ppl-meta-media, ppl-meta-frontend  

---

## 1. Overview

Introduce a **`media:view`** capability (privilege) that controls whether a user can see actual media content (images, video, thumbnails) throughout the application. The privilege is managed by **admin users** via the existing Role → Capability system in ppl-meta-node. When a user **lacks** the `media:view` capability, all media playback and image rendering is replaced with a branded placeholder showing the EyeNet logo and a "Media Privacy" message. Analytics screens remain accessible but best-frame and best-face images are also replaced with the placeholder.

**Key points:**
- Admin / owner users possess the capability by default.
- Regular users must be **explicitly granted** the `media:view` capability by an admin.
- The privilege is enforced both **server-side** (media service rejects file downloads) and **client-side** (frontend hides media UI).

---

## 2. Motivation

- **Access control** — Not every user should be able to view raw media. Admins decide who gets visual access.
- **Privacy compliance** — Restricts visual access to captured media while still allowing analytical review (counts, metadata, detection events).
- **Leverages existing infrastructure** — The platform already has a `Capability` model, `RoleCapability` join table, `user_has_capability()` dependency, and role-management API endpoints. This proposal adds one new capability row.
- **Extends existing "Privacy & Security" placeholder** — The profile screen already reserves a section for privacy features; this is the first concrete implementation.

---

## 3. Prerequisites — User & Role Setup

Before the `media:view` capability can be managed, the platform needs well-defined admin and non-admin users and the ability for admins to manage capabilities via the UI.

### 3.1 Seed Users on Startup (ppl-meta-node)

The node service startup (`main.py` → `init_guid_and_admin`) already creates `nick.glezakos@gmail.com` as the first user and assigns the `admin` role. Extend this block to also ensure the test user and the non-admin user exist:

| # | Email | Username | Admin? | Notes |
|---|-------|----------|--------|-------|
| 1 | `nick.glezakos@gmail.com` | `nick.glezakos@gmail.com` | **Yes** | Already seeded in startup. No change needed — `ensure_admin_role()` already runs. |
| 2 | `fresh.user@example.com` | `fresh.user@example.com` | **Yes** | Seed on startup if not present. Assign `admin` role via `ensure_admin_role()`. |
| 3 | `nick.glezakos@outlook.com` | `nick.glezakos@outlook.com` | **No** | Seed on startup if not present. Gets the default `user` role — **no** `media:view` capability. |

#### Backend change — `main.py` startup block

```python
# Existing admin user (nick.glezakos@gmail.com) — already handled above

# Ensure test admin user exists
test_admin_email = "fresh.user@example.com"
test_admin_user = get_user_by_email(db, test_admin_email)
if not test_admin_user:
    test_admin = UserCreate(
        username=test_admin_email,
        email=test_admin_email,
        password="TestUser@23",
    )
    create_user(db, test_admin)
    logger.info("Test admin user created.")
ensure_admin_role(db, test_admin_email)
logger.info("Test admin role ensured")

# Ensure non-admin user exists
nonadmin_email = "nick.glezakos@outlook.com"
nonadmin_user = get_user_by_email(db, nonadmin_email)
if not nonadmin_user:
    nonadmin = UserCreate(
        username=nonadmin_email,
        email=nonadmin_email,
        password="Viewer@23",
    )
    create_user(db, nonadmin)
    logger.info("Non-admin user created (no media:view).")
# NOTE: no ensure_admin_role() call — this user stays a regular "user"
```

### 3.2 Ensure `user` Role Exists

Add a `ensure_user_role()` function (or extend startup) so a `user` role is always seeded. Non-admin accounts are assigned this role on registration. The `user` role does **not** include `media:view` by default.

```python
def ensure_user_role(db: Session):
    """Ensure a default 'user' role exists for non-admin accounts."""
    user_role = get_role_by_name(db, "user")
    if not user_role:
        create_role(db, "user")
```

### 3.3 Admin-Only Users Screen — `http://localhost:3000/#/users`

**Current state:** The users list at `/users` (`UsersScreen`) shows user cards with avatar, username, email, and email verification badge. There is **no role/capability display** and **no tap action** on user rows.

**Required changes:**

1. **Show role badge** on each `_UserCard` (e.g. "Admin" chip in blue, "User" chip in grey).
2. **Make each user row tappable.** On tap, navigate to the profile screen scoped to the selected user:
   ```
   http://localhost:3000/#/profile?userId=<user_id>
   ```
3. **Restrict access** — only users with the `admin` role can see the `/users` route. Non-admin users who navigate here are redirected to `/home`.

#### Frontend changes — `users_screen.dart`

```dart
// In _UserCard, wrap with InkWell:
InkWell(
  onTap: () {
    // Admin taps a user → go to profile with userId param
    context.go('/profile?userId=${user.id}');
  },
  child: Card(
    // ... existing card content ...
    // Add role badge:
    Chip(
      label: Text(user.isAdmin ? 'Admin' : 'User'),
      backgroundColor: user.isAdmin
          ? Colors.blue.shade100
          : Colors.grey.shade200,
    ),
  ),
)
```

#### Frontend changes — `app_router.dart`

Update the `/profile` route to accept an optional `userId` query parameter:

```dart
GoRoute(
  path: '/profile',
  name: 'profile',
  builder: (context, state) {
    final userId = state.uri.queryParameters['userId'];
    return ProfileScreen(targetUserId: userId);
  },
),
```

### 3.4 Profile Screen as Capability Manager — `http://localhost:3000/#/profile`

**Current state:** The profile screen (`ProfileScreen`) shows the **current user's** info: avatar, username, email, verification badge, member-since date, and a settings list (Edit Profile, Change Password, Notifications, Privacy & Security, etc.). The "Privacy & Security" option shows a "coming soon!" snackbar.

**Required changes:**

#### 3.4.1 Dual mode — self-view vs admin-managing-another-user

| Mode | URL | Behaviour |
|------|-----|-----------|
| **Self** | `/profile` (no `userId` param) | Shows the logged-in user's own profile. Read-only capability display. |
| **Admin managing user** | `/profile?userId=42` | Admin sees the target user's profile with **editable capability toggles**. |

#### 3.4.2 Capabilities Section (replaces "Privacy & Security" placeholder)

Replace the "coming soon!" snackbar in the **Privacy & Security** settings option with a real capabilities panel:

```
┌──────────────────────────────────────────────┐
│  Capabilities                                │
│  ──────────────────────────────────────────── │
│  ☑  media:view     Media viewing access      │
│  ☐  media:delete   Media deletion access     │  ← future capabilities
│  ☑  system:admin   Full admin access         │
│  ──────────────────────────────────────────── │
│  (toggles enabled only when admin is         │
│   managing another user)                     │
└──────────────────────────────────────────────┘
```

- **Self-view:** Capabilities shown as read-only chips/badges. User cannot modify their own capabilities.
- **Admin-managing-user:** Each capability has a toggle switch. Admin can enable/disable `media:view` (and future capabilities) for the target user.
- Toggling a capability calls the existing backend APIs:
  - **Enable:** `POST /roles/add-capability/` with `{ role_id, capability_id }`
  - **Disable:** `POST /roles/remove-capability/` with `{ role_id, capability_id }`

#### 3.4.3 Frontend User Model Extension

The `User` class in `core/models/user.dart` currently has no role/capability fields. Extend it:

```dart
class User {
  final int id;
  final String username;
  final String email;
  final bool emailVerified;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  // New fields:
  final List<String> roles;
  final List<String> capabilities;

  bool get isAdmin => roles.contains('admin');
  bool get canViewMedia => capabilities.contains('media:view');
}
```

#### 3.4.4 Fetch Capabilities with User Data

Add a provider that calls `/api/v1/users/user-permissions/{user_id}` to get roles + capabilities for a given user. Cache in the user state on login, and re-fetch when an admin opens another user's profile.

### 3.5 Summary of Changes in This Section

| Area | File / Component | Change |
|------|-----------------|--------|
| **Node startup** | `main.py` | Seed `fresh.user@example.com` (admin) and `nick.glezakos@outlook.com` (non-admin) |
| **Node startup** | `role_service.py` | Add `ensure_user_role()` |
| **Frontend model** | `core/models/user.dart` | Add `roles`, `capabilities`, `isAdmin`, `canViewMedia` |
| **Frontend routing** | `app_router.dart` | `/profile` accepts optional `userId` query param |
| **Frontend users** | `users_screen.dart` | Role badge on cards, tappable rows → navigate to `/profile?userId=` |
| **Frontend profile** | `profile_screen.dart` | Dual-mode (self / admin-managing), capabilities panel with toggles |
| **Frontend auth** | Auth provider | Fetch capabilities on login, cache in state |

---

## 4. User Experience — Media Privacy

### 4.1 Admin Workflow (privilege assignment)

1. Admin navigates to **User Management** (or uses API directly).
2. Admin selects a user → **Manage Roles / Capabilities**.
3. Admin assigns the `media:view` capability to the user's role (or creates a role that includes it).
4. The user's frontend session picks up the new capability on next token refresh or re-login.

> The admin (owner) role already includes all capabilities (`permissions: ["*"]` on bootcore / `system:admin` on media service). The `media:view` capability is seeded into the `admin` role automatically during migration.

### 4.2 Regular User — Without `media:view`

| Screen / Component | Current Behaviour | New Behaviour (no capability) |
|--------------------|-------------------|----------------------------|
| **Media Preview Screen** (`EnhancedMediaPreviewScreen`) | Video/image playback via `SmartVideoPlayerWidget` / `VideoPlayerWidget` | Placeholder image (EyeNet logo + "Media Privacy" label). No playback initialised. |
| **Gallery Screen** (`GalleryScreen` / `ResponsiveMediaGallery`) | Thumbnail grid with cached network images | Each thumbnail replaced with the placeholder. |
| **Collections Screen** (`CollectionsScreen`) | Collection cover images and media grid | Placeholder in place of every media thumbnail and cover image. |
| **Snapshot Gallery** (`SnapshotGalleryScreen` / `SnapshotGalleryWidget`) | Camera snapshot thumbnails | Placeholder per snapshot cell. |
| **Analysis Detail – Best Frames** (`MVRFrameThumbnail`) | Frame image with quality score | Placeholder image; quality score badge still visible. |
| **Analysis Detail – Best Faces** (`MVRFaceThumbnail`) | Face crop with quality badge | Placeholder image; quality badge still visible. |
| **Person Objects Detail** (`PersonObjectsDetailScreen`) | Person images / crops | Placeholder per image. |
| **Face Detection Overlays** (`FaceDetectionOverlay`, `VideoFaceDetectionOverlay`, `SimpleVideoFaceDetectionOverlay`) | Overlay rectangles on video/image | Overlay hidden (no underlying media visible). |
| **Vision Results Dialog** (`VisionResultsDialog`) | Summary with thumbnail | Placeholder thumbnail. |
| **Draggable Media Item** (`DraggableMediaItem`) | Draggable thumbnail | Placeholder thumbnail; drag-and-drop still functional. |
| **Media Details Dialog** (`MediaDetailsDialog`) | Media preview + metadata | Placeholder instead of preview; metadata still shown. |
| **MJPEG Player** (`MjpegVideoPlayer`) | Live MJPEG stream | Placeholder; stream not connected. |

### 4.3 What Remains Visible (even without `media:view`)

- All **text metadata** (filename, date, duration, size, tags, collections).
- All **analytics numbers** (face count, person count, quality scores, MVR metrics).
- **Navigation and actions** (details button, collection assignment, search, filters).
- **Detection event lists and logs**.
- **Share/delete actions** are hidden when the user lacks `media:view` (they can't see what they're sharing).

### 4.4 Profile Screen — Privacy Status (read-only indicator)

Non-admin users see a **read-only** indicator in Profile → Privacy & Security:
 
```
Media Viewing: Restricted
Contact your administrator to request media viewing access.
```

Admin users see their own status as **Enabled** (non-toggleable — it's always on for admins).

---

## 5. Technical Design

### 5.1 Backend — New Capability (ppl-meta-node)

#### 5.1.1 Database Migration

Seed a new row in the `capabilities` table:

```sql
INSERT INTO capabilities (name) VALUES ('media:view') ON CONFLICT DO NOTHING;
```

#### 5.1.2 Assign to Admin Role on Startup

Extend `ensure_admin_role()` in `role_service.py`:

```python
def ensure_admin_capabilities(db: Session):
    """Ensure the admin role has all platform capabilities including media:view."""
    admin_role = get_role_by_name(db, "admin")
    if not admin_role:
        return

    media_view_cap = db.query(Capability).filter(Capability.name == "media:view").first()
    if not media_view_cap:
        media_view_cap = Capability(name="media:view")
        db.add(media_view_cap)
        db.commit()
        db.refresh(media_view_cap)

    # Ensure admin role has it
    existing = db.query(RoleCapability).filter_by(
        role_id=admin_role.id, capability_id=media_view_cap.id
    ).first()
    if not existing:
        add_capability_to_role(db, admin_role.id, media_view_cap.id)
```

#### 5.1.3 Expose Capabilities in JWT / User-Info

The existing `/api/v1/users/user-permissions/{user_id}` endpoint already returns the user's capabilities list. The frontend reads this on login and caches it. No changes needed here.

#### 5.1.4 Capability Check Dependency (already exists)

```python
# Existing in capabilites_service.py — reuse as-is
media_view_required = user_has_capability("media:view")
```

### 5.2 Backend — Server-Side Enforcement (ppl-meta-media)

#### 5.2.1 Add `media:view` to RBAC Roles

Update `RoleBasedAccessControl.ROLES` in `security/auth.py`:

```python
ROLES = {
    "admin": {
        "permissions": {
            # ... existing ...
            "media:view",        # <-- add
        }
    },
    "user": {
        "permissions": {
            # ... existing ...
            # NOTE: "media:view" is NOT included by default for "user" role.
            # It must be explicitly granted via the Capability system.
        }
    },
    "viewer": {
        "permissions": {
            "media:read",        # metadata only
            "collection:read",
            "share:read_shared",
            # NO "media:view" — can see listings but not actual file bytes
        }
    },
    "guest": {
        "permissions": {"media:read_public", "collection:read_public"}
    },
}
```

#### 5.2.2 Guard File-Download Endpoints

On media download / stream / thumbnail endpoints, check for `media:view`:

```python
@router.get("/files/{media_id}/download")
async def download_media(
    media_id: str,
    current_user = Depends(get_current_user),
):
    # Check media:view capability
    if not has_capability(current_user, "media:view"):
        raise HTTPException(status_code=403, detail="Media viewing not permitted")
    # ... existing download logic ...
```

This ensures even if someone bypasses the frontend, they cannot fetch raw media bytes without the privilege.

### 5.3 Backend — Gateway Passthrough (ppl-meta-gateway)

No changes required. The gateway already forwards auth tokens to downstream services. The `media:view` check happens at the media service level.

### 5.4 Frontend — Capability Provider

#### 5.4.1 User Capabilities Provider

**File:** `lib/core/providers/features_providers.dart`

Add a provider that reads the user's capabilities from the auth state:

```dart
/// Whether the current user has the media:view capability.
/// Derived from the user's roles/capabilities fetched at login.
final mediaViewingEnabledProvider = Provider<bool>((ref) {
  final userCapabilities = ref.watch(userCapabilitiesProvider);
  return userCapabilities.contains('media:view');
});
```

#### 5.4.2 Fetch Capabilities on Login

On successful login, call the `/api/v1/users/user-permissions/{user_id}` endpoint and cache the returned `capabilities` list in the auth state / secure storage.

**File:** `lib/providers/auth_provider.dart` (or equivalent)

```dart
// After successful login:
final permissionsResponse = await apiClient.get(
  '/api/v1/users/user-permissions/${user.id}',
);
final capabilities = List<String>.from(
  permissionsResponse.data['capabilities'].map((c) => c['name']),
);
state = state.copyWith(capabilities: capabilities);
```

### 5.5 Frontend — Placeholder Widget

Create a reusable widget (unchanged from v1):

**File:** `lib/widgets/media_privacy_placeholder.dart`

```dart
class MediaPrivacyPlaceholder extends StatelessWidget {
  final double? width;
  final double? height;
  final BoxFit fit;

  const MediaPrivacyPlaceholder({
    super.key,
    this.width,
    this.height,
    this.fit = BoxFit.contain,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      color: Theme.of(context).colorScheme.surfaceVariant,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Image.asset(
            'assets/images/eyenet-logo.png',
            width: 64,
            height: 64,
            fit: BoxFit.contain,
          ),
          const SizedBox(height: 12),
          Text(
            'Media Privacy',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
```

### 5.6 Frontend — Integration Points

Each affected widget reads `mediaViewingEnabledProvider` and conditionally renders:

```dart
final canViewMedia = ref.watch(mediaViewingEnabledProvider);

if (!canViewMedia) {
  return MediaPrivacyPlaceholder(
    width: thumbnailSize,
    height: thumbnailSize,
  );
}
// ... normal media rendering ...
```

#### Frontend files to modify

| File | Change |
|------|--------|
| `lib/core/providers/features_providers.dart` | Add `mediaViewingEnabledProvider` from capabilities |
| `lib/providers/auth_provider.dart` (or equivalent) | Fetch & cache user capabilities on login |
| `lib/screens/media_preview_screen.dart` | Guard playback with capability check |
| `lib/widgets/video_player_widget.dart` | Return placeholder when no capability |
| `lib/widgets/smart_video_player_widget.dart` | Return placeholder when no capability |
| `lib/widgets/media/mjpeg_video_player.dart` | Return placeholder when no capability |
| `lib/screens/gallery_screen.dart` | Pass flag to gallery grid |
| `lib/widgets/responsive_media_gallery.dart` | Replace thumbnails with placeholder |
| `lib/screens/collections_screen.dart` | Replace collection cover + grid thumbnails |
| `lib/widgets/mvr_face_thumbnail.dart` | Replace face/frame images with placeholder |
| `lib/screens/person_objects_detail_screen.dart` | Replace person images with placeholder |
| `lib/widgets/face_detection_overlay.dart` | Hide overlay when media hidden |
| `lib/widgets/video_face_detection_overlay.dart` | Hide overlay when media hidden |
| `lib/widgets/simple_video_face_detection_overlay.dart` | Hide overlay when media hidden |
| `lib/widgets/vision_results_dialog.dart` | Replace thumbnail with placeholder |
| `lib/widgets/draggable_media_item.dart` | Replace child thumbnail with placeholder |
| `lib/widgets/media_details_dialog.dart` | Replace preview with placeholder |
| `lib/presentation/screens/camera/snapshot_gallery_screen.dart` | Replace snapshot thumbnails |
| `lib/presentation/widgets/camera/snapshot_gallery_widget.dart` | Replace snapshot thumbnails |
| `lib/screens/profile_screen.dart` | Show capability status in Privacy section |
| `lib/presentation/pages/profile_page.dart` | Show capability status in Privacy section |

### 5.7 Admin UI — Assign Capability to Users

Extend the existing User Management screen (or add one if it only exists via API) so admins can:

1. View a user's current roles and capabilities.
2. Toggle the `media:view` capability on/off for a role or directly for a user.

This uses the existing API endpoints:
- `POST /roles/add-capability/` — `{ role_id, capability_id }`
- `POST /roles/remove-capability/` — `{ role_id, capability_id }`

---

## 6. Capability Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  Startup (ppl-meta-node)                                        │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ ensure_admin_capabilities()                          │       │
│  │  → INSERT capability "media:view" if not exists      │       │
│  │  → Assign to "admin" role if not already assigned    │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Admin assigns capability to a user's role                     │
│  POST /roles/add-capability/  { role_id, capability_id }       │
│  OR                                                             │
│  Admin creates a "media-viewer" role with media:view and       │
│  assigns it to the user via POST /roles/assign/                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  User logs in (frontend)                                       │
│  → GET /api/v1/users/user-permissions/{user_id}                │
│  → Response: { capabilities: ["media:view", ...] }             │
│  → Cached in auth state                                        │
│  → mediaViewingEnabledProvider = capabilities.contains(...)    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  User navigates app                                            │
│  ┌─ Has media:view? ───────── YES → normal media rendering     │
│  └─ No ────────────────────────── → MediaPrivacyPlaceholder    │
│                                                                 │
│  User tries to download/stream (API)                           │
│  ┌─ Has media:view? ───────── YES → serve file bytes           │
│  └─ No ────────────────────────── → 403 Forbidden              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Edge Cases

| Scenario | Resolution |
|----------|------------|
| Admin revokes `media:view` while user is logged in | Frontend checks on each screen render; server rejects media API calls immediately. User sees placeholder on next navigation. Force-refresh capabilities on 403. |
| Admin grants `media:view` while user is logged in | User must refresh capabilities (pull-to-refresh on profile, or automatic periodic refresh). |
| User tries to share media without `media:view` | Share button hidden. Server-side 403 if attempted directly. |
| User opens a deep link to a media item | Placeholder shown if no capability; metadata still visible. |
| Network image cache (`cached_network_image`) | Skip loading entirely when capability is absent — no bandwidth wasted. |
| Search results | Thumbnails in search results also show placeholder. |
| Drag-and-drop organisation | Placeholder is draggable; drop target behaviour unchanged. |
| Migration — existing users | Existing admin/owner roles get `media:view` on startup. Existing regular users do **not** — admin must explicitly grant. |

---

## 8. Acceptance Criteria

1. `nick.glezakos@gmail.com` is seeded as an admin user on startup with the `admin` role.
2. `fresh.user@example.com` is seeded as an admin user on startup with the `admin` role.
3. `nick.glezakos@outlook.com` is seeded as a non-admin user on startup — **no** `media:view` capability.
4. A `media:view` capability exists in the database, auto-assigned to the `admin` role on startup.
5. At `http://localhost:3000/#/users`, admin users see a list of all users with role badges. Each row is tappable.
6. Tapping a user row at `/users` navigates to `http://localhost:3000/#/profile?userId=<id>` where the admin can manage that user's capabilities.
7. At `http://localhost:3000/#/profile`, the capabilities section (under Privacy & Security) shows `media:view` and other capabilities.
8. Admin users can toggle `media:view` on/off for any user via the profile screen.
9. Non-admin users see their own capabilities as read-only on their profile.
10. Users **without** `media:view` see the EyeNet-branded placeholder in **all** media views: gallery, collections, media preview, snapshots, best frames, best faces, and person objects.
11. Users **with** `media:view` see media normally — no behaviour change.
12. Analytics data (counts, scores, metadata) remain fully visible regardless of capability.
13. The "Details" button on a media item remains functional and opens the analysis/metadata view.
14. Media file download/stream API endpoints return **403** for users without `media:view`.
15. No network requests are made to fetch media assets on the frontend when the user lacks the capability.
16. Granting/revoking the capability takes effect without requiring app reinstall (at most a re-login or capability refresh).
17. Non-admin users cannot access the `/users` route — they are redirected to `/home`.

---

## 9. Testing Plan

| Test | Type | Scope | Description |
|------|------|-------|-------------|
| Admin users seeded | Unit | Node | `nick.glezakos@gmail.com` and `fresh.user@example.com` exist with `admin` role after startup. |
| Non-admin user seeded | Unit | Node | `nick.glezakos@outlook.com` exists with `user` role, no `media:view`. |
| Capability seeded | Unit | Node | `media:view` capability exists after startup migration. |
| Admin role has capability | Unit | Node | Admin role includes `media:view` after `ensure_admin_capabilities()`. |
| Regular user lacks capability | Unit | Node | Newly created user with "user" role does not have `media:view`. |
| Capability grant/revoke API | Integration | Node | `POST /roles/add-capability/` and `/remove-capability/` work for `media:view`. |
| Media download blocked | Integration | Media | `GET /files/{id}/download` returns 403 for user without `media:view`. |
| Media download allowed | Integration | Media | `GET /files/{id}/download` returns 200 for user with `media:view`. |
| Users screen — admin access | Widget | Frontend | Admin user sees user list with role badges at `/users`. |
| Users screen — non-admin blocked | Widget | Frontend | Non-admin user is redirected away from `/users`. |
| User row tap → profile | Widget | Frontend | Tapping user row navigates to `/profile?userId=<id>`. |
| Profile — self view | Widget | Frontend | Own profile shows capabilities as read-only. |
| Profile — admin manages user | Widget | Frontend | Admin viewing another user's profile can toggle `media:view`. |
| Capabilities fetched on login | Integration | Frontend | `/user-permissions/{id}` response is cached in auth state. |
| Placeholder renders | Widget | Frontend | `MediaPrivacyPlaceholder` shows logo + text at various sizes. |
| Gallery hides thumbnails | Widget | Frontend | `ResponsiveMediaGallery` shows placeholders when capability absent. |
| Video player not initialised | Widget | Frontend | `VideoPlayerWidget` does not create a controller when capability absent. |
| Best faces placeholder | Widget | Frontend | `MVRFaceThumbnail` shows placeholder; quality badge still visible. |
| Best frames placeholder | Widget | Frontend | `MVRFrameThumbnail` shows placeholder; quality badge still visible. |
| Collections placeholder | Widget | Frontend | `CollectionsScreen` media grid shows placeholders. |
| No network fetches | Integration | Frontend | Confirm no media URLs are requested when capability absent. |
| Capability revoked mid-session | E2E | Full stack | Admin revokes → user gets 403 on next media request → frontend shows placeholder after refresh. |

---

## 10. Estimated Scope

| Area | New Files | Modified Files | Risk |
|------|-----------|----------------|------|
| **ppl-meta-node** | 0 | 3 (main.py seed users, role_service.py ensure caps + user role, capabilites_service.py) | Low — adds seed data and one capability row |
| **ppl-meta-media** | 0 | 2 (auth.py, file endpoints) | Low — adds one permission check |
| **ppl-meta-frontend** | 1 (placeholder widget) | ~25 (user model, users screen, profile screen, router, auth provider, ~20 media UI files) | Medium — user management UI is new but uses existing API endpoints |

---

## 11. Future Enhancements

- **PIN/biometric prompt** before revealing media for users who *have* the capability (additional local protection).
- **Granular privacy** — per-collection or per-camera `media:view` scoping.
- **Audit logging** — log when `media:view` is granted/revoked and by whom.
- **Time-limited access** — grant `media:view` for a window (e.g. 24 h) then auto-revoke.
