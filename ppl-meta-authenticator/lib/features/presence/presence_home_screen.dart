import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/auth/auth_service.dart';
import '../../data/presence_authenticator_api.dart';
import '../enroll/enroll_gate.dart';
import '../enroll/face_capture_screen.dart';
import '../setup/setup_screen.dart';
import 'presence_result_screen.dart';
import 'qr_scan_screen.dart';

class PresenceHomeScreen extends StatefulWidget {
  const PresenceHomeScreen({super.key});

  @override
  State<PresenceHomeScreen> createState() => _PresenceHomeScreenState();
}

class _PresenceHomeScreenState extends State<PresenceHomeScreen> {
  final _api = PresenceAuthenticatorApi();
  String? _mvrUuid;
  bool _busy = false;
  String? _status;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final enrollment = await _api.getEnrollment();
    if (!mounted) return;
    if (!enrollment.enrolled) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const EnrollGate()),
      );
      return;
    }
    setState(() {
      _mvrUuid = enrollment.mvrPeopleUuid;
    });
  }

  Future<void> _withBusy(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _status = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _status = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _showOwnerQr() async {
    await _withBusy(() async {
      final data = await _api.renderOwnerQr();
      final payload = data['payload'] is Map<String, dynamic>
          ? data['payload'] as Map<String, dynamic>
          : data;
      final token = payload['qr_token']?.toString() ?? data['qr_token']?.toString();
      final qrData = token == null
          ? jsonEncode(payload)
          : jsonEncode(payload.isNotEmpty ? payload : {'qr_token': token});
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('User Owner QR'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 220,
                height: 220,
                child: QrImageView(data: qrData, size: 220),
              ),
              const SizedBox(height: 8),
              Text(context.read<AuthService>().userEmail ?? 'Owner QR ready'),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
          ],
        ),
      );
    });
  }

  Future<PresenceResultSummary> _pollResult(String sessionUuid) async {
    for (var i = 0; i < 20; i++) {
      final result = await _api.getResult(sessionUuid);
      if (result.decision != 'pending') return result;
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    return _api.getResult(sessionUuid);
  }

  Future<void> _scanStationQrOnly() async {
    await _withBusy(() async {
      // Scan first so backing out of the camera does not leave an orphan
      // session that later expires as FAILED in the Presence Sessions tab.
      if (!mounted) return;
      final raw = await Navigator.of(context).push<String>(
        MaterialPageRoute(builder: (_) => const QrScanScreen()),
      );
      if (raw == null) return;
      final token = _api.parseQrToken(raw);
      final session = await _api.createSession('qr_only');
      await _api.submitQrHit(sessionUuid: session.sessionUuid, qrToken: token);
      final result = await _pollResult(session.sessionUuid);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PresenceResultScreen(result: result)),
      );
    });
  }

  Future<void> _videoMatch() async {
    await _withBusy(() async {
      final session = await _api.createSession('camera_only');
      if (!mounted) return;
      final file = await Navigator.of(context).push<File>(
        MaterialPageRoute(
          builder: (_) => const FaceCaptureScreen(title: 'Video match'),
        ),
      );
      if (file == null) return;
      final verify = await _api.verifyFace(
        imageFile: file,
        sessionUuid: session.sessionUuid,
      );
      if (verify['verified'] != true) {
        final score = verify['similarity_score'];
        final scoreText = score is num ? score.toStringAsFixed(3) : score?.toString();
        throw Exception(
          '${verify['message'] ?? 'Face verify failed'}'
          '${scoreText != null ? ' (score=$scoreText)' : ''}',
        );
      }
      final result = await _pollResult(session.sessionUuid);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PresenceResultScreen(result: result)),
      );
    });
  }

  Future<void> _qrPlusVideo() async {
    await _withBusy(() async {
      final session = await _api.createSession('qr_plus_camera');
      if (!mounted) return;
      final file = await Navigator.of(context).push<File>(
        MaterialPageRoute(
          builder: (_) => const FaceCaptureScreen(title: 'Verify face'),
        ),
      );
      if (file == null) return;
      final verify = await _api.verifyFace(
        imageFile: file,
        sessionUuid: session.sessionUuid,
      );
      if (verify['verified'] != true) {
        final score = verify['similarity_score'];
        final scoreText = score is num ? score.toStringAsFixed(3) : score?.toString();
        throw Exception(
          '${verify['message'] ?? 'Face verify failed'}'
          '${scoreText != null ? ' (score=$scoreText)' : ''}',
        );
      }
      if (!mounted) return;
      final raw = await Navigator.of(context).push<String>(
        MaterialPageRoute(builder: (_) => const QrScanScreen()),
      );
      if (raw == null) return;
      await _api.submitQrHit(
        sessionUuid: session.sessionUuid,
        qrToken: _api.parseQrToken(raw),
      );
      final result = await _pollResult(session.sessionUuid);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PresenceResultScreen(result: result)),
      );
    });
  }

  Future<void> _reEnroll() async {
    await _api.clearLocalEnrollment();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const EnrollGate()),
    );
  }

  Future<void> _logout() async {
    await context.read<AuthService>().logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const SetupScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final email = context.read<AuthService>().userEmail ?? 'Signed in';
    return Scaffold(
      appBar: AppBar(
        title: const Text('Presence'),
        actions: [
          IconButton(
            tooltip: 'Re-enroll face',
            onPressed: _busy ? null : _reEnroll,
            icon: const Icon(Icons.face_retouching_natural),
          ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: _busy ? null : _logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(email, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                _mvrUuid == null
                    ? 'No local MVR binding'
                    : 'Enrolled MVR: ${_mvrUuid!.substring(0, _mvrUuid!.length.clamp(0, 8))}…',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 20),
              _ActionTile(
                icon: Icons.badge_outlined,
                title: 'Owner QR',
                subtitle: 'Show your identity QR for the desk camera',
                onTap: _busy ? null : _showOwnerQr,
              ),
              _ActionTile(
                icon: Icons.qr_code_scanner,
                title: 'Scan station QR',
                subtitle: 'QR-only check-in (check_in grant)',
                onTap: _busy ? null : _scanStationQrOnly,
              ),
              _ActionTile(
                icon: Icons.videocam_outlined,
                title: 'Video match',
                subtitle: 'Live face verify against enrolled MVR',
                onTap: _busy ? null : _videoMatch,
              ),
              _ActionTile(
                icon: Icons.verified_user_outlined,
                title: 'QR + Video',
                subtitle: 'Verify face, then scan station QR',
                onTap: _busy ? null : _qrPlusVideo,
              ),
              if (_status != null) ...[
                const SizedBox(height: 16),
                Text(
                  _status!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
          if (_busy)
            const ColoredBox(
              color: Color(0x66000000),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
        onTap: onTap,
      ),
    );
  }
}
