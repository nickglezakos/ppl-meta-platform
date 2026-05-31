# PPL Meta Presence Mobile Flutter Architecture

**Date**: May 30, 2026  
**Status**: Draft  
**Depends On**: [docs/proposals/presence/Eyenet presence.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/Eyenet%20presence.md), [docs/proposals/presence/ppl-meta-presence-mobile-functional-spec.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/ppl-meta-presence-mobile-functional-spec.md)

---

## Purpose

This document turns the functional spec into a concrete Flutter architecture and screen plan for `ppl-meta-presence-mobile`.

The design goal is a reliable, testable Flutter application that:

- keeps camera lifecycle transitions explicit
- isolates backend orchestration from UI state
- makes the retry flow deterministic
- can be implemented incrementally

The first implementation should inherit service and process layers from [ppl_meta_mobile_camera](/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera) wherever they already solve presence-mobile needs.

---

## Architectural Principles

1. Use a feature-first structure centered on the presence flow.
2. Keep camera control behind dedicated services, not inside widgets.
3. Model the full flow as a state machine, not a loose set of booleans.
4. Keep API contracts in a repository layer.
5. Treat front-burst capture and back-camera QR scanning as separate camera phases.
6. Make cleanup explicit whenever the flow changes phase.
7. Reuse proven mobile camera services before introducing presence-specific replacements.

---

## Recommended Project Structure

```text
lib/
  app/
    app.dart
    router.dart
    theme.dart
  core/
    auth/
      auth_repository.dart
      auth_state.dart
      inherited_mobile_auth_adapter.dart
    networking/
      api_client.dart
      api_error.dart
    logging/
      app_logger.dart
    permissions/
      camera_permission_service.dart
  features/
    presence/
      application/
        presence_flow_controller.dart
        presence_flow_state.dart
        presence_flow_event.dart
      data/
        presence_repository.dart
        presence_models.dart
      domain/
        presence_result.dart
        presence_session.dart
        presence_phase.dart
      presentation/
        screens/
          presence_home_screen.dart
          front_burst_capture_screen.dart
          qr_scan_screen.dart
          holding_retry_screen.dart
          presence_result_screen.dart
        widgets/
          presence_primary_button.dart
          capture_progress_card.dart
          qr_scan_overlay.dart
          holding_status_card.dart
          result_status_card.dart
      services/
        inherited_mobile_camera_adapter.dart
        front_burst_camera_service.dart
        qr_scanner_service.dart
        burst_upload_service.dart
        session_polling_service.dart
```

---

## State Management

The app should use one dedicated controller for the end-to-end presence flow.

Recommended shape:

- `PresenceFlowController`
- immutable `PresenceFlowState`
- explicit phase enum plus attached data

Suggested phases:

- `idle`
- `creatingSession`
- `capturingFrontBurst1`
- `uploadingFrontBurst1`
- `scanningQr`
- `submittingQrHit`
- `waitingForDecision`
- `retryRequired`
- `capturingFrontBurst2`
- `uploadingFrontBurst2`
- `success`
- `denied`
- `failed`

The UI should render entirely from this state.

---

## Services

The first implementation should explicitly wrap and adapt existing mobile camera services rather than replacing them immediately.

Suggested inherited service mappings:

- `EnhancedAuthenticationService` -> auth adapter
- `HybridServiceDiscoveryService` -> platform connection and endpoint adapter
- `AutoCameraRegistrationService` -> device identity and registration adapter
- `MobileStreamingService` -> burst upload transport adapter

## Adapter Interface Layer

The presence app should introduce a thin adapter layer so the inherited mobile camera services can be consumed without leaking their concrete implementations into feature UI code.

Recommended adapter interfaces:

```dart
abstract class InheritedMobileAuthAdapter {
  Future<bool> initialize();
  Future<AuthSessionSnapshot> login({
    required String username,
    required String password,
  });
  Future<AuthSessionSnapshot?> restoreSession();
  String? get authToken;
  String? get serverUrl;
  Map<String, dynamic>? get platformServices;
}

abstract class InheritedPlatformConnectionAdapter {
  Future<List<DiscoveredService>> getAvailableServices();
  Future<String?> discoverNodeService();
  String? get gatewayBaseUrl;
  String? get camerasBaseUrl;
}

abstract class InheritedDeviceRegistrationAdapter {
  Future<RegisteredMobileDevice?> getExistingRegistration(String jwtToken);
  Future<RegisteredMobileDevice> registerDevice(String jwtToken);
  Future<void> sendHeartbeat(String cameraUuid, String jwtToken);
  Future<void> updateIpAddress(String deviceId, String ipAddress);
}

abstract class InheritedBurstTransportAdapter {
  Future<void> configure({
    required String backendUrl,
    required String accessToken,
    required String deviceId,
  });
  Future<void> sendBurstFrame(BurstFramePayload frame);
  Future<void> sendBurstFrames(List<BurstFramePayload> frames);
}
```

## Concrete Dart Model Types

The first implementation should standardize on the following adapter-facing Dart model types before writing feature code.

```dart
class AuthSessionSnapshot {
  final String authToken;
  final String serverUrl;
  final Map<String, dynamic> userData;
  final Map<String, dynamic> platformServices;
  final bool isAuthenticated;

  const AuthSessionSnapshot({
    required this.authToken,
    required this.serverUrl,
    required this.userData,
    required this.platformServices,
    required this.isAuthenticated,
  });
}

class DiscoveredService {
  final String name;
  final String host;
  final int port;
  final String status;
  final String? baseUrl;

  const DiscoveredService({
    required this.name,
    required this.host,
    required this.port,
    required this.status,
    this.baseUrl,
  });
}

class RegisteredMobileDevice {
  final String cameraId;
  final String deviceUuid;
  final String cameraName;
  final String? streamUrl;

  const RegisteredMobileDevice({
    required this.cameraId,
    required this.deviceUuid,
    required this.cameraName,
    this.streamUrl,
  });
}

class BurstFramePayload {
  final String frameData;
  final double timestamp;
  final int width;
  final int height;
  final String format;
  final String orientation;
  final int rotationAngle;
  final int fps;
  final String? cameraFacing;

  const BurstFramePayload({
    required this.frameData,
    required this.timestamp,
    required this.width,
    required this.height,
    required this.format,
    required this.orientation,
    required this.rotationAngle,
    required this.fps,
    this.cameraFacing,
  });
}

class PresenceBurstPayload {
  final String deviceId;
  final String sessionUuid;
  final String capturePhase;
  final List<BurstFramePayload> frames;
  final DateTime capturedAt;
  final String transportSource;

  const PresenceBurstPayload({
    required this.deviceId,
    required this.sessionUuid,
    required this.capturePhase,
    required this.frames,
    required this.capturedAt,
    required this.transportSource,
  });
}
```

These types should be treated as the first implementation DTO surface between adapters, repository code, and the presence flow controller.

These adapters should be implemented by thin wrappers around the existing services rather than rewritten from scratch.

## Concrete Existing Mappings

The first adapter implementations should map to the current mobile camera app as follows:

- `InheritedMobileAuthAdapter` wraps `EnhancedAuthenticationService`
- `InheritedPlatformConnectionAdapter` wraps `HybridServiceDiscoveryService` plus resolved platform-services data
- `InheritedDeviceRegistrationAdapter` wraps `AutoCameraRegistrationService`, `MobileCameraHeartbeatService`, and `MobileCameraIPUpdateService` where needed
- `InheritedBurstTransportAdapter` wraps `MobileStreamingService`

The adapter implementations should preserve the current persisted key model:

- `ppl_meta_auth_token`
- `ppl_meta_user_data`
- `ppl_meta_device_data`
- `ppl_meta_server_config`
- `ppl_meta_discovered_services`
- `ppl_meta_platform_services`

## Adapter Mapping Matrix

The first implementation should use the following explicit mapping between inherited service responsibilities and new presence app adapters.

| Presence adapter | Inherited service | Existing responsibility | Presence responsibility |
| --- | --- | --- | --- |
| `InheritedMobileAuthAdapter` | `EnhancedAuthenticationService` | initialize auth, discover services, login, persist token and platform data, fetch user profile | initialize session, restore session, expose token/server/platform services to the presence flow |
| `InheritedPlatformConnectionAdapter` | `HybridServiceDiscoveryService` | discover Node and service endpoints via discovery and health checks | resolve Node, gateway, and cameras endpoints for presence session bootstrap |
| `InheritedDeviceRegistrationAdapter` | `AutoCameraRegistrationService` | check existing registration, register mobile device, persist server-generated UUID | establish or restore the device anchor used by presence sessions |
| `InheritedDeviceRegistrationAdapter` | `MobileCameraHeartbeatService` | keep registered mobile camera/device alive and synchronized | optionally keep the presence device anchor fresh during longer-lived presence sessions |
| `InheritedDeviceRegistrationAdapter` | `MobileCameraIPUpdateService` | update backend IP when network changes | preserve reachability for registered device anchors if presence depends on inherited mobile registration |
| `InheritedBurstTransportAdapter` | `MobileStreamingService` | package frames, attach orientation/fps metadata, send HTTP frame payloads | send front-camera burst frames using the inherited frame schema with presence envelope metadata |

## Method-Level Mapping

Recommended initial method mapping:

- `InheritedMobileAuthAdapter.initialize()` -> `EnhancedAuthenticationService.initializeAuth()`
- `InheritedMobileAuthAdapter.login()` -> `EnhancedAuthenticationService.autoLogin()`
- `InheritedMobileAuthAdapter.restoreSession()` -> read inherited persisted auth/token/platform-service state through `EnhancedAuthenticationService`
- `InheritedPlatformConnectionAdapter.getAvailableServices()` -> `HybridServiceDiscoveryService.getAvailableServices()`
- `InheritedPlatformConnectionAdapter.discoverNodeService()` -> `HybridServiceDiscoveryService.discoverNodeService()`
- `InheritedDeviceRegistrationAdapter.getExistingRegistration()` -> `AutoCameraRegistrationService.checkExistingCamera()`
- `InheritedDeviceRegistrationAdapter.registerDevice()` -> `AutoCameraRegistrationService.autoRegisterCamera()`
- `InheritedDeviceRegistrationAdapter.sendHeartbeat()` -> `MobileCameraHeartbeatService` heartbeat call
- `InheritedDeviceRegistrationAdapter.updateIpAddress()` -> `MobileCameraIPUpdateService` IP update call
- `InheritedBurstTransportAdapter.configure()` -> `MobileStreamingService.setBackendConnection()`
- `InheritedBurstTransportAdapter.sendBurstFrame()` -> `MobileStreamingService.sendFrameToBackend()` after frame packaging
- `InheritedBurstTransportAdapter.sendBurstFrames()` -> repeated `sendFrameToBackend()` calls under one presence burst envelope strategy

Recommended return/input conventions:

- auth adapters return `AuthSessionSnapshot`
- discovery adapters return `DiscoveredService`
- registration adapters return `RegisteredMobileDevice`
- transport adapters accept `BurstFramePayload` or `PresenceBurstPayload`

## Responsibility Split

The split between inherited services and presence-specific code should be:

- inherited services own auth bootstrap, discovery, registration, and low-level frame transport
- presence-specific code owns session orchestration, QR flow, retry flow, and presence result handling
- adapters isolate the presence app from internal implementation details of the inherited mobile camera services

## FrontBurstCameraService

Responsibilities:

- initialize front camera
- capture configured burst frame set
- dispose camera immediately after capture
- surface capture errors as typed failures

Suggested interface:

```dart
abstract class FrontBurstCameraService {
  Future<List<BurstFrame>> captureBurst({required BurstCaptureConfig config});
  Future<void> dispose();
}
```

Implementation note:

- this service should focus on camera capture only
- it should delegate upload to `InheritedBurstTransportAdapter`
- it should not own auth, endpoint discovery, or registration logic

## QrScannerService

Responsibilities:

- initialize back camera scanning session
- expose QR scan events
- stop scanning after first valid hit
- dispose back camera when flow exits

Suggested interface:

```dart
abstract class QrScannerService {
  Stream<QrScanResult> startScanning();
  Future<void> stop();
  Future<void> dispose();
}
```

## PresenceRepository

Responsibilities:

- create sessions
- upload bursts
- submit QR hits
- fetch session and result state
- hide HTTP details from UI

Implementation requirement:

- repository setup should consume the same token and platform-services data model already persisted by the current mobile camera app services

Concrete inherited endpoint expectations:

- login bootstrap depends on `/api/v1/users/login`, `/api/v1/users/platform/services`, and `/api/v1/users/profile`
- presence device anchoring may depend on `/api/v1/cameras/mobile` and related inherited mobile camera lifecycle endpoints
- burst upload should stay compatible with current HTTP frame transport at `/api/v1/streaming/mobile/{device_id}/frame`

Suggested interface:

```dart
abstract class PresenceRepository {
  Future<PresenceSessionDto> createSession(DeviceContext context);
  Future<DetectionAttemptDto> uploadFrontBurst(String sessionId, BurstPayload payload);
  Future<DetectionAttemptDto> uploadRetryBurst(String sessionId, BurstPayload payload);
  Future<PresenceSessionDto> submitQrHit(String sessionId, QrHitPayload payload);
  Future<PresenceResultDto> getResult(String sessionId);
}
```

## SessionPollingService

Responsibilities:

- poll the session result endpoint while in waiting states
- stop polling when terminal state is reached
- emit retry-required or final outcome transitions

---

## Screen Plan

## 1. PresenceHomeScreen

Purpose:

- landing screen after login
- primary CTA to start the flow

UI contents:

- current user summary
- installation summary if available
- main action button
- last result summary optionally

Transitions:

- tap CTA -> `creatingSession`

## 2. FrontBurstCaptureScreen

Purpose:

- handle both first and second burst capture phases

UI contents:

- minimal camera framing UI
- text instruction
- progress bar or frame counter
- cancel action if allowed

Behavior:

- auto-start capture on entry
- auto-exit on success
- surface capture failure clearly

## 3. QrScanScreen

Purpose:

- guide the user through the back-camera QR scan phase

UI contents:

- live preview
- scan frame overlay
- timeout progress or status text
- cancel action

Behavior:

- starts scanning on entry
- submits first valid QR hit
- stops scanner immediately after valid QR

## 4. HoldingRetryScreen

Purpose:

- communicate that the first detection result is insufficient or still pending
- stage the retry burst if needed

UI contents:

- holding animation
- short explanatory text
- optional countdown or progress state

Behavior:

- if backend requests retry, transition into second burst capture
- if backend returns final result while waiting, bypass retry screen quickly

## 5. PresenceResultScreen

Purpose:

- display granted, denied, or failed outcome

UI contents:

- clear status title
- reason text
- return home button
- retry button if policy allows

---

## Routing Strategy

The app can use either declarative routing or imperative navigation, but the flow should be controller-driven.

Recommended approach:

- keep a small route surface
- let the controller decide transitions
- avoid allowing the user to back-navigate into stale camera screens without controller approval

Suggested route list:

- `/login`
- `/home`
- `/presence/front-burst`
- `/presence/qr-scan`
- `/presence/holding`
- `/presence/result`

---

## Data Models

Suggested client models:

```dart
class PresenceSession {
  final String sessionUuid;
  final PresenceSessionStatus status;
  final DateTime expiresAt;
}

class BurstFrame {
  final List<int> jpegBytes;
  final DateTime capturedAt;
}

class PresenceResult {
  final PresenceDecision decision;
  final String reasonCode;
  final String? triggerType;
  final String? actionType;
}
```

---

## Controller Responsibilities

`PresenceFlowController` should:

- request permissions
- create session
- call front burst capture service
- upload bursts
- start QR scanning
- submit QR hit
- poll for result
- decide whether retry is needed
- clean up camera services on every phase transition
- expose user-facing error states

It should not:

- hold raw widget references
- perform HTTP directly
- leave camera resources alive after a phase completes

---

## Error Handling Model

Recommended error categories:

- authentication error
- permission error
- camera initialization error
- burst capture error
- upload error
- QR timeout error
- invalid QR error
- backend timeout error
- presence denial

Map these to user-safe messages in the presentation layer.

---

## Testing Plan

## Unit Tests

- state machine transitions
- retry logic
- result polling behavior
- repository response mapping

## Widget Tests

- home screen rendering
- front burst progress states
- QR scan screen static UI states
- holding screen states
- result screen variants

## Integration Tests

- happy path with mocked backend
- retry path with mocked retry-required status
- failure path for upload or QR timeout

---

## Incremental Delivery Plan

## Milestone 1

- login shell
- home screen
- presence flow controller skeleton
- mocked repository
- adapter layer around inherited services from `ppl_meta_mobile_camera`

Milestone 1 deliverable detail:

- prove that `EnhancedAuthenticationService`, `HybridServiceDiscoveryService`, `AutoCameraRegistrationService`, and `MobileStreamingService` can all be consumed through the adapter interfaces without changing their current contracts

## Milestone 2

- first front-burst capture
- upload integration
- QR scan screen

## Milestone 3

- result polling
- retry flow
- result screen

## Milestone 4

- cleanup hardening
- telemetry
- UI refinement

---

## Open Architecture Questions

1. Should the app reuse any packages or services from `ppl_meta_mobile_camera`, or stay fully standalone?
2. Should burst capture be built on the Flutter `camera` plugin directly, or should a narrower native bridge be introduced later if camera handoff latency is too high?
3. Should session polling be replaced by server push in a later phase if backend infrastructure allows it?
4. Should the QR scanning package be the same one already used elsewhere in the workspace, or selected specifically for stronger lifecycle isolation?
