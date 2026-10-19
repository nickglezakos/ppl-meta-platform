import 'dart:io';

import 'package:flutter/material.dart';

import '../../data/presence_authenticator_api.dart';
import '../presence/presence_home_screen.dart';
import 'face_capture_screen.dart';

/// Forces one-time face enrollment via Presence → vmeta before home.
class EnrollGate extends StatefulWidget {
  const EnrollGate({super.key});

  @override
  State<EnrollGate> createState() => _EnrollGateState();
}

class _EnrollGateState extends State<EnrollGate> {
  final _api = PresenceAuthenticatorApi();
  bool _loading = true;
  String? _status;
  String? _error;
  AuthenticatorEnrollment? _enrollment;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final enrollment = await _api.getEnrollment();
      if (!mounted) return;
      if (enrollment.enrolled) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const PresenceHomeScreen()),
        );
        return;
      }
      setState(() {
        _enrollment = enrollment;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _enroll() async {
    final file = await Navigator.of(context).push<File>(
      MaterialPageRoute(
        builder: (_) => const FaceCaptureScreen(title: 'Enroll face'),
      ),
    );
    if (file == null) return;
    setState(() {
      _loading = true;
      _status = 'Uploading face to platform (vmeta)…';
      _error = null;
    });
    try {
      await _api.enrollFace(file);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const PresenceHomeScreen()),
      );
    } catch (e) {
      setState(() {
        _error = 'Enrollment failed: $e';
        _status = null;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(height: 16),
                Text(
                  _status ?? 'Checking enrollment…',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Face enrollment')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Create your Presence identity once',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'We send a short face capture to the platform (vmeta) to create '
              'one MVR person for your account. Later check-ins verify live '
              'against that enrollment — this phone is not registered as a camera.',
            ),
            if (_enrollment != null) ...[
              const SizedBox(height: 12),
              Text('Status: not enrolled yet'),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              const SizedBox(height: 8),
              const Text(
                'If this was the first enroll after a lab restart, vmeta may have been '
                'downloading face models. Wait a minute and try again.',
              ),
            ],
            const Spacer(),
            FilledButton(
              onPressed: _enroll,
              child: const Text('Capture & enroll'),
            ),
            TextButton(
              onPressed: _check,
              child: const Text('Refresh status'),
            ),
          ],
        ),
      ),
    );
  }
}
