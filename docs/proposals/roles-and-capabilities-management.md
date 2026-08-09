# Roles and Capabilities Management — Frontend Implementation Proposal

**Date**: 09 August 2026  
**Status**: Draft  
**Depends On**: [docs/modules/users/ROLES_AND_CAPABILITIES.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/modules/users/ROLES_AND_CAPABILITIES.md), [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md)  
**Target**: `ppl-meta-frontend` (Flutter / Riverpod / GoRouter)

---

## Purpose

The EyeNet Node backend provides a complete Role-Based Access Control (RBAC) system — system roles, custom roles, capabilities, user-role assignment, and role-capability assignment — all with a full REST API. However, the Flutter frontend currently has **no administrative surface** for managing this RBAC system. Roles and capabilities can only be created or assigned via direct API calls or backend scripts.

This proposal defines the **full frontend implementation** for the roles and capabilities lifecycle, wired into existing Flutter views wherever possible:

1. What backend APIs already exist and what the frontend needs to call
2. What views need to be created vs modified vs reused
3. What services, providers, and models need to be added
4. How the new views wire into the existing GoRouter navigation
---

## 1. Current State Assessment

### 1.1 Backend — What Exists

The Node service (`ppl-meta-node`) exposes the following RBAC API surface:

| API Group | Endpoints | Status |
|-----------|-----------|--------|
| **Roles CRUD** | `POST/GET/PUT/DELETE /roles/` + `/roles/by-name/{name}` | ✅ Implemented, capability-protected |
| **User-Role Assignment** | `POST /roles/assign/`, `POST /roles/unassign/` | ✅ Implemented, capability-protected |
| **Role-Capability Assignment** | `POST /roles/add-capability/`, `POST /roles/remove-capability/` | ✅ Implemented, capability-protected |
| **Capability Queries** | `GET /capabilities/by-role/{id}`, `/by-user/{id}`, `/my-capabilities` | ✅ Implemented, capability-protected |
| **User Profile** | `GET /api/v1/users/profile`, `/user-profile/{id}`, `/toggle-capability/{id}` | ✅ Implemented, capability-protected |
| **Users List** | `GET /api/v1/users/` | ✅ Implemented |
| **User Actions (Audit)** | `GET /actions/` | ✅ Implemented |

**Backend capability enforcement is already in place.** Every role/capability management endpoint requires a specific capability (e.g., `auth.roles.create`, `auth.capabilities.assign`). An owner or admin with these capabilities can already make all calls; the frontend just needs to surface the UI.

### 1.2 Frontend — What Exists Today

| Component | File | What it does | Gaps |
|-----------|------|-------------|------|
| **User model** | `lib/core/models/user.dart` | Has `roles` and `capabilities` fields, `isAdmin` getter | No `canManageRoles`, `canAssignRoles` helpers |
| **UsersService** | `lib/core/services/users_service.dart` | Only `getUsers()` with pagination | No role/capability CRUD, no toggle, no assignment |
| **UsersProvider** | `lib/core/providers/users_provider.dart` | Loads user list, loading/error state | No per-user detail, no role/capability state |
| **UsersScreen** | `lib/presentation/screens/users/users_screen.dart` | Lists users with cards, navigates to profile | No role/capability badges, no filtering, no admin actions |
| **ProfileScreen** | `lib/screens/profile_screen.dart` | Own profile + admin view with roles chips and single `media:view` toggle | Only one hardcoded capability toggle, no role assignment UI, no full capability list |
| **AuthProvider** | `lib/core/providers/auth_provider.dart` | Auth state, login/logout, current user | No capability check helpers |
| **GoRouter** | `lib/presentation/navigation/app_router.dart` | Routes: `/home`, `/users`, `/profile`, `/cameras`, etc. | No roles/capabilities routes |

### 1.3 The Gap

The backend can do everything. The frontend cannot. An admin today must:

- Use curl or Swagger UI to assign roles
- Run Python scripts to add capabilities
- Manually call the toggle-capability endpoint

This proposal bridges that gap.

---

## 2. Target UX Architecture

### 2.1 View Map

```
┌────────────────────────────────────────────────────────────────┐
│                        NAVIGATION                              │
├────────────┬────────────┬─────────────┬───────────┬───────────┤
│   Home     │  Users  ✦  │  Roles  ✦   │ Cameras   │  ...      │
│  (exist)   │ (enhanced) │   (NEW)     │  (exist)  │           │
└────────────┴──────┬──────┴──────┬──────┴───────────┴───────────┘
                    │              │
          ┌─────────▼─────────┐   │
          │ User Profile   ✦  │   │
          │ (enhanced)        │   │
          │ ┌───────────────┐ │   │
          │ │ Roles assign  │ │   │
          │ │ Caps toggle   │ │   │
          │ │ Set password  │ │   │
          │ └───────────────┘ │   │
          └───────────────────┘   │
                    ┌─────────────▼─────────────┐
                    │  Roles Management     ✦   │
                    │  (NEW)                    │
                    │ ┌───────────────────────┐ │
                    │ │ Role CRUD             │ │
                    │ │ Capabilities per role │ │
                    │ │ Users per role        │ │
                    │ │ Assign/unassign caps  │ │
                    │ └───────────────────────┘ │
                    └───────────────────────────┘

  ✦ = modified or new in this proposal
```

### 2.2 Views to Build or Modify

| # | View | Action | Description |
|---|------|--------|-------------|
| **A** | Users List Screen | **Modify** | Add role/capability badges, role filter chips, quick-actions |
| **B** | User Profile Screen | **Modify** | Full capability toggle list, role assignment panel, role removal |
| **C** | Roles Management Screen | **New** | List all roles, create/rename/delete, user counts, tap to detail |
| **D** | Role Detail View | **New** | Capabilities for role (toggle on/off), users assigned, add/remove |
| **E** | Capability Assign Dialog | **New** | Reusable dialog for assigning capabilities to a role |
| **F** | Role Assign Dialog | **New** | Reusable dialog for assigning/unassigning roles to a user |
| **G** | Audit Log Tab | **New** | Filterable log of role/capability/user changes from `user_actions` |

---

## 3. Data Layer — New Services and Providers

### 3.1 RolesService

**File:** `lib/core/services/roles_service.dart`

```dart
class RolesService {
  final ApiClient _apiClient;

  // CRUD
  Future<List<Role>> getRoles();
  Future<Role> getRoleById(int roleId);
  Future<Role> getRoleByName(String name);
  Future<Role> createRole(String name);
  Future<Role> updateRole(int roleId, String newName);
  Future<void> deleteRole(int roleId);

  // User-Role assignment
  Future<void> assignRoleToUser(int userId, int roleId);
  Future<void> unassignRoleFromUser(int userId, int roleId);

  // Role-Capability assignment
  Future<void> addCapabilityToRole(int roleId, int capabilityId);
  Future<void> removeCapabilityFromRole(int roleId, int capabilityId);

  // Queries
  Future<Map<String, dynamic>> getRolesAndCapabilitiesForUser(int userId);
  Future<List<Capability>> getCapabilitiesByRole(int roleId);
}
```

**API mappings:**

| Method | Endpoint | Required Capability (backend enforces) |
|--------|----------|--------------------------------------|
| `getRoles` | `GET /roles/` | `auth.roles.read` |
| `getRoleById` | `GET /roles/{roleId}` | `auth.roles.read` |
| `getRoleByName` | `GET /roles/by-name/{name}` | `auth.roles.read` |
| `createRole` | `POST /roles/` | `auth.roles.create` |
| `updateRole` | `PUT /roles/{roleId}` | `auth.roles.update` |
| `deleteRole` | `DELETE /roles/{roleId}` | `auth.roles.delete` |
| `assignRoleToUser` | `POST /roles/assign/?user_id=&role_id=` | `auth.roles.assign` |
| `unassignRoleFromUser` | `POST /roles/unassign/?user_id=&role_id=` | `auth.roles.unassign` |
| `addCapabilityToRole` | `POST /roles/add-capability/` | `auth.capabilities.assign` |
| `removeCapabilityFromRole` | `POST /roles/remove-capability/` | `auth.capabilities.unassign` |
| `getRolesAndCapabilitiesForUser` | `GET /capabilities/by-user/{userId}` | `users.accounts.read` |
| `getCapabilitiesByRole` | `GET /capabilities/by-role/{roleId}` | `auth.capabilities.read` |

### 3.2 CapabilitiesService

**File:** `lib/core/services/capabilities_service.dart`

```dart
class CapabilitiesService {
  final ApiClient _apiClient;

  Future<List<String>> getMyCapabilities();
  Future<List<Capability>> getCapabilitiesByRole(int roleId);
  Future<Map<String, dynamic>> getRolesAndCapabilitiesForUser(int userId);
}
```

### 3.3 RolesProvider

**File:** `lib/core/providers/roles_provider.dart`

```dart
class RolesState {
  final List<Role> roles;
  final Role? selectedRole;
  final List<Capability> selectedRoleCapabilities;
  final List<User> selectedRoleUsers;
  final bool isLoading;
  final String? error;
}

class RolesNotifier extends StateNotifier<RolesState> {
  Future<void> loadRoles();
  Future<void> selectRole(int roleId);
  Future<void> createRole(String name);
  Future<void> updateRole(int roleId, String newName);
  Future<void> deleteRole(int roleId);
  Future<void> assignRoleToUser(int userId, int roleId);
  Future<void> unassignRoleFromUser(int userId, int roleId);
  Future<void> addCapabilityToRole(int roleId, int capabilityId);
  Future<void> removeCapabilityFromRole(int roleId, int capabilityId);
}
```

### 3.4 CapabilitiesProvider

**File:** `lib/core/providers/capabilities_provider.dart`

```dart
class CapabilitiesState {
  final List<Capability> allCapabilities;
  final List<String> myCapabilities;
  final bool isLoading;
  final String? error;
}

class CapabilitiesNotifier extends StateNotifier<CapabilitiesState> {
  Future<void> loadAllCapabilities();
  Future<void> loadMyCapabilities();
  Future<List<Capability>> getCapabilitiesByRole(int roleId);
}
```

### 3.5 Enhanced UsersProvider

Add to existing `UsersProvider`:

```dart
class UsersNotifier extends StateNotifier<UsersState> {
  // Existing: loadUsers, refreshUsers, clearError

  // New:
  Future<UserDetail> loadUserDetail(int userId);
  Future<void> toggleUserCapability(int userId, String capability, bool enabled);
  Future<void> assignRoleToUser(int userId, int roleId);
  Future<void> unassignRoleFromUser(int userId, int roleId);
}
```

### 3.6 Role Model

**File:** `lib/core/models/role.dart` (NEW)

```dart
@JsonSerializable()
class Role {
  final int id;
  final String name;

  const Role({required this.id, required this.name});

  bool get isSystemRole => name == 'owner' || name == 'admin' || name == 'user';

  factory Role.fromJson(Map<String, dynamic> json) => _$RoleFromJson(json);
  Map<String, dynamic> toJson() => _$RoleToJson(this);
}
```

### 3.7 Capability Model

**File:** `lib/core/models/capability.dart` (NEW)

```dart
@JsonSerializable()
class Capability {
  final int id;
  final String name;

  const Capability({required this.id, required this.name});

  /// Derive namespace from name: "auth.roles.create" → "auth", "cameras:view" → "cameras"
  String get namespace {
    if (name.contains(':')) return name.split(':').first;
    if (name.contains('.')) return name.split('.').first;
    return 'other';
  }

  factory Capability.fromJson(Map<String, dynamic> json) => _$CapabilityFromJson(json);
  Map<String, dynamic> toJson() => _$CapabilityToJson(this);
}
```

> **Note:** The backend does not return `namespace` or `description` fields. The frontend derives `namespace` from the name and uses a static lookup map for human-readable descriptions (see §9).

### 3.8 User Model Enhancements

Add to existing `User` model in `lib/core/models/user.dart`:

```dart
// New capability-check helpers
bool get isOwner => roles.contains('owner');
bool get canManageRoles =>
    capabilities.contains('auth.roles.read') ||
    capabilities.contains('auth.roles.create') ||
    capabilities.contains('auth.roles.update') ||
    capabilities.contains('auth.roles.delete') ||
    capabilities.contains('auth.roles.assign') ||
    capabilities.contains('auth.roles.unassign');
bool get canManageCapabilities =>
    capabilities.contains('auth.capabilities.read') ||
    capabilities.contains('auth.capabilities.assign') ||
    capabilities.contains('auth.capabilities.unassign') ||
    capabilities.contains('auth.capabilities.manage');
bool get canManageUsers =>
    capabilities.contains('users.accounts.read') ||
    capabilities.contains('users.accounts.create') ||
    capabilities.contains('users.accounts.update') ||
    capabilities.contains('users.accounts.disable') ||
    capabilities.contains('users.accounts.delete');
```

---

## 4. View Designs

### 4.1 View A: Enhanced Users List Screen

**Modify:** `lib/presentation/screens/users/users_screen.dart`

**Current behavior:** Lists users as cards with username + email. Tap navigates to `/profile?userId=X`.

**Target behavior:**

```
┌──────────────────────────────────────────┐
│  CustomAppBar(title: "Users")            │
├──────────────────────────────────────────┤
│  [All] [owner] [admin] [user] [custom]   │  ← Role filter chips
├──────────────────────────────────────────┤
│  ┌────────────────────────────────────┐  │
│  │ 👤 nick.glezakos@gmail.com         │  │
│  │    Roles: [admin] [user]           │  │  ← Role badges
│  │    Caps: 19 capabilities           │  │
│  │                          [View →] │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 👤 fresh.user@example.com           │  │
│  │    Roles: [owner] [admin] [user]   │  │
│  │    Caps: 30 capabilities           │  │
│  │                          [View →] │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**Implementation details:**

- Add `List<String>` state field for active role filter
- Filter users client-side by role based on `user.roles`
- Each user card shows: avatar (first letter of email), email + username, role chips (owner=amber, admin=deepPurple, user=blue, custom=grey), capability count badge
- Tap navigates to `/profile?userId=X` (existing route)
- Pull-to-refresh triggers `loadUsers()`
- **Visibility:** Only users with `users.accounts.read`. Backend enforces; frontend hides nav item if lacking.

### 4.2 View B: Enhanced User Profile Screen

**Modify:** `lib/screens/profile_screen.dart`

**Current behavior:** Own profile shows account info + change password. Admin mode shows target user's roles as chips + single `media:view` toggle.

**Target behavior (Admin mode):**

```
┌──────────────────────────────────────────┐
│  CustomAppBar(title: "User Profile")     │
├──────────────────────────────────────────┤
│  ┌────────────────────────────────────┐  │
│  │  Profile Header (avatar, email)    │  │  ← Existing
│  └────────────────────────────────────┘  │
│  Account Info                            │  ← Existing
│                                          │
│  ── ROLES ─────────────────── [+ Assign] │  ← NEW button
│  [owner] [admin] [user]          ✕ ✕ ✕  │  ← Each chip has remove (✕)
│                                          │
│  ── CAPABILITIES ──────────────────────  │
│  ┌─ Auth & Session ───────────────────┐  │
│  │ [✓] auth.session.use               │  │  ← Grouped by namespace
│  │ [✓] auth.roles.read                │  │
│  │ [ ] auth.roles.create    (owner)   │  │  ← Greyed if user can't toggle
│  └────────────────────────────────────┘  │
│  ┌─ Users ────────────────────────────┐  │
│  │ [✓] users.profile.read             │  │
│  │ [ ] users.accounts.delete (owner)  │  │
│  └────────────────────────────────────┘  │
│  ┌─ Cameras ──────────────────────────┐  │
│  │ [✓] cameras:view                   │  │
│  │ [ ] cameras:admin                  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ── ADMIN ACTIONS ─────────────────────  │
│  [Set Password]                          │  ← Existing
│  [Disable Account]                       │  ← NEW
│  [Delete User]                           │  ← NEW (owner only)
└──────────────────────────────────────────┘
```

**Key changes:**

1. **Replace hardcoded `media:view` toggle** with a dynamic list from the user's capabilities + full capability registry
2. **Group capabilities by namespace** (auth, users, cameras, media, analytics, workflows, operations, system, vision)
3. **Add [+ Assign] button** next to Roles section → opens **Role Assign Dialog** (View F)
4. **Add remove (✕) on each role chip** — calls `unassignRoleFromUser`, with safeguard preventing removal of last `owner`
5. **Capability toggles:** Call `POST /api/v1/users/toggle-capability/{userId}`. Only shown if current user has `auth.capabilities.assign`
6. **Admin actions:** Set Password (existing), Disable Account (new), Delete User (new, owner-only)

**New file:** `lib/presentation/screens/roles/roles_screen.dart`

```
┌──────────────────────────────────────────┐
│  CustomAppBar(title: "Roles") [+ Create] │
├──────────────────────────────────────────┤
│  ┌────────────────────────────────────┐  │
│  │ 👑 owner     30 caps · 1 user     │  │
│  │    System role · cannot delete    │  │
│  │                          [View →] │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 🛡️ admin     19 caps · 2 users    │  │
│  │    System role · cannot delete    │  │
│  │                          [View →] │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 👤 user       9 caps · 3 users    │  │
│  │    System role · cannot delete    │  │
│  │                          [View →] │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 📷 camera_user  11 caps · 1 user  │  │
│  │    Custom role                    │  │
│  │                   [Edit] [Delete] │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**Implementation details:**

- **Create button** opens dialog: text field for role name → `POST /roles/`
- System roles show lock badge; **cannot be deleted or renamed**
- Custom roles show [Edit] (rename dialog) and [Delete] (confirmation dialog)
- Each card shows: icon, name, capability count, user count
- Tap navigates to Role Detail (View D)
- **Visibility:** Users with `auth.roles.read`

### 4.4 View D: Role Detail View

**New file:** `lib/presentation/screens/roles/role_detail_screen.dart`

```
┌──────────────────────────────────────────┐
│  CustomAppBar(title: "Role: admin")      │
├──────────────────────────────────────────┤
│  ┌─ Overview ─────────────────────────┐  │
│  │ Role: admin    Type: System role   │  │
│  │ Capabilities: 19    Users: 2       │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ── CAPABILITIES ─────────── [+ Add] ──  │
│  ┌─ Auth & Session ───────────────────┐  │
│  │ [✓] auth.session.use             ✕ │  │  ← Tap ✕ to remove
│  │ [✓] auth.roles.read              ✕ │  │
│  └────────────────────────────────────┘  │
│  ┌─ Users ────────────────────────────┐  │
│  │ [✓] users.accounts.read          ✕ │  │
│  │ [✓] users.accounts.create        ✕ │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ── USERS WITH THIS ROLE ──────────────  │
│  ┌────────────────────────────────────┐  │
│  │ 👤 nick.glezakos@gmail.com       ✕ │  │  ← Remove user from role
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 👤 fresh.user@example.com        ✕ │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

**Implementation:**
- Overview card with metadata. Capabilities grouped by namespace, each with remove (✕)
- [+ Add] opens Capability Assign Dialog (View E)
- Users section with remove (✕). Safeguard: last `owner` cannot be removed.

### 4.5 View E: Capability Assign Dialog

**New file:** `lib/presentation/screens/roles/capability_assign_dialog.dart`

Bottom sheet or dialog used from Role Detail to add/remove capabilities.

```
┌──────────────────────────────────────────┐
│  Add Capabilities to "admin"      [Apply]│
│  🔍 Search capabilities...               │
│  ── Unassigned ────────────────────────  │
│  ☐ auth.roles.create                     │
│  ☐ auth.roles.delete                     │
│  ☐ users.accounts.delete                 │
│  ── Already Assigned (greyed) ─────────  │
│  ☑ auth.session.use                      │
│  ☑ users.accounts.read                   │
└──────────────────────────────────────────┘
```

Behavior: Fetches assigned + unassigned capabilities. Check = assign, uncheck = remove. On Apply: batch `POST add-capability` / `POST remove-capability`.

### 4.6 View F: Role Assign Dialog

**New file:** `lib/presentation/screens/users/role_assign_dialog.dart`

Dialog used from User Profile to assign/unassign roles.

```
┌──────────────────────────────────────────┐
│  Manage Roles for nick.glezakos@gmail.com│
│  ☐ owner   Full platform control (30)   │
│  ☑ admin   Administrative access (19)   │
│  ☑ user    Basic platform access (9)    │
│  ☐ camera_user  Camera service (11)     │
│  ┌──────────┐  ┌──────────┐             │
│  │  Cancel  │  │  Apply   │             │
│  └──────────┘  └──────────┘             │
└──────────────────────────────────────────┘
```

Shows all roles with checkboxes. Pre-checks currently assigned. Apply assigns/unassigns. **Safeguard:** Unchecking last `owner` shows warning and blocks.

### 4.7 View G: Audit Log Screen

**New file:** `lib/presentation/screens/users/audit_log_screen.dart`

```
┌──────────────────────────────────────────┐
│  CustomAppBar(title: "Audit Log")        │
│  [All] [role] [capability] [user] [auth] │
│  ─────────────────────────────────────   │
│  2026-08-09 14:32  fresh.user@ex...      │
│  role_assign:user=5:role=2               │
│  ─────────────────────────────────────   │
│  2026-08-09 14:31  fresh.user@ex...      │
│  capability_assign:role=3:cap=12         │
└──────────────────────────────────────────┘
```

Calls `GET /actions/?skip=0&limit=50`. Client-side filter by action prefix. Requires `users.accounts.read`.

---

## 5. Navigation Wiring — GoRouter Changes

### 5.1 New Routes

Add to `lib/presentation/navigation/app_router.dart`:

```dart
GoRoute(
  path: '/roles',
  name: 'roles',
  builder: (context, state) => const ProviderScreenWrapper(
    child: RolesScreen(),
  ),
),
GoRoute(
  path: '/roles/:roleId',
  name: 'role-detail',
  builder: (context, state) {
    final roleId = int.parse(state.pathParameters['roleId']!);
    return ProviderScreenWrapper(
      child: RoleDetailScreen(roleId: roleId),
    );
  },
),
GoRoute(
  path: '/audit',
  name: 'audit-log',
  builder: (context, state) => const ProviderScreenWrapper(
    child: AuditLogScreen(),
  ),
),
```

### 5.2 Existing Routes — No Changes

Existing `/users` and `/profile` routes remain as-is. `/profile?userId=X` already supports viewing other users. Only the screen implementations change.

### 5.3 Navigation Access Points

| Entry Point | Location | Navigates To | Visibility Gate |
|-------------|----------|-------------|-----------------|
| Home screen nav | Existing sidebar/bottom nav | `/roles` | `auth.roles.read` |
| Users screen → tap card | Existing | `/profile?userId=X` | `users.accounts.read` |
| Roles screen → tap card | New | `/roles/:roleId` | `auth.roles.read` |
| Profile → [+ Assign] | New button | Opens Role Assign Dialog | `auth.roles.assign` |
| Role detail → [+ Add] | New button | Opens Capability Assign Dialog | `auth.capabilities.assign` |
| Settings/Admin menu | New link | `/audit` | `users.accounts.read` |

### 5.4 Home Screen Integration

Add Roles as a nav item, visible only when `user.canManageRoles` is true.

---

## 6. Reuse of Existing Views & Patterns

### Views Modified

| File | Changes |
|------|---------|
| `lib/presentation/screens/users/users_screen.dart` | Role badges, filter chips, capability counts |
| `lib/screens/profile_screen.dart` | Dynamic capability toggle list, role assign dialog trigger, role chip removal, admin actions |
| `lib/core/models/user.dart` | Add `isOwner`, `canManageRoles`, `canManageCapabilities`, `canManageUsers` |
| `lib/core/providers/users_provider.dart` | Add `loadUserDetail`, `toggleCapability`, `assignRole`, `unassignRole` |
| `lib/core/services/users_service.dart` | Add `getUserProfile`, `toggleCapability` |
| `lib/presentation/navigation/app_router.dart` | Add `/roles`, `/roles/:roleId`, `/audit` routes |

### Views Created (New)

| File | Purpose |
|------|---------|
| `lib/presentation/screens/roles/roles_screen.dart` | Roles list with CRUD |
| `lib/presentation/screens/roles/role_detail_screen.dart` | Single role: capabilities + users |
| `lib/presentation/screens/roles/capability_assign_dialog.dart` | Add/remove capabilities from role |
| `lib/presentation/screens/users/role_assign_dialog.dart` | Assign/unassign roles to user |
| `lib/presentation/screens/users/audit_log_screen.dart` | Filterable audit log |
| `lib/core/models/role.dart` | Role model with JSON serialization |
| `lib/core/models/capability.dart` | Capability model with JSON serialization |
| `lib/core/services/roles_service.dart` | All role/capability API calls |
| `lib/core/services/capabilities_service.dart` | Capability query API calls |
| `lib/core/providers/roles_provider.dart` | Roles state management |
| `lib/core/providers/capabilities_provider.dart` | Capabilities state management |

### Views Reused As-Is

| Component | Why |
|-----------|-----|
| `CustomAppBar` | All new screens use it for consistent navigation |
| `AppTheme` / color system | Role colors: owner=amber, admin=deepPurple, user=blue |
| `ApiClient` | All new services use existing Dio-based client with JWT interceptor |
| `ProviderScreenWrapper` | Wraps all new screens for Riverpod access |
| `ChangePasswordDialog` | Already exists, reused in enhanced profile |
| `AuthorityStatusCard` | Already exists, reused in profile |
| GoRouter auth guard | Existing redirect pattern, no changes needed |

---

## 7. Phased Implementation Plan

### Phase 1: Data Layer (Models + Services + Providers)

**Goal:** All API calls available from Flutter. No UI changes yet.

| # | Task | Files | Effort |
|---|------|-------|--------|
| 1.1 | Create `Role` model | `lib/core/models/role.dart` + `.g.dart` | Small |
| 1.2 | Create `Capability` model | `lib/core/models/capability.dart` + `.g.dart` | Small |
| 1.3 | Add `User` capability helpers | `lib/core/models/user.dart` | Small |
| 1.4 | Create `RolesService` | `lib/core/services/roles_service.dart` | Medium |
| 1.5 | Create `CapabilitiesService` | `lib/core/services/capabilities_service.dart` | Small |
| 1.6 | Enhance `UsersService` | `lib/core/services/users_service.dart` | Small |
| 1.7 | Create `RolesProvider` | `lib/core/providers/roles_provider.dart` | Medium |
| 1.8 | Create `CapabilitiesProvider` | `lib/core/providers/capabilities_provider.dart` | Small |
| 1.9 | Enhance `UsersProvider` | `lib/core/providers/users_provider.dart` | Small |

**Deliverable:** All backend APIs callable from Flutter. Testable via debug console.

### Phase 2: User-Centric Views

**Goal:** Enhanced Users list and User Profile with role/capability management.

| # | Task | Files | Effort |
|---|------|-------|--------|
| 2.1 | Enhance `UsersScreen` | `lib/presentation/screens/users/users_screen.dart` | Medium |
| 2.2 | Create `RoleAssignDialog` | `lib/presentation/screens/users/role_assign_dialog.dart` | Medium |
| 2.3 | Enhance `ProfileScreen` | `lib/screens/profile_screen.dart` | Large |
| 2.4 | Wire navigation changes | `lib/presentation/navigation/app_router.dart` | Small |

**Deliverable:** Admins can view user roles/capabilities, assign/remove roles, toggle capabilities from User Profile. Users list shows role badges.

### Phase 3: Admin Views

**Goal:** Roles management, role detail, capability assignment, audit log.

| # | Task | Files | Effort |
|---|------|-------|--------|
| 3.1 | Create `RolesScreen` | `lib/presentation/screens/roles/roles_screen.dart` | Medium |
| 3.2 | Create `RoleDetailScreen` | `lib/presentation/screens/roles/role_detail_screen.dart` | Large |
| 3.3 | Create `CapabilityAssignDialog` | `lib/presentation/screens/roles/capability_assign_dialog.dart` | Medium |
| 3.4 | Create `AuditLogScreen` | `lib/presentation/screens/users/audit_log_screen.dart` | Small |
| 3.5 | Wire routes + home screen nav | `app_router.dart` + home screen | Small |

**Deliverable:** Full lifecycle: create/rename/delete roles, add/remove capabilities from roles, view users per role, audit log.

---

## 8. Safeguards & Edge Cases

| Scenario | Handling |
|----------|----------|
| **User tries to delete system role** | UI hides delete button for `owner`, `admin`, `user`. Backend also rejects. |
| **User tries to rename system role** | UI hides rename/edit for system roles. Backend raises `ValueError`. |
| **User tries to remove last owner** | UI disables remove button with tooltip. Backend also rejects. |
| **User lacks required capability** | Backend returns 403. Frontend hides nav items via `User.canManage*` checks. |
| **Network error during toggle** | Show SnackBar with error. Revert toggle to previous state. |
| **Concurrent role assignment** | Backend `UNIQUE(user_id, role_id)` prevents duplicates. UI shows success toast. |
| **Capability assigned twice** | Backend `UNIQUE(role_id, capability_id)` prevents duplicates. |
| **Offline / no connectivity** | Loading state → error state with retry button (existing pattern). |

---

## 9. Capability Naming for UI Grouping

Since the backend doesn't return `namespace` or `description` fields, the frontend derives them client-side:

```dart
String capabilityNamespace(String name) {
  if (name.contains(':')) return name.split(':').first;
  if (name.contains('.')) return name.split('.').first;
  return 'other';
}
```

A static description map should be maintained in `lib/core/constants/capability_descriptions.dart` with all known capabilities from the backend. This map must be kept in sync when new capabilities are added.

**Key namespaces for grouping:**

| Namespace | Example capabilities |
|-----------|---------------------|
| `auth` | `auth.session.use`, `auth.roles.create`, `auth.capabilities.assign` |
| `users` | `users.profile.read`, `users.accounts.create`, `users.accounts.delete` |
| `cameras` | `cameras:view`, `cameras:connect`, `cameras:admin` (colon notation) |
| `cameras` | `cameras.view`, `cameras.manage` (dot notation — legacy) |
| `media` | `media.view`, `media.manage` |
| `analytics` | `analytics.view` |
| `workflows` | `workflows.use` |
| `operations` | `operations.execute` |
| `system` | `system.installation.manage`, `system.licensing.manage` |
| `vision` | `vision` |

---

## 10. Success Criteria

1. An admin can view all users with role badges and capability counts from the Users screen
2. An admin can tap a user, see their full role/capability state, and toggle any capability on/off
3. An admin can assign or remove roles from a user via the Role Assign Dialog
4. An admin can view all roles, see their capability counts and user counts
5. An admin can create a new custom role, rename it, or delete it
6. An admin can drill into a role, see which capabilities it has, and add/remove capabilities
7. An admin can view which users have a specific role from the Role Detail screen
8. An admin can view the audit log of all role/capability/user management actions
9. System roles (owner, admin, user) cannot be renamed, deleted, or have their last owner removed
10. All views are capability-gated — unauthorized users see nothing or get 403
