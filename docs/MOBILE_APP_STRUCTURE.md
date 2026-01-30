# Eyenet Vision Mobile Camera App - Structure & Navigation Map

**Document Created:** January 30, 2026  
**Purpose:** Map the mobile app architecture to understand which screens are active vs inactive

---

## 🚀 Entry Point & Navigation Flow

### Main Entry (`lib/main.dart`)
- **App Name:** Currently "PPL Meta Camera" (needs update to "Eyenet Vision")
- **Entry Widget:** `PPLMetaCameraApp` → `MainNavigator`
- **Authentication Router:** `MainNavigator._build()`

```dart
MainNavigator Logic:
├─ If NOT authenticated → SimpleSetupScreen (ACTIVE LOGIN PAGE)
├─ If authenticated + needs camera registration → CameraRegistrationScreen
└─ If authenticated + registered → CameraScreen
```

---

## 📱 Active Screens (Currently Used)

### 1. **SimpleSetupScreen** ✅ ACTIVE LOGIN PAGE
**File:** `lib/features/authentication/screens/simple_setup_screen_new.dart`  
**Export:** `lib/features/authentication/authentication.dart` (line 6)  
**Status:** ✅ **THIS IS THE ACTUAL LANDING PAGE**

**Features:**
- Complete backend IP input (e.g., `192.168.1.68`)
- Discovery service port input (default: `8006`)
- Username/password fields
- Direct connection to Discovery Service
- Authenticates via Node service

**Current State:**
- ⚠️ Title: "PPL Meta Setup" (needs to be "Eyenet Vision")
- ⚠️ No logo displayed
- ⚠️ Help text is static, not in dropdown
- ⚠️ No "How Tos" section

**What Needs Updating:**
```dart
Line ~107: AppBar title → "Eyenet Vision"
Line ~110: Add logo to AppBar
Line ~300+: Replace static help text with "How Tos" dropdown
```

---

### 2. **CameraRegistrationScreen** ✅ ACTIVE
**File:** `lib/features/camera/screens/camera_registration_screen.dart`  
**Shown:** After successful login, before camera setup

**Purpose:**
- Register mobile device as a camera
- Enter camera name
- Complete platform registration

---

### 3. **CameraScreen** ✅ ACTIVE
**File:** `lib/features/camera/screens/camera_screen.dart`  
**Shown:** Main camera interface after authentication + registration

**Features:**
- Live camera preview
- Start/stop streaming
- Camera controls
- Gallery access
- Settings panel

**Status:**
- ✅ Already updated with "Eyenet Vision" branding
- ✅ Logo integrated in top app bar

---

## 📋 Inactive/Alternate Screens (NOT Currently Used)

### 4. **simple_setup_screen.dart** ❌ NOT USED
**File:** `lib/features/authentication/screens/simple_setup_screen.dart`  
**Status:** ❌ **NOT EXPORTED - NOT IN USE**

**Why it exists:**
- Older version of setup screen
- Uses IP last part only (e.g., "68" for 192.168.1.68)
- Auto-detects network prefix
- Kept for reference/backup

**We mistakenly updated this file!** ❌
- Added logo ✓
- Added "How Tos" dropdown ✓
- Updated branding ✓
- **BUT IT'S NOT BEING USED!** ❌

---

### 5. **AuthenticationScreen** ❌ NOT USED AS ENTRY
**File:** `lib/features/authentication/screens/authentication_screen.dart`  
**Status:** ⚠️ Exported but not used as landing page

**Features:**
- Tab-based UI (Login / Register)
- Uses `LoginForm` and `RegistrationForm` widgets
- More polished UI with animations
- Server discovery integration

**Current State:**
- ✅ Updated with "Eyenet Vision" branding
- ✅ Logo integrated
- ✅ "How Tos" dropdown at bottom
- **BUT NOT DISPLAYED TO USER** ⚠️

**Why not used:**
- MainNavigator loads `SimpleSetupScreen` directly
- This is likely a more advanced/alternate authentication flow

---

### 6. **AutomaticSetupScreen** ❌ NOT USED
**File:** `lib/features/authentication/screens/automatic_setup_screen.dart`  
**Status:** Exported but not in navigation flow

**Purpose:** Auto-discovery based setup (experimental)

---

### 7. **ConnectionScreen** ❌ NOT USED
**File:** `lib/features/connection/screens/connection_screen.dart`  
**Status:** Exists but not in main navigation

**Purpose:** Alternative connection/streaming screen (Phase 2?)

---

### 8. **PlatformConnectionScreen** ❌ NOT USED
**File:** `lib/features/camera/screens/platform_connection_screen.dart`  
**Status:** Platform service registration (older flow?)

---

## 🔄 Multiple Main Entry Points

The app has 3 different `main` files:

### 1. **main.dart** ✅ DEFAULT
**Used by:** `flutter run` (default)  
**Entry Screen:** `SimpleSetupScreen` (from simple_setup_screen_new.dart)

### 2. **main_simple.dart** ❌ NOT USED
**Purpose:** Minimal test/demo app
**Contains:** Basic "Hello World" style app

### 3. **main_streaming.dart** ❌ NOT USED
**Purpose:** Streaming-focused demo
**Entry Screen:** `ConnectionScreen`

---

## 🎯 What We Need to Fix

### HIGH PRIORITY - SimpleSetupScreen (simple_setup_screen_new.dart)

This is the **ACTUAL LANDING PAGE** that users see!

**Required Changes:**

1. ✅ **App Bar Title**
   ```dart
   // Line ~107
   AppBar(
     title: const Text('Eyenet Vision'),  // Currently "PPL Meta Setup"
   ```

2. ✅ **Add Logo to App Bar**
   ```dart
   AppBar(
     title: Row(
       mainAxisSize: MainAxisSize.min,
       children: [
         // Logo container
         Image.asset('assets/logo.png', ...),
         const SizedBox(width: 8),
         const Text('Eyenet Vision'),
       ],
     ),
   ```

3. ✅ **Replace Static Help Text with "How Tos" Dropdown**
   ```dart
   // Replace the static help Container (around line 280-320)
   // With expandable "How Tos" section similar to AuthenticationScreen
   ```

4. ✅ **Update Button Text**
   ```dart
   // Line ~260
   'Connect to Platform'  // Currently "Connect to PPL Meta Platform"
   ```

5. ✅ **Add Version Info at Bottom**
   ```dart
   Text('Eyenet Vision v1.0.0')
   ```

---

## 📊 Screen Usage Summary

| Screen | File | Status | User Sees |
|--------|------|--------|-----------|
| SimpleSetupScreen | `simple_setup_screen_new.dart` | ✅ **ACTIVE** | ✅ **YES - LANDING PAGE** |
| CameraRegistrationScreen | `camera_registration_screen.dart` | ✅ ACTIVE | ✅ YES - After login |
| CameraScreen | `camera_screen.dart` | ✅ ACTIVE | ✅ YES - Main camera |
| AuthenticationScreen | `authentication_screen.dart` | ❌ Not Used | ❌ NO (but updated) |
| simple_setup_screen.dart | `simple_setup_screen.dart` | ❌ Not Used | ❌ NO (but updated) |
| AutomaticSetupScreen | `automatic_setup_screen.dart` | ❌ Not Used | ❌ NO |
| ConnectionScreen | `connection_screen.dart` | ❌ Not Used | ❌ NO |
| PlatformConnectionScreen | `platform_connection_screen.dart` | ❌ Not Used | ❌ NO |

---

## 🔍 Key Findings

1. **We updated the WRONG file twice:**
   - Updated `simple_setup_screen.dart` ❌ (not exported)
   - Updated `AuthenticationScreen` ❌ (not used as entry)
   - Need to update `simple_setup_screen_new.dart` ✅ (actual landing page)

2. **Two versions of SimpleSetupScreen exist:**
   - `simple_setup_screen.dart` - Uses IP last part + auto-detection
   - `simple_setup_screen_new.dart` - Uses complete IP (ACTIVE)

3. **Export file determines what's used:**
   - `lib/features/authentication/authentication.dart`
   - Line 6: `export 'screens/simple_setup_screen_new.dart';`
   - This is what MainNavigator imports and uses

4. **Navigation is centralized:**
   - `MainNavigator` in `main.dart` controls all routing
   - Single decision point based on authentication state

---

## ✅ Action Items

- [x] Document app structure
- [ ] Update `simple_setup_screen_new.dart` with:
  - [ ] "Eyenet Vision" branding
  - [ ] Logo in app bar
  - [ ] "How Tos" expandable dropdown at bottom
  - [ ] Dark theme styling
  - [ ] Version info
- [ ] Update `main.dart`:
  - [ ] MaterialApp title → "Eyenet Vision"
- [ ] Test with `flutter run` to verify changes appear
- [ ] Consider removing/archiving unused screen files

---

## 🎨 Design Consistency

All active screens should have:
- ✅ "Eyenet Vision" branding (not "PPL Meta")
- ✅ Logo from `assets/logo.png`
- ✅ Dark theme Material Design 3 colors
- ✅ Version info in footer
- ✅ Consistent navigation patterns

---

**End of Document**
