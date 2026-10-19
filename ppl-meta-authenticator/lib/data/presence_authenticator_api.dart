import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../services/safe_shared_preferences.dart';

import '../core/auth/auth_service.dart';
import '../core/device/soft_device_id.dart';

class AuthenticatorEnrollment {
  final bool enrolled;
  final String? mvrPeopleUuid;
  final String? pppUuid;
  final String? enrolledAt;

  AuthenticatorEnrollment({
    required this.enrolled,
    this.mvrPeopleUuid,
    this.pppUuid,
    this.enrolledAt,
  });

  factory AuthenticatorEnrollment.fromJson(Map<String, dynamic> json) {
    return AuthenticatorEnrollment(
      enrolled: json['enrolled'] == true,
      mvrPeopleUuid: json['mvr_people_uuid']?.toString(),
      pppUuid: json['ppp_uuid']?.toString(),
      enrolledAt: json['enrolled_at']?.toString(),
    );
  }
}

class PresenceSessionSummary {
  final String sessionUuid;
  final String sessionMode;
  final String status;
  final String decision;
  final String? detectionStatus;
  final String? qrToken;

  PresenceSessionSummary({
    required this.sessionUuid,
    required this.sessionMode,
    required this.status,
    required this.decision,
    this.detectionStatus,
    this.qrToken,
  });

  factory PresenceSessionSummary.fromJson(Map<String, dynamic> json) {
    return PresenceSessionSummary(
      sessionUuid: json['session_uuid']?.toString() ?? '',
      sessionMode: json['session_mode']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      decision: json['decision']?.toString() ?? 'pending',
      detectionStatus: json['detection_status']?.toString(),
      qrToken: json['qr_token']?.toString(),
    );
  }
}

class PresenceResultSummary {
  final String sessionUuid;
  final String decision;
  final String status;
  final String reasonCode;
  final String? matchedMemberName;

  PresenceResultSummary({
    required this.sessionUuid,
    required this.decision,
    required this.status,
    required this.reasonCode,
    this.matchedMemberName,
  });

  factory PresenceResultSummary.fromJson(Map<String, dynamic> json) {
    return PresenceResultSummary(
      sessionUuid: json['session_uuid']?.toString() ?? '',
      decision: json['decision']?.toString() ?? 'pending',
      status: json['status']?.toString() ?? '',
      reasonCode: json['reason_code']?.toString() ?? 'pending',
      matchedMemberName: json['matched_member_name']?.toString(),
    );
  }

  bool get isGranted => decision == 'granted';
}

/// Presence authenticator + mobile session client (gateway only).
class PresenceAuthenticatorApi {
  PresenceAuthenticatorApi({AuthService? auth}) : _auth = auth ?? AuthService.instance;

  final AuthService _auth;

  static const _localMvrKey = 'authenticator_local_mvr_people_uuid';
  static const _localEnrolledAtKey = 'authenticator_local_enrolled_at';

  String get _base {
    final uri = Uri.tryParse(_auth.serverUrl);
    if (uri == null || uri.host.isEmpty) {
      throw Exception('Not signed in to a platform');
    }
    return 'http://${uri.host}:${uri.hasPort ? uri.port : 8080}';
  }

  Future<String> resolveInstallationUuid() async {
    final response = await http.get(
      Uri.parse('$_base/api/v1/presence/installations/current'),
      headers: _auth.authHeaders(),
    );
    final data = _unwrap(response);
    return data['installation_uuid']?.toString() ?? 'local-installation';
  }

  Future<AuthenticatorEnrollment> getEnrollment() async {
    final response = await http.get(
      Uri.parse('$_base/api/v1/presence/authenticator/enrollment'),
      headers: _auth.authHeaders(),
    );
    final data = _unwrap(response);
    final enrollment = AuthenticatorEnrollment.fromJson(data);
    if (enrollment.enrolled && enrollment.mvrPeopleUuid != null) {
      await _persistLocalBinding(enrollment.mvrPeopleUuid!, enrollment.enrolledAt);
    } else {
      // Server is source of truth — drop stale local binding after lab clears / re-enroll.
      await clearLocalEnrollment();
    }
    return enrollment;
  }

  Future<AuthenticatorEnrollment> enrollFace(File imageFile) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$_base/api/v1/presence/authenticator/enroll-face'),
    );
    request.headers.addAll(_auth.authHeaders());
    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        imageFile.path,
        contentType: MediaType('image', 'jpeg'),
      ),
    );
    final streamed = await request.send().timeout(const Duration(seconds: 90));
    final response = await http.Response.fromStream(streamed);
    final data = _unwrap(response);
    final mvr = data['mvr_people_uuid']?.toString();
    if (mvr == null || mvr.isEmpty) {
      throw Exception('Enrollment did not return mvr_people_uuid');
    }
    await _persistLocalBinding(mvr, data['enrolled_at']?.toString());
    return AuthenticatorEnrollment(
      enrolled: true,
      mvrPeopleUuid: mvr,
      pppUuid: data['ppp_uuid']?.toString(),
      enrolledAt: data['enrolled_at']?.toString(),
    );
  }

  Future<Map<String, dynamic>> verifyFace({
    required File imageFile,
    String? sessionUuid,
  }) async {
    final uri = Uri.parse('$_base/api/v1/presence/authenticator/verify-face').replace(
      queryParameters: {
        if (sessionUuid != null && sessionUuid.isNotEmpty) 'session_uuid': sessionUuid,
      },
    );
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(_auth.authHeaders());
    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        imageFile.path,
        contentType: MediaType('image', 'jpeg'),
      ),
    );
    final streamed = await request.send().timeout(const Duration(seconds: 90));
    final response = await http.Response.fromStream(streamed);
    return _unwrap(response);
  }

  Future<PresenceSessionSummary> createSession(String sessionMode) async {
    final deviceUuid = await SoftDeviceId.instance.getOrCreate();
    final response = await http.post(
      Uri.parse('$_base/api/v1/presence/mobile/sessions'),
      headers: {
        ..._auth.authHeaders(),
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'session_mode': sessionMode,
        'device_uuid': deviceUuid,
        'device_name': 'EyeNet Authenticator',
        'device_platform': Platform.operatingSystem,
        'app_version': 'ppl-meta-authenticator/1.0.0',
        'client_origin': 'authenticator',
      }),
    );
    return PresenceSessionSummary.fromJson(_unwrap(response));
  }

  Future<PresenceSessionSummary> submitQrHit({
    required String sessionUuid,
    required String qrToken,
  }) async {
    final installationUuid = await resolveInstallationUuid();
    final response = await http.post(
      Uri.parse('$_base/api/v1/presence/mobile/sessions/$sessionUuid/qr-hit'),
      headers: {
        ..._auth.authHeaders(),
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'qr_token': qrToken,
        'installation_uuid': installationUuid,
        'scanned_at': DateTime.now().toUtc().toIso8601String(),
      }),
    );
    return PresenceSessionSummary.fromJson(_unwrap(response));
  }

  Future<Map<String, dynamic>> renderOwnerQr() async {
    final installationUuid = await resolveInstallationUuid();
    final response = await http.post(
      Uri.parse('$_base/api/v1/presence/qr/render-owner'),
      headers: {
        ..._auth.authHeaders(),
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'installation_uuid': installationUuid,
        'owner_display_name': _auth.userEmail,
      }),
    );
    return _unwrap(response);
  }

  Future<PresenceResultSummary> getResult(String sessionUuid) async {
    final response = await http.get(
      Uri.parse('$_base/api/v1/presence/mobile/sessions/$sessionUuid/result'),
      headers: _auth.authHeaders(),
    );
    return PresenceResultSummary.fromJson(_unwrap(response));
  }

  Future<String?> localMvrPeopleUuid() async {
    final prefs = await SafeSharedPreferences.getInstance();
    return prefs.getString(_localMvrKey);
  }

  Future<void> clearLocalEnrollment() async {
    final prefs = await SafeSharedPreferences.getInstance();
    await prefs.remove(_localMvrKey);
    await prefs.remove(_localEnrolledAtKey);
  }

  Future<void> _persistLocalBinding(String mvrUuid, String? enrolledAt) async {
    final prefs = await SafeSharedPreferences.getInstance();
    await prefs.setString(_localMvrKey, mvrUuid);
    if (enrolledAt != null) {
      await prefs.setString(_localEnrolledAtKey, enrolledAt);
    }
  }

  String parseQrToken(String raw) {
    final trimmed = raw.trim();
    if (trimmed.startsWith('{')) {
      final decoded = jsonDecode(trimmed);
      if (decoded is Map<String, dynamic> && decoded['qr_token'] != null) {
        return decoded['qr_token'].toString();
      }
    }
    return trimmed;
  }

  Map<String, dynamic> _unwrap(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }
    final body = jsonDecode(response.body);
    if (body is Map<String, dynamic>) {
      if (body['success'] == true && body['data'] is Map<String, dynamic>) {
        return body['data'] as Map<String, dynamic>;
      }
      if (body['payload'] is Map<String, dynamic>) {
        return {
          ...body,
          ...(body['payload'] as Map<String, dynamic>),
        };
      }
      return body;
    }
    throw Exception('Unexpected response: ${response.body}');
  }
}
