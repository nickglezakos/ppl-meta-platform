import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../../../core/providers/authentication_provider.dart';
import '../../../features/camera/screens/camera_screen.dart';
import '../../../models/presence_mobile_models.dart';
import '../../../services/presence_mobile_service.dart';

class MobilePresenceScreen extends StatefulWidget {
  const MobilePresenceScreen({super.key});

  @override
  State<MobilePresenceScreen> createState() => _MobilePresenceScreenState();
}

class _MobilePresenceScreenState extends State<MobilePresenceScreen> {
  final PresenceMobileService _presenceService = PresenceMobileService();

  String _sessionMode = 'qr_plus_camera';
  String? _deviceUuid;
  PresenceMobileSession? _session;
  PresenceMobileResult? _result;
  PresenceMobileDetectionAttempt? _lastAttempt;
  PresenceMobileDetectionStatus? _detectionStatus;
  CameraController? _frontCameraController;
  bool _isBusy = false;
  bool _autoPolling = false;
  String? _statusMessage;
  Timer? _pollTimer;
  String? _lastTerminalAlertKey;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _frontCameraController?.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    await _runBusy(() async {
      final deviceUuid = await _presenceService.ensureRegisteredDevice();
      await _ensureFrontCameraPreview();
      if (!mounted) {
        return;
      }
      setState(() {
        _deviceUuid = deviceUuid;
        _statusMessage = 'Mobile presence is ready. Device anchor restored from the existing camera client registration.';
      });
    });
  }

  Future<void> _ensureFrontCameraPreview() async {
    if (_sessionMode == 'qr_only') {
      return;
    }
    if (_frontCameraController != null && _frontCameraController!.value.isInitialized) {
      return;
    }

    final cameras = await availableCameras();
    final frontCamera = cameras.where((camera) => camera.lensDirection == CameraLensDirection.front).firstOrNull;
    if (frontCamera == null) {
      throw Exception('Front camera is not available on this device');
    }

    final controller = CameraController(frontCamera, ResolutionPreset.medium, enableAudio: false);
    await controller.initialize();
    if (!mounted) {
      await controller.dispose();
      return;
    }
    setState(() {
      _frontCameraController = controller;
    });
  }

  Future<void> _startSession() async {
    await _runBusy(() async {
      final session = await _presenceService.createSession(sessionMode: _sessionMode);
      if (!mounted) {
        return;
      }
      setState(() {
        _session = session;
        _result = null;
        _lastAttempt = null;
        _detectionStatus = null;
        _lastTerminalAlertKey = null;
        _statusMessage = 'Presence session created. Continue with the mode-specific steps below.';
      });
    });
  }

  Future<void> _captureFrontBurst({required String capturePhase}) async {
    final session = _session;
    if (session == null) {
      return;
    }

    await _runBusy(() async {
      await _ensureFrontCameraPreview();
      final controller = _frontCameraController;
      if (controller == null || !controller.value.isInitialized) {
        throw Exception('Front camera is not initialized');
      }

      final images = <XFile>[];
      for (var index = 0; index < 3; index++) {
        images.add(await controller.takePicture());
        if (index < 2) {
          await Future<void>.delayed(const Duration(milliseconds: 220));
        }
      }

      final attempt = await _presenceService.uploadFrontBurst(
        sessionUuid: session.sessionUuid,
        imageFiles: images,
        capturePhase: capturePhase,
      );
      final refreshedSession = await _presenceService.getSession(session.sessionUuid);
      final detectionStatus = await _presenceService.getDetectionStatus(session.sessionUuid);

      if (!mounted) {
        return;
      }
      setState(() {
        _lastAttempt = attempt;
        _session = refreshedSession;
        _detectionStatus = detectionStatus;
        _statusMessage = detectionStatus.requiresRetry
            ? 'The backend requested a retry burst. Capture the retry burst to continue.'
            : capturePhase == 'pre_qr'
                ? 'Front burst uploaded. Continue to QR scan for mixed-mode presence.'
                : 'Retry front burst uploaded. Polling for final presence outcome.';
      });

      if (detectionStatus.requiresRetry) {
        _setAutoPolling(false);
      } else if (_sessionMode == 'camera_only' || capturePhase == 'post_qr_retry') {
        _setAutoPolling(true);
        await _refreshResult();
      }
    });
  }

  Future<void> _scanQrAndSubmit() async {
    final session = _session;
    if (session == null) {
      return;
    }

    final navigator = Navigator.of(context);
    await _frontCameraController?.dispose();
    _frontCameraController = null;

    final rawValue = await navigator.push<String>(
      MaterialPageRoute(builder: (_) => const _PresenceQrScannerScreen()),
    );

    if (!mounted) {
      return;
    }

    if (rawValue == null || rawValue.isEmpty) {
      await _ensureFrontCameraPreview();
      return;
    }

    await _runBusy(() async {
      final qrToken = _presenceService.parseQrToken(rawValue);
      final refreshedSession = await _presenceService.submitQrHit(
        sessionUuid: session.sessionUuid,
        qrToken: qrToken,
      );
      final detectionStatus = await _presenceService.getDetectionStatus(session.sessionUuid);
      if (!mounted) {
        return;
      }
      setState(() {
        _session = refreshedSession;
        _detectionStatus = detectionStatus;
        _statusMessage = detectionStatus.requiresRetry
            ? 'QR resolved. The backend requires a retry burst before final grant.'
            : 'QR hit submitted. Polling for the backend decision now.';
      });
      if (detectionStatus.requiresRetry) {
        _setAutoPolling(false);
      } else {
        _setAutoPolling(true);
        await _refreshResult();
      }
    });

    await _ensureFrontCameraPreview();
  }

  Future<void> _refreshResult() async {
    final session = _session;
    if (session == null) {
      return;
    }

    try {
      final refreshedSession = await _presenceService.getSession(session.sessionUuid);
      final detectionStatus = await _presenceService.getDetectionStatus(session.sessionUuid);
      final result = await _presenceService.getResult(session.sessionUuid);
      if (!mounted) {
        return;
      }
      setState(() {
        _session = refreshedSession;
        _detectionStatus = detectionStatus;
        _result = result;
        _statusMessage = result.isTerminal
            ? 'Presence flow reached a terminal backend decision.'
            : detectionStatus.requiresRetry
                ? 'Presence is waiting for a retry burst before final resolution.'
                : 'Presence session is still in progress on the platform.';
      });
      if (result.isTerminal || detectionStatus.requiresRetry) {
        _setAutoPolling(false);
      }
      _showTerminalFailureAlertIfNeeded(
        result: result,
        session: refreshedSession,
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = error.toString();
      });
    }
  }

  void _showTerminalFailureAlertIfNeeded({
    PresenceMobileResult? result,
    PresenceMobileSession? session,
  }) {
    if (!mounted) {
      return;
    }
    final resultDecision = result?.decision;
    final sessionDecision = session?.decision;
    final sessionStatus = session?.status;
    final shouldAlertFromResult = resultDecision == 'failed' || resultDecision == 'denied';
    final shouldAlertFromSession =
        sessionDecision == 'failed' || sessionDecision == 'denied' || sessionStatus == 'failed';
    if (!shouldAlertFromResult && !shouldAlertFromSession) {
      return;
    }

    final sessionUuid = result?.sessionUuid ?? session?.sessionUuid ?? '';
    final reasonCode = result?.reasonCode ?? session?.failureReasonCode ?? 'presence_failed';
    final decision = resultDecision ?? sessionDecision ?? sessionStatus ?? 'failed';
    final alertKey = '$sessionUuid:$reasonCode:$decision';
    if (_lastTerminalAlertKey == alertKey) {
      return;
    }
    _lastTerminalAlertKey = alertKey;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Presence Unsuccessful'),
        content: Text(_humanizeFailureReason(reasonCode)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  String _humanizeFailureReason(String reasonCode) {
    switch (reasonCode) {
      case 'presence_session_expired':
        return 'The presence session expired before a successful match was completed.';
      case 'presence_attempt_limit_reached':
        return 'The presence session reached the maximum number of unsuccessful attempts.';
      case 'presence_no_match':
        return 'The presence session ended without a matching person.';
      default:
        return 'The presence session ended unsuccessfully.';
    }
  }

  void _setAutoPolling(bool enabled) {
    _pollTimer?.cancel();
    if (!enabled) {
      if (mounted) {
        setState(() {
          _autoPolling = false;
        });
      }
      return;
    }

    if (mounted) {
      setState(() {
        _autoPolling = true;
      });
    }

    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!_isBusy && mounted) {
        _refreshResult();
      }
    });
  }

  Future<void> _runBusy(Future<void> Function() action) async {
    if (_isBusy) {
      return;
    }
    setState(() {
      _isBusy = true;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) {
        setState(() {
          _statusMessage = error.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isBusy = false;
        });
      }
    }
  }

  Future<bool> _handleBack() async {
    _setAutoPolling(false);
    if (!mounted) {
      return true;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const CameraScreen()),
    );
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthenticationProvider>();

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (!didPop) {
          await _handleBack();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mobile Presence'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _handleBack,
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Presence execution reuses the existing mobile client authentication and registered camera identity.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Connection', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Text('User: ${authProvider.getUserDisplayName()}'),
                    Text('Server: ${authProvider.serverUrl ?? 'Not connected'}'),
                    Text('Device Anchor: ${_deviceUuid ?? 'Resolving...'}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _sessionMode,
              decoration: const InputDecoration(labelText: 'Presence Mode'),
              items: const [
                DropdownMenuItem(value: 'qr_only', child: Text('QR Only')),
                DropdownMenuItem(value: 'camera_only', child: Text('Camera Only')),
                DropdownMenuItem(value: 'qr_plus_camera', child: Text('QR + Camera')),
              ],
              onChanged: _isBusy
                  ? null
                  : (value) async {
                      if (value == null) {
                        return;
                      }
                      setState(() {
                        _sessionMode = value;
                      });
                      if (value != 'qr_only') {
                        await _ensureFrontCameraPreview();
                      }
                    },
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _isBusy ? null : _startSession,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Presence Session'),
            ),
            const SizedBox(height: 16),
            if (_sessionMode != 'qr_only')
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Front Burst', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      if (_frontCameraController != null && _frontCameraController!.value.isInitialized)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: AspectRatio(
                            aspectRatio: _frontCameraController!.value.aspectRatio,
                            child: CameraPreview(_frontCameraController!),
                          ),
                        )
                      else
                        const Text('Front camera preview is not ready yet.'),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          OutlinedButton.icon(
                            onPressed: _isBusy || _session == null ? null : () => _captureFrontBurst(capturePhase: 'pre_qr'),
                            icon: const Icon(Icons.camera_front),
                            label: Text(_sessionMode == 'camera_only' ? 'Capture 3-Frame Burst' : 'Capture Pre-QR Burst'),
                          ),
                          if ((_session?.retryAllowed ?? false) && (_detectionStatus?.requiresRetry ?? false))
                            OutlinedButton.icon(
                              onPressed: _isBusy ? null : () => _captureFrontBurst(capturePhase: 'post_qr_retry'),
                              icon: const Icon(Icons.refresh),
                              label: const Text('Capture 3-Frame Retry Burst'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            if (_sessionMode != 'camera_only')
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('QR Scan', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      const Text('Use the back camera scanner to resolve the platform-issued QR token into the active session.'),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: _isBusy || _session == null ? null : _scanQrAndSubmit,
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('Scan QR And Submit'),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Session State', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (_session == null)
                      const Text('No presence session started yet.')
                    else ...[
                      Text('Session UUID: ${_session!.sessionUuid}'),
                      Text('Status: ${_session!.status}'),
                      Text('QR Status: ${_session!.qrStatus}'),
                      Text('Detection: ${_session!.detectionStatus}'),
                      Text('Grant Type: ${_session!.grantType}'),
                      if (_detectionStatus != null)
                        Text('Decision State: ${_detectionStatus!.presenceDecisionState}'),
                      if (_detectionStatus != null)
                        Text('Detection Poll Status: ${_detectionStatus!.instantDetectionStatus}'),
                    ],
                    if (_lastAttempt != null) ...[
                      const SizedBox(height: 8),
                      Text('Last Burst Attempt: ${_lastAttempt!.attemptIndex} (${_lastAttempt!.capturePhase})'),
                    ],
                    if (_result != null) ...[
                      const SizedBox(height: 12),
                      Text('Decision: ${_result!.decision}'),
                      Text('Reason: ${_result!.reasonCode}'),
                      if (_result!.policySource != null) Text('Policy Source: ${_result!.policySource}'),
                      if (_result!.actionExecutionStatus != null) Text('Action Status: ${_result!.actionExecutionStatus}'),
                    ],
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        OutlinedButton.icon(
                          onPressed: _session == null || _isBusy ? null : _refreshResult,
                          icon: const Icon(Icons.sync),
                          label: const Text('Refresh Result'),
                        ),
                        FilterChip(
                          label: const Text('Auto Poll'),
                          selected: _autoPolling,
                          onSelected: (_session == null || _isBusy) ? null : _setAutoPolling,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (_statusMessage != null)
              Text(
                _statusMessage!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            if (_isBusy) ...[
              const SizedBox(height: 16),
              const Center(child: CircularProgressIndicator()),
            ],
          ],
        ),
      ),
    );
  }
}

class _PresenceQrScannerScreen extends StatefulWidget {
  const _PresenceQrScannerScreen();

  @override
  State<_PresenceQrScannerScreen> createState() => _PresenceQrScannerScreenState();
}

class _PresenceQrScannerScreenState extends State<_PresenceQrScannerScreen> {
  final MobileScannerController _controller = MobileScannerController(facing: CameraFacing.back);
  bool _handled = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Presence QR')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: (capture) {
              if (_handled) {
                return;
              }
              final value = capture.barcodes.firstOrNull?.rawValue;
              if (value == null || value.isEmpty) {
                return;
              }
              _handled = true;
              Navigator.of(context).pop(value);
            },
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              margin: const EdgeInsets.all(24),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'Point the back camera at the session QR issued by the platform.',
                style: TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }
}