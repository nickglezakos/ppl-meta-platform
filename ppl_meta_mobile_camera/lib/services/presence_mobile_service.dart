import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;

import '../core/services/authentication_service.dart';
import '../core/services/orientation_service.dart';
import '../models/presence_mobile_models.dart';
import 'auto_camera_registration_service.dart';
import 'device_identifier_service.dart';
import 'discovery_config_service.dart';

class PresenceMobileService {
  final AuthenticationService _authService = AuthenticationService.instance;
  final AutoCameraRegistrationService _registrationService = AutoCameraRegistrationService();
  final DeviceIdentifierService _deviceIdentifierService = DeviceIdentifierService();
  final DiscoveryConfigService _discoveryConfig = DiscoveryConfigService.instance;

  Future<String> ensureRegisteredDevice() async {
    final token = _requireAuthToken();
    final existingUuid = await _deviceIdentifierService.getStoredCameraUuid();
    if (existingUuid != null && existingUuid.isNotEmpty) {
      return existingUuid;
    }

    final registration = await _registrationService.autoRegisterCamera(token);
    if (!registration.isSuccess || registration.deviceId == null || registration.deviceId!.isEmpty) {
      throw Exception(registration.error ?? 'Failed to register mobile camera device');
    }
    return registration.deviceId!;
  }

  Future<PresenceMobileSession> createSession({required String sessionMode}) async {
    final token = _requireAuthToken();
    final deviceUuid = await ensureRegisteredDevice();
    final deviceInfo = await _deviceIdentifierService.getDeviceRegistrationInfo();
    final baseUrl = await _presenceBaseUrl();
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions'),
      headers: _jsonHeaders(token),
      body: jsonEncode({
        'session_mode': sessionMode,
        'device_uuid': deviceUuid,
        'device_name': deviceInfo['model'] ?? 'Presence Mobile Camera',
        'device_platform': Platform.operatingSystem,
        'app_version': 'ppl_meta_mobile_camera_presence',
      }),
    );

    return PresenceMobileSession.fromJson(_unwrapData(response));
  }

  Future<PresenceMobileSession> getSession(String sessionUuid) async {
    final token = _requireAuthToken();
    final baseUrl = await _presenceBaseUrl();
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions/$sessionUuid'),
      headers: _jsonHeaders(token),
    );
    return PresenceMobileSession.fromJson(_unwrapData(response));
  }

  Future<PresenceMobileResult> getResult(String sessionUuid) async {
    final token = _requireAuthToken();
    final baseUrl = await _presenceBaseUrl();
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions/$sessionUuid/result'),
      headers: _jsonHeaders(token),
    );
    return PresenceMobileResult.fromJson(_unwrapData(response));
  }

  Future<PresenceMobileDetectionStatus> getDetectionStatus(String sessionUuid) async {
    final token = _requireAuthToken();
    final baseUrl = await _presenceBaseUrl();
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions/$sessionUuid/instant-detection-status'),
      headers: _jsonHeaders(token),
    );
    return PresenceMobileDetectionStatus.fromJson(_unwrapData(response));
  }

  Future<PresenceMobileDetectionAttempt> uploadFrontBurst({
    required String sessionUuid,
    required List<XFile> imageFiles,
    required String capturePhase,
  }) async {
    final token = _requireAuthToken();
    final deviceUuid = await ensureRegisteredDevice();
    final baseUrl = await _presenceBaseUrl();
    final orientation = OrientationService.instance.currentOrientation;
    final rotationAngle = _rotationAngleFor(orientation, isFrontCamera: true);
    final frames = <Map<String, dynamic>>[];

    for (final imageFile in imageFiles) {
      final imageBytes = await imageFile.readAsBytes();
      final decodedImage = img.decodeImage(imageBytes);
      if (decodedImage == null) {
        throw Exception('Failed to decode captured image');
      }
      final timestampSeconds = DateTime.now().millisecondsSinceEpoch / 1000.0;
      frames.add({
        'frame_data': base64Encode(imageBytes),
        'timestamp': timestampSeconds,
        'width': decodedImage.width,
        'height': decodedImage.height,
        'format': 'jpeg',
        'orientation': orientation.toString(),
        'rotation_angle': rotationAngle,
        'fps': 8,
        'camera_facing': 'front',
      });
    }

    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions/$sessionUuid/feeds/front-burst${capturePhase == 'post_qr_retry' ? '/retry' : ''}'),
      headers: _jsonHeaders(token),
      body: jsonEncode({
        'device_id': deviceUuid,
        'session_uuid': sessionUuid,
        'capture_phase': capturePhase,
        'frames': frames,
        'captured_at': DateTime.now().toUtc().toIso8601String(),
        'transport_source': 'mobile_streaming_service',
      }),
    );

    return PresenceMobileDetectionAttempt.fromJson(_unwrapData(response));
  }

  Future<PresenceMobileSession> submitQrHit({
    required String sessionUuid,
    required String qrToken,
  }) async {
    final token = _requireAuthToken();
    final baseUrl = await _presenceBaseUrl();
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/presence/mobile/sessions/$sessionUuid/qr-hit'),
      headers: _jsonHeaders(token),
      body: jsonEncode({
        'qr_token': qrToken,
        'installation_uuid': 'local-installation',
        'scanned_at': DateTime.now().toUtc().toIso8601String(),
      }),
    );
    return PresenceMobileSession.fromJson(_unwrapData(response));
  }

  String parseQrToken(String rawValue) {
    final trimmed = rawValue.trim();
    if (trimmed.startsWith('{')) {
      final decoded = jsonDecode(trimmed);
      if (decoded is Map<String, dynamic> && decoded['qr_token'] != null) {
        return decoded['qr_token'].toString();
      }
    }
    return trimmed;
  }

  Map<String, String> _jsonHeaders(String token) {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  Future<String> _presenceBaseUrl() async {
    final uri = Uri.tryParse(_authService.serverUrl);
    if (uri != null && uri.host.isNotEmpty) {
      final gatewayUrl = 'http://${uri.host}:8080';
      if (await _isHealthyGateway(gatewayUrl)) {
        return gatewayUrl;
      }
    }

    final discoveredPresence = await _discoveryConfig.findService('ppl-meta-presence');
    if (discoveredPresence != null && discoveredPresence.baseUrl.isNotEmpty) {
      return discoveredPresence.baseUrl;
    }

    final platformServices = _authService.platformServices;
    final microservices = platformServices?['microservices'] as Map<String, dynamic>?;
    final presenceService = microservices?['presence'] as Map<String, dynamic>?;
    final endpoints = presenceService?['endpoints'] as Map<String, dynamic>?;
    final directEndpoint = (endpoints?['local'] ?? endpoints?['tailscale'] ?? presenceService?['endpoint'])?.toString();
    if (directEndpoint != null && directEndpoint.isNotEmpty) {
      return directEndpoint;
    }

    throw Exception('Authenticated server URL is not available');
  }

  Future<bool> _isHealthyGateway(String gatewayUrl) async {
    try {
      final response = await http
          .get(
            Uri.parse('$gatewayUrl/health/gateway'),
            headers: const {'Accept': 'application/json'},
          )
          .timeout(const Duration(seconds: 2));
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
  }

  String _requireAuthToken() {
    final token = _authService.authToken;
    if (token == null || token.isEmpty) {
      throw Exception('Authentication token is not available');
    }
    return token;
  }

  Map<String, dynamic> _unwrapData(http.Response response) {
    final decoded = jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = decoded is Map<String, dynamic> ? decoded['detail'] ?? decoded['error'] : null;
      throw Exception(detail?.toString() ?? 'Request failed with status ${response.statusCode}');
    }
    if (decoded is Map<String, dynamic>) {
      final data = decoded['data'];
      if (data is Map<String, dynamic>) {
        return data;
      }
    }
    throw Exception('Unexpected response payload');
  }

  int _rotationAngleFor(DeviceOrientation orientation, {required bool isFrontCamera}) {
    switch (orientation) {
      case DeviceOrientation.portraitUp:
        return isFrontCamera ? 270 : 90;
      case DeviceOrientation.landscapeLeft:
        return isFrontCamera ? 180 : 180;
      case DeviceOrientation.portraitDown:
        return isFrontCamera ? 90 : 270;
      case DeviceOrientation.landscapeRight:
        return isFrontCamera ? 0 : 0;
    }
  }
}