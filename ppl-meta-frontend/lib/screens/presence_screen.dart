import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../core/providers/auth_provider.dart';
import '../models/api_response.dart';
import '../core/theme/app_theme.dart';
import '../models/presence_models.dart';
import '../services/presence_api_client.dart';
import '../widgets/custom_app_bar.dart';
import '../core/providers/camera_providers.dart';

class PresenceScreen extends ConsumerStatefulWidget {
  final bool stationMode;

  const PresenceScreen({super.key, this.stationMode = false});

  @override
  ConsumerState<PresenceScreen> createState() => _PresenceScreenState();
}

class _PresenceScreenState extends ConsumerState<PresenceScreen> {
  PresenceAnalyticsSummary? _summary;
  PresenceInstallationContext? _installationContext;
  List<PresenceAnalyticsBucket> _sessionModes = const [];
  List<PresenceAnalyticsBucket> _grantTypes = const [];
  List<PresenceSessionTraceSummary> _recentSessions = const [];
  List<PresenceCameraOption> _cameras = const [];
  List<PresenceGroupSummary> _groups = const [];
  PresenceLiveSession? _activeSession;
  PresenceQrPayload? _currentQr;
  PresenceResultDetails? _activeResult;
  PresenceQrValidation? _qrValidation;
  bool _isLoading = true;
  bool _isSubmittingAdminAction = false;
  String? _error;
  String _selectedExecutionMode = 'qr_plus_camera';
  bool _autoRefreshExecution = false;
  Timer? _executionPollTimer;
  final TextEditingController _deviceReferenceController = TextEditingController();
  final TextEditingController _deviceDisplayNameController = TextEditingController();
  final TextEditingController _locationLabelController = TextEditingController();
  final TextEditingController _ownerDisplayNameController = TextEditingController();
  String? _lastTerminalAlertSessionKey;
  String? _lastGrantedAlertSessionKey;

  PresenceApiClient get _apiClient => ref.read(presenceApiClientProvider);

  @override
  void initState() {
    super.initState();
    _deviceReferenceController.text = widget.stationMode ? 'presence-web-station' : 'presence-web-console';
    _deviceDisplayNameController.text = widget.stationMode ? 'Presence Web Station' : 'Presence Web Console';
    if (widget.stationMode) {
      _selectedExecutionMode = 'qr_plus_camera';
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadPresenceDashboard();
      if (widget.stationMode) {
        _refreshExecutionState(renderIfMissing: true);
      }
    });
  }

  @override
  void dispose() {
    _executionPollTimer?.cancel();
    _deviceReferenceController.dispose();
    _deviceDisplayNameController.dispose();
    _locationLabelController.dispose();
    _ownerDisplayNameController.dispose();
    super.dispose();
  }

  Future<void> _loadPresenceDashboard() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final results = await Future.wait([
      _apiClient.getAnalyticsSummary(),
      _apiClient.getInstallationContext(),
      _apiClient.getBySessionMode(),
      _apiClient.getByGrantType(),
      _apiClient.getSessionTraces(limit: 12),
      _apiClient.getCameras(),
      _apiClient.getGroups(),
    ]);

    final summaryResponse = results[0] as ApiResponse<PresenceAnalyticsSummary>;
    final installationResponse = results[1] as ApiResponse<PresenceInstallationContext>;
    final modeResponse = results[2] as ApiResponse<List<PresenceAnalyticsBucket>>;
    final grantResponse = results[3] as ApiResponse<List<PresenceAnalyticsBucket>>;
    final traceResponse = results[4] as ApiResponse<List<PresenceSessionTraceSummary>>;
    final camerasResponse = results[5] as ApiResponse<List<PresenceCameraOption>>;
    final groupsResponse = results[6] as ApiResponse<List<PresenceGroupSummary>>;

    if (!mounted) {
      return;
    }

    if (!summaryResponse.success) {
      setState(() {
        _error = summaryResponse.error ?? 'Failed to load presence dashboard';
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _summary = summaryResponse.data;
      _installationContext = installationResponse.data;
      _sessionModes = modeResponse.data ?? const [];
      _grantTypes = grantResponse.data ?? const [];
      _recentSessions = traceResponse.data ?? const [];
      _cameras = camerasResponse.data ?? const [];
      _groups = groupsResponse.data ?? const [];
      _error = traceResponse.success || modeResponse.success || grantResponse.success
          ? null
          : traceResponse.error ?? modeResponse.error ?? grantResponse.error ?? installationResponse.error;
      _isLoading = false;
    });
  }

  Future<void> _reserveCamera(PresenceCameraOption camera) async {
    final installationUuid = _installationContext?.installationUuid;
    if (installationUuid == null || installationUuid.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.reserveCamera(
      installationUuid: installationUuid,
      resourceUuid: camera.deviceId,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success
              ? 'Reserved camera ${camera.name} for presence.'
              : (response.error ?? 'Failed to reserve camera'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _unreserveCamera(PresenceCameraOption camera) async {
    final installationUuid = _installationContext?.installationUuid;
    if (installationUuid == null || installationUuid.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.unreserveCamera(
      installationUuid: installationUuid,
      resourceUuid: camera.deviceId,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success
              ? 'Released camera ${camera.name.isEmpty ? camera.deviceId : camera.name} from presence.'
              : (response.error ?? 'Failed to unreserve camera'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _resetReservations() async {
    final installationUuid = _installationContext?.installationUuid;
    if (installationUuid == null || installationUuid.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.resetReservations(installationUuid: installationUuid);

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success ? 'Presence reservations cleared.' : (response.error ?? 'Failed to reset reservations'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _showPolicyEditor() async {
    final current = _installationContext?.groupPolicy ?? const PresenceGroupPolicy();
    final updatedPolicy = await showDialog<PresenceGroupPolicy>(
      context: context,
      builder: (context) => _PresencePolicyDialog(initialPolicy: current),
    );

    if (updatedPolicy == null || _installationContext == null) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.updateInstallationPolicy(
      installationUuid: _installationContext!.installationUuid,
      groupPolicy: updatedPolicy,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success ? 'Installation policy updated.' : (response.error ?? 'Failed to update policy'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _showEnsureGroupDialog() async {
    final payload = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => const _EnsurePresenceGroupDialog(),
    );

    if (payload == null || _installationContext == null) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.ensureGroup(
      installationUuid: _installationContext!.installationUuid,
      displayName: payload['display_name'] as String,
      userUuid: payload['user_uuid'] as String?,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success ? 'Presence group ensured.' : (response.error ?? 'Failed to ensure group'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _showSessionInspector(PresenceSessionTraceSummary session) async {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return _PresenceSessionInspector(
          session: session,
          apiClient: _apiClient,
        );
      },
    );
  }

  Future<void> _startExecutionSession() async {
    final installationUuid = _installationContext?.installationUuid;
    final currentUser = ref.read(currentUserProvider);
    final deviceReference = _deviceReferenceController.text.trim();
    if (installationUuid == null || installationUuid.isEmpty || deviceReference.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.createSession(
      sessionMode: _selectedExecutionMode,
      deviceUuid: deviceReference,
      deviceName: currentUser?.username ?? 'presence-web-operator',
      devicePlatform: 'web',
      appVersion: 'presence-web-console',
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _activeSession = response.data;
      _activeResult = null;
      _qrValidation = null;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.success ? 'Presence session started.' : (response.error ?? 'Failed to start session')),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      _setAutoRefreshExecution(true);
      await _refreshExecutionState(renderIfMissing: true);
      await _loadPresenceDashboard();
    }
  }

  String _qrData(PresenceQrPayload payload) {
    if (payload.payload != null) {
      return jsonEncode(payload.payload);
    }
    return payload.qrToken ?? '';
  }

  Future<void> _renderOwnerQr() async {
    final installationUuid = _installationContext?.installationUuid;
    final currentUser = ref.read(currentUserProvider);
    if (installationUuid == null || installationUuid.isEmpty || currentUser == null) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.renderOwnerQr(
      installationUuid: installationUuid,
      ownerDisplayName: _ownerDisplayNameController.text.trim().isEmpty ? currentUser.username : _ownerDisplayNameController.text.trim(),
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _currentQr = response.data;
      _qrValidation = null;
    });
  }

  Future<void> _openWebQrScanner({String sessionMode = 'qr_only'}) async {
    final scannedText = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _PresenceQrScannerSheet(),
    );
    if (scannedText == null || scannedText.trim().isEmpty) {
      return;
    }
    await _consumeScannedQr(scannedText.trim(), sessionMode: sessionMode);
  }

  Future<void> _consumeScannedQr(String rawValue, {String sessionMode = 'qr_only'}) async {
    final installationUuid = _installationContext?.installationUuid;
    final deviceReference = _deviceReferenceController.text.trim();
    if (installationUuid == null || installationUuid.isEmpty || deviceReference.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    Map<String, dynamic>? payload;
    try {
      final decoded = jsonDecode(rawValue);
      if (decoded is Map<String, dynamic>) {
        payload = decoded;
      }
    } catch (_) {
      payload = null;
    }

    var activeSession = _activeSession;
    final requiresNewSession =
        activeSession == null ||
        activeSession.sessionUuid.isEmpty ||
        activeSession.sessionMode != sessionMode;
    if (requiresNewSession) {
      final currentUser = ref.read(currentUserProvider);
      final sessionResponse = await _apiClient.createSession(
        sessionMode: sessionMode,
        deviceUuid: deviceReference,
        deviceName: _deviceDisplayNameController.text.trim().isEmpty ? (currentUser?.username ?? 'presence-web-station') : _deviceDisplayNameController.text.trim(),
        devicePlatform: 'web',
        appVersion: sessionMode == 'qr_plus_camera' ? 'presence-web-scanner-verified' : 'presence-web-scanner',
      );
      if (!sessionResponse.success || sessionResponse.data == null) {
        if (!mounted) {
          return;
        }
        setState(() {
          _isSubmittingAdminAction = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(sessionResponse.error ?? 'Failed to start scanner session'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }
      activeSession = sessionResponse.data;
    }

    ApiResponse<PresenceLiveSession> response;
    if (payload != null && payload['qr_type'] == 'owner_identity') {
      response = await _apiClient.submitOwnerQrHit(
        sessionUuid: activeSession!.sessionUuid,
        qrPayload: payload,
        installationUuid: installationUuid,
      );
    } else {
      final qrToken = payload != null && payload['qr_token'] != null ? payload['qr_token'].toString() : rawValue;
      response = await _apiClient.submitQrHit(
        sessionUuid: activeSession!.sessionUuid,
        qrToken: qrToken,
        installationUuid: installationUuid,
      );
    }

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _activeSession = response.data ?? activeSession;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          response.success
              ? (sessionMode == 'qr_plus_camera'
                  ? 'Scanned QR submitted. Camera verification is starting.'
                  : 'Scanned QR submitted.')
              : (response.error ?? 'Failed to submit scanned QR'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      if (sessionMode == 'qr_plus_camera') {
        _setAutoRefreshExecution(true);
      }
      await _refreshExecutionState();
      await _loadPresenceDashboard();
    }
  }

  Future<void> _refreshExecutionState({bool renderIfMissing = false}) async {
    final installationUuid = _installationContext?.installationUuid;
    final deviceReference = _deviceReferenceController.text.trim();
    if (installationUuid == null || installationUuid.isEmpty || deviceReference.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final qrResponse = await _apiClient.getCurrentQr(
      installationUuid: installationUuid,
      deviceReference: deviceReference,
    );

    ApiResponse<PresenceQrPayload>? renderedQrResponse;
    if (renderIfMissing && qrResponse.success && !(qrResponse.data?.found ?? false) && _selectedExecutionMode != 'camera_only') {
      renderedQrResponse = await _apiClient.renderQr(
        installationUuid: installationUuid,
        deviceReference: deviceReference,
        deviceDisplayName: _deviceDisplayNameController.text.trim().isEmpty ? null : _deviceDisplayNameController.text.trim(),
        location: _locationLabelController.text.trim().isEmpty ? null : {'label': _locationLabelController.text.trim()},
      );
    }

    final effectiveSessionUuid = _activeSession?.sessionUuid ?? qrResponse.data?.sessionUuid ?? renderedQrResponse?.data?.sessionUuid;
    ApiResponse<PresenceLiveSession>? sessionResponse;
    ApiResponse<PresenceResultDetails>? resultResponse;
    if (effectiveSessionUuid != null && effectiveSessionUuid.isNotEmpty) {
      sessionResponse = await _apiClient.getSession(effectiveSessionUuid);
      resultResponse = await _apiClient.getResult(effectiveSessionUuid);
    }

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _currentQr = renderedQrResponse?.data ?? qrResponse.data;
      _activeSession = sessionResponse?.data ?? _activeSession;
      _activeResult = resultResponse?.data;
    });

    _showTerminalFailureAlertIfNeeded();
    _showGrantedAlertIfNeeded();
  }

  void _showGrantedAlertIfNeeded() {
    final session = _activeSession;
    final result = _activeResult;
    if (!mounted) {
      return;
    }

    final granted = result?.decision == 'granted' || session?.decision == 'granted' || result?.status == 'completed';
    if (!granted) {
      return;
    }

    final sessionUuid = result?.sessionUuid ?? session?.sessionUuid ?? '';
    final alertKey = '$sessionUuid:granted';
    if (_lastGrantedAlertSessionKey == alertKey) {
      return;
    }
    _lastGrantedAlertSessionKey = alertKey;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Presence grant awarded.'),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _showTerminalFailureAlertIfNeeded() {
    final session = _activeSession;
    final result = _activeResult;
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
    if (_lastTerminalAlertSessionKey == alertKey) {
      return;
    }
    _lastTerminalAlertSessionKey = alertKey;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(_humanizeFailureReason(reasonCode)),
        backgroundColor: Colors.red,
      ),
    );
  }

  String _humanizeFailureReason(String reasonCode) {
    switch (reasonCode) {
      case 'presence_session_expired':
        return 'Presence session expired before a successful match was completed.';
      case 'presence_attempt_limit_reached':
        return 'Presence session reached the maximum number of unsuccessful attempts.';
      case 'presence_no_match':
        return 'Presence session ended without a matching person.';
      default:
        return 'Presence session ended unsuccessfully.';
    }
  }

  Future<void> _validateCurrentQr() async {
    final qrToken = _currentQr?.qrToken;
    if (qrToken == null || qrToken.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.validateQr(qrToken);

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _qrValidation = response.data;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.success ? 'QR validation refreshed.' : (response.error ?? 'Failed to validate QR')),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );
  }

  Future<void> _submitTestQrHit() async {
    final installationUuid = _installationContext?.installationUuid;
    final sessionUuid = _activeSession?.sessionUuid ?? _currentQr?.sessionUuid;
    final qrToken = _currentQr?.qrToken;
    if (installationUuid == null || installationUuid.isEmpty || sessionUuid == null || sessionUuid.isEmpty || qrToken == null || qrToken.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.submitQrHit(
      sessionUuid: sessionUuid,
      qrToken: qrToken,
      installationUuid: installationUuid,
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _activeSession = response.data ?? _activeSession;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.success ? 'QR hit submitted to active session.' : (response.error ?? 'Failed to submit QR hit')),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _refreshExecutionState();
      await _loadPresenceDashboard();
    }
  }

  void _setAutoRefreshExecution(bool enabled) {
    _executionPollTimer?.cancel();
    if (!enabled) {
      setState(() {
        _autoRefreshExecution = false;
      });
      return;
    }

    setState(() {
      _autoRefreshExecution = true;
    });

    _executionPollTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!mounted || _isSubmittingAdminAction || _isLoading) {
        return;
      }
      _refreshExecutionState();
    });
  }

  Future<void> _copyQrToken() async {
    final qrData = _currentQr == null ? '' : _qrData(_currentQr!);
    if (qrData.isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: qrData));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('QR token copied.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Presence',
        showBackButton: true,
        showHomeButton: true,
        actions: [
          IconButton(
            onPressed: _isLoading ? null : _loadPresenceDashboard,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_summary == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 56, color: Colors.redAccent),
            const SizedBox(height: 12),
            Text(_error ?? 'Presence dashboard is unavailable'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadPresenceDashboard,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadPresenceDashboard,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Presence operations overview',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'This module consumes the presence backend directly for operator analytics and recent session visibility.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[400],
                ),
          ),
          const SizedBox(height: 20),
          _buildSummaryGrid(context),
          const SizedBox(height: 20),
          _buildExecutionSection(context),
          const SizedBox(height: 20),
          _buildAdminSection(context),
          const SizedBox(height: 20),
          _buildDistributionSection(
            context,
            title: 'Session Modes',
            subtitle: 'How presence flows are being requested across qr_only, camera_only, and qr_plus_camera.',
            buckets: _sessionModes,
          ),
          const SizedBox(height: 20),
          _buildDistributionSection(
            context,
            title: 'Grant Types',
            subtitle: 'Resulting assurance-oriented grants returned by the presence service.',
            buckets: _grantTypes,
          ),
          const SizedBox(height: 20),
          _buildRecentSessions(context),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(
              _error!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.orangeAccent,
                  ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSummaryGrid(BuildContext context) {
    final summary = _summary!;
    final cards = [
      _MetricCard(title: 'Total Sessions', value: summary.totalSessions.toString(), icon: Icons.how_to_reg),
      _MetricCard(title: 'Completed', value: summary.completedSessions.toString(), icon: Icons.verified),
      _MetricCard(title: 'Pending', value: summary.pendingSessions.toString(), icon: Icons.timelapse),
      _MetricCard(title: 'Granted', value: summary.grantedSessions.toString(), icon: Icons.check_circle),
      _MetricCard(title: 'Denied', value: summary.deniedSessions.toString(), icon: Icons.cancel),
    ];

    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: cards
          .map(
            (card) => SizedBox(
              width: 220,
              child: card,
            ),
          )
          .toList(),
    );
  }

  Widget _buildDistributionSection(
    BuildContext context, {
    required String title,
    required String subtitle,
    required List<PresenceAnalyticsBucket> buckets,
  }) {
    final total = buckets.fold<int>(0, (sum, item) => sum + item.count);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 16),
          if (buckets.isEmpty)
            Text(
              'No data available yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ...buckets.map((bucket) {
              final percent = total == 0 ? 0.0 : bucket.count / total;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(child: Text(bucket.label)),
                        Text('${bucket.count}'),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: LinearProgressIndicator(
                        value: percent,
                        minHeight: 10,
                        backgroundColor: Colors.white10,
                      ),
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildRecentSessions(BuildContext context) {
    final formatter = DateFormat('MMM d, HH:mm');

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recent Sessions',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            'Latest presence traces exposed by the backend for operator review.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 16),
          if (_recentSessions.isEmpty)
            Text(
              'No recent presence sessions found.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._recentSessions.map((session) {
              final createdAt = session.createdAt != null ? formatter.format(session.createdAt!) : 'Unknown';
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  onTap: () => _showSessionInspector(session),
                  title: Text(session.sessionUuid),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _TraceChip(label: session.sessionMode),
                        _TraceChip(label: session.assuranceLevel),
                        _TraceChip(label: session.grantType),
                        _TraceChip(label: 'QR ${session.qrStatus}'),
                        _TraceChip(label: session.status),
                      ],
                    ),
                  ),
                  trailing: Text(
                    createdAt,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildAdminSection(BuildContext context) {
    final installation = _installationContext;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Presence Settings',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Operator controls for reservation, default policy, and group bootstrapping.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
                    ),
                  ],
                ),
              ),
              if (_isSubmittingAdminAction)
                const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (installation != null) ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _TraceChip(label: installation.installationName),
                _TraceChip(label: 'Backend ${installation.detectionBackendMode}'),
                if (installation.reservedCameraUuid != null)
                  _TraceChip(label: 'Camera ${installation.reservedCameraUuid}'),
                if (installation.reservedCollectionUuid != null)
                  _TraceChip(label: 'Collection ${installation.reservedCollectionUuid}'),
              ],
            ),
            const SizedBox(height: 16),
          ],
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              ElevatedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : _showPolicyEditor,
                icon: const Icon(Icons.rule),
                label: const Text('Edit Policy'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : _showEnsureGroupDialog,
                icon: const Icon(Icons.group_add),
                label: const Text('Ensure Group'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : _resetReservations,
                icon: const Icon(Icons.restart_alt),
                label: const Text('Reset Reservations'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            'Available Cameras',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            'Reserving a camera also auto-binds its linked collection when the backend can resolve one.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 12),
          if (_cameras.isEmpty)
            Text(
              'No cameras available from the presence backend.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._cameras.map((camera) => Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    title: Text(camera.name.isEmpty ? camera.deviceId : camera.name),
                    subtitle: Text('${camera.cameraType} • ${camera.status}'),
                    trailing: camera.reservedForPresence
                        ? (camera.reservedResourceUuid != null && camera.reservedResourceUuid!.isNotEmpty
                            ? TextButton(
                                onPressed: _isSubmittingAdminAction ? null : () => _unreserveCamera(camera),
                                child: const Text('Unreserve'),
                              )
                            : const Text('Reserved'))
                        : TextButton(
                            onPressed: _isSubmittingAdminAction ? null : () => _reserveCamera(camera),
                            child: const Text('Reserve'),
                          ),
                  ),
                )),
          const SizedBox(height: 20),
          Text(
            'Presence Groups',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          if (_groups.isEmpty)
            Text(
              'No presence groups have been provisioned yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._groups.take(6).map((group) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(group.displayName),
                  subtitle: Text(group.userUuid == null ? group.groupUuid : '${group.userUuid} • ${group.groupUuid}'),
                  trailing: Text(group.status),
                )),
        ],
      ),
    );
  }

  Widget _buildExecutionSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Execution',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      widget.stationMode
                          ? 'Render a live station QR for another mobile or web client to scan during presence verification.'
                          : 'Start a presence session, fetch the current QR payload, and refresh live state from the frontend.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.stationMode
                          ? 'Station mode is intended to present the current live QR token for another device to scan.'
                          : _selectedExecutionMode == 'camera_only'
                              ? 'Camera Only uses the presence backend and a reserved platform camera. It does not open this browser device webcam.'
                              : 'QR-backed modes render the current token for the selected device reference below.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.orangeAccent),
                    ),
                  ],
                ),
              ),
              if (_isSubmittingAdminAction)
                const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 16),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'qr_only', label: Text('QR Only')),
              ButtonSegment(value: 'camera_only', label: Text('Camera Only')),
              ButtonSegment(value: 'qr_plus_camera', label: Text('QR + Camera')),
            ],
            selected: {_selectedExecutionMode},
            onSelectionChanged: widget.stationMode ? null : (selection) {
              setState(() {
                _selectedExecutionMode = selection.first;
              });
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _deviceReferenceController,
            decoration: const InputDecoration(
              labelText: 'Device Reference / Device UUID',
              border: OutlineInputBorder(),
              helperText: 'Use one stable device anchor per kiosk or test device to retrieve its latest QR-backed session.',
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _deviceDisplayNameController,
            decoration: const InputDecoration(
              labelText: 'Device Display Name',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _locationLabelController,
            decoration: const InputDecoration(
              labelText: 'Location Label',
              border: OutlineInputBorder(),
              helperText: 'Optional local label stored inside the QR payload.',
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _ownerDisplayNameController,
            decoration: const InputDecoration(
              labelText: 'Owner QR Display Name',
              border: OutlineInputBorder(),
              helperText: 'Optional display name used when rendering a user-owned QR.',
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              ElevatedButton.icon(
                onPressed: _isSubmittingAdminAction
                    ? null
                    : (widget.stationMode
                        ? () => _refreshExecutionState(renderIfMissing: true)
                        : _startExecutionSession),
                icon: Icon(widget.stationMode ? Icons.qr_code_2 : Icons.play_arrow),
                label: Text(widget.stationMode ? 'Render Station QR' : 'Start Session'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : () => _refreshExecutionState(),
                icon: const Icon(Icons.sync),
                label: Text(widget.stationMode ? 'Refresh QR' : 'Refresh State'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : _renderOwnerQr,
                icon: const Icon(Icons.badge),
                label: const Text('Render Owner QR'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction ? null : _openWebQrScanner,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Open Web Scanner'),
              ),
              OutlinedButton.icon(
                onPressed: widget.stationMode || _isSubmittingAdminAction || _selectedExecutionMode != 'qr_plus_camera'
                    ? null
                    : () => _openWebQrScanner(sessionMode: 'qr_plus_camera'),
                icon: const Icon(Icons.video_call),
                label: const Text('Scan QR + Camera'),
              ),
              OutlinedButton.icon(
                onPressed: _isSubmittingAdminAction || _currentQr?.qrToken == null ? null : _validateCurrentQr,
                icon: const Icon(Icons.verified_user),
                label: const Text('Validate QR'),
              ),
              OutlinedButton.icon(
                onPressed: widget.stationMode || _isSubmittingAdminAction || _selectedExecutionMode == 'camera_only' || _currentQr?.qrToken == null
                    ? null
                    : _submitTestQrHit,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Submit Test QR Hit'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('Auto-refresh execution state'),
            subtitle: Text(widget.stationMode
                ? 'Refresh the station QR and linked session state every 4 seconds.'
                : 'Poll current QR, session status, and result every 4 seconds while testing.'),
            value: _autoRefreshExecution,
            onChanged: _isSubmittingAdminAction ? null : _setAutoRefreshExecution,
          ),
          if (_activeSession != null) ...[
            const SizedBox(height: 16),
            Text(
              'Active Session',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _TraceChip(label: _activeSession!.sessionUuid),
                _TraceChip(label: _activeSession!.status),
                _TraceChip(label: _activeSession!.sessionMode),
                if ((_activeSession!.qrStatus ?? '').isNotEmpty) _TraceChip(label: 'QR ${_activeSession!.qrStatus}'),
                if ((_activeSession!.detectionStatus ?? '').isNotEmpty)
                  _TraceChip(label: 'Detection ${_activeSession!.detectionStatus}'),
              ],
            ),
          ],
          if (_currentQr != null && _selectedExecutionMode != 'camera_only') ...[
            const SizedBox(height: 16),
            Text(
              'Current QR Payload',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            if (_currentQr!.found) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Center(
                  child: QrImageView(
                    data: _qrData(_currentQr!),
                    version: QrVersions.auto,
                    size: 220,
                    backgroundColor: Colors.white,
                    eyeStyle: const QrEyeStyle(
                      eyeShape: QrEyeShape.square,
                      color: Colors.black,
                    ),
                    dataModuleStyle: const QrDataModuleStyle(
                      dataModuleShape: QrDataModuleShape.square,
                      color: Colors.black,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: SelectableText(_qrData(_currentQr!))),
                  IconButton(
                    onPressed: _copyQrToken,
                    tooltip: 'Copy QR data',
                    icon: const Icon(Icons.copy),
                  ),
                ],
              ),
              if (_currentQr!.expiresAt != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('Expires: ${_currentQr!.expiresAt}'),
                ),
              if (_currentQr!.payload != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: SelectableText(_currentQr!.payload.toString()),
                ),
              if (_qrValidation != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _TraceChip(label: _qrValidation!.valid ? 'QR Valid' : 'QR Invalid'),
                      if (_currentQr!.qrType != null) _TraceChip(label: _currentQr!.qrType!),
                      if (_qrValidation!.referenceSource != null) _TraceChip(label: _qrValidation!.referenceSource!),
                      if (_qrValidation!.sessionUuid != null) _TraceChip(label: 'Session ${_qrValidation!.sessionUuid}'),
                    ],
                  ),
                ),
              if (_installationContext != null && _installationContext!.installationReference.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: SelectableText(_installationContext!.installationReference.toString()),
                ),
            ] else
              Text(
                'No current QR payload found for this device reference.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
          ],
          if (_activeResult != null) ...[
            const SizedBox(height: 16),
            Text(
              'Live Result',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _TraceChip(label: _activeResult!.decision),
                _TraceChip(label: _activeResult!.grantType),
                _TraceChip(label: _activeResult!.reasonCode),
                if (_activeResult!.policySource != null) _TraceChip(label: _activeResult!.policySource!),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _PresenceSessionInspector extends StatefulWidget {
  final PresenceSessionTraceSummary session;
  final PresenceApiClient apiClient;

  const _PresenceSessionInspector({
    required this.session,
    required this.apiClient,
  });

  @override
  State<_PresenceSessionInspector> createState() => _PresenceSessionInspectorState();
}

class _PresenceSessionInspectorState extends State<_PresenceSessionInspector> {
  PresenceActionPlanDetails? _actionPlan;
  PresenceSessionTraceDetails? _trace;
  List<PresenceDecisionRecordDetails> _decisionHistory = const [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDetails();
  }

  Future<void> _loadDetails() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final results = await Future.wait([
      widget.apiClient.getActionPlan(widget.session.sessionUuid),
      widget.apiClient.getDecisionHistory(widget.session.sessionUuid),
      widget.apiClient.getSessionTrace(widget.session.sessionUuid),
    ]);

    final actionPlanResponse = results[0] as ApiResponse<PresenceActionPlanDetails>;
    final decisionResponse = results[1] as ApiResponse<List<PresenceDecisionRecordDetails>>;
    final traceResponse = results[2] as ApiResponse<PresenceSessionTraceDetails>;

    if (!mounted) {
      return;
    }

    setState(() {
      _actionPlan = actionPlanResponse.data;
      _decisionHistory = decisionResponse.data ?? const [];
      _trace = traceResponse.data;
      _error = actionPlanResponse.success || decisionResponse.success || traceResponse.success
          ? null
          : actionPlanResponse.error ?? decisionResponse.error ?? traceResponse.error;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.8,
        maxChildSize: 0.95,
        minChildSize: 0.5,
        builder: (context, scrollController) {
          return Material(
            color: AppColors.background,
            child: ListView(
              controller: scrollController,
              padding: const EdgeInsets.all(16),
              children: [
                Center(
                  child: Container(
                    width: 48,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Session Inspector',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(widget.session.sessionUuid, style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 16),
                if (_isLoading)
                  const Center(child: CircularProgressIndicator())
                else ...[
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(_error!, style: const TextStyle(color: Colors.orangeAccent)),
                    ),
                  _SessionOverviewCard(session: _trace?.session ?? PresenceSessionDetails(
                    sessionUuid: widget.session.sessionUuid,
                    status: widget.session.status,
                    sessionMode: widget.session.sessionMode,
                    assuranceLevel: widget.session.assuranceLevel,
                    grantType: widget.session.grantType,
                    decision: 'unknown',
                    qrStatus: widget.session.qrStatus,
                    detectionStatus: 'unknown',
                    matchedGroupUuid: null,
                    policySource: null,
                    triggerType: null,
                    actionType: null,
                    actionExecutionStatus: null,
                    resolvedCameraUuid: null,
                    resolvedCollectionUuid: null,
                    createdAt: widget.session.createdAt?.toIso8601String(),
                    externalAssets: null,
                  )),
                  const SizedBox(height: 16),
                  if (_actionPlan != null) _ActionPlanCard(actionPlan: _actionPlan!),
                  const SizedBox(height: 16),
                  _DecisionHistoryCard(items: _decisionHistory),
                  const SizedBox(height: 16),
                  if (_trace?.auditLog != null) _AuditLogCard(auditLog: _trace!.auditLog!),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SessionOverviewCard extends StatelessWidget {
  final PresenceSessionDetails session;

  const _SessionOverviewCard({required this.session});

  @override
  Widget build(BuildContext context) {
    return _InspectorCard(
      title: 'Session',
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          _TraceChip(label: session.sessionMode),
          _TraceChip(label: session.assuranceLevel),
          _TraceChip(label: session.grantType),
          _TraceChip(label: session.status),
          _TraceChip(label: session.decision),
          _TraceChip(label: 'QR ${session.qrStatus}'),
          _TraceChip(label: 'Detection ${session.detectionStatus}'),
          if (session.resolvedCameraUuid != null) _TraceChip(label: 'Camera ${session.resolvedCameraUuid}'),
          if (session.resolvedCollectionUuid != null) _TraceChip(label: 'Collection ${session.resolvedCollectionUuid}'),
        ],
      ),
    );
  }
}

class _ActionPlanCard extends StatelessWidget {
  final PresenceActionPlanDetails actionPlan;

  const _ActionPlanCard({required this.actionPlan});

  @override
  Widget build(BuildContext context) {
    return _InspectorCard(
      title: 'Action Plan',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InspectorRow(label: 'Policy Source', value: actionPlan.policySource),
          _InspectorRow(label: 'Trigger Type', value: actionPlan.triggerType),
          _InspectorRow(label: 'Action Type', value: actionPlan.actionType),
          _InspectorRow(label: 'Execution Status', value: actionPlan.actionExecutionStatus),
          _InspectorRow(label: 'Matched Group', value: actionPlan.matchedGroupUuid),
          if (actionPlan.externalAssets != null) ...[
            const SizedBox(height: 12),
            Text('External Assets', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            _InspectorRow(label: 'Group', value: actionPlan.externalAssets!.individualGroupId),
            _InspectorRow(label: 'Trigger', value: actionPlan.externalAssets!.triggerUuid),
            _InspectorRow(label: 'Action', value: actionPlan.externalAssets!.actionUuid),
          ],
          if (actionPlan.triggerObservation != null) ...[
            const SizedBox(height: 12),
            Text('Trigger Observation', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            _InspectorRow(label: 'Trigger UUID', value: actionPlan.triggerObservation!.triggerUuid),
            _InspectorRow(label: 'Configured Actions', value: actionPlan.triggerObservation!.configuredActionNames.join(', ')),
            _InspectorRow(label: 'Last Fired', value: actionPlan.triggerObservation!.lastFiredAt),
            _InspectorRow(label: 'Last Matched', value: actionPlan.triggerObservation!.lastMatchedAt),
          ],
        ],
      ),
    );
  }
}

class _DecisionHistoryCard extends StatelessWidget {
  final List<PresenceDecisionRecordDetails> items;

  const _DecisionHistoryCard({required this.items});

  @override
  Widget build(BuildContext context) {
    return _InspectorCard(
      title: 'Decision History',
      child: items.isEmpty
          ? Text('No decision history recorded.', style: Theme.of(context).textTheme.bodyMedium)
          : Column(
              children: items
                  .map(
                    (item) => ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      childrenPadding: const EdgeInsets.only(bottom: 12),
                      title: Text(item.decision),
                      subtitle: Text(item.reasonCode),
                      children: [
                        _InspectorRow(label: 'Policy Source', value: item.policySource),
                        _InspectorRow(label: 'Trigger Type', value: item.triggerType),
                        _InspectorRow(label: 'Action Type', value: item.actionType),
                        _InspectorRow(label: 'Execution Status', value: item.actionExecutionStatus),
                        _InspectorRow(label: 'Created At', value: item.createdAt),
                      ],
                    ),
                  )
                  .toList(),
            ),
    );
  }
}

class _AuditLogCard extends StatelessWidget {
  final PresenceAuditLogTrace auditLog;

  const _AuditLogCard({required this.auditLog});

  @override
  Widget build(BuildContext context) {
    return _InspectorCard(
      title: 'Audit Log',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InspectorRow(label: 'Found', value: auditLog.found.toString()),
          _InspectorRow(label: 'Log UUID', value: auditLog.logUuid),
          if (auditLog.error != null) _InspectorRow(label: 'Error', value: auditLog.error),
          if (auditLog.payload != null)
            Text(
              auditLog.payload.toString(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
        ],
      ),
    );
  }
}

class _InspectorCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _InspectorCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _InspectorRow extends StatelessWidget {
  final String label;
  final String? value;

  const _InspectorRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[400])),
          ),
          Expanded(
            child: Text(value == null || value!.isEmpty ? 'Not available' : value!),
          ),
        ],
      ),
    );
  }
}

class _PresencePolicyDialog extends StatefulWidget {
  final PresenceGroupPolicy initialPolicy;

  const _PresencePolicyDialog({required this.initialPolicy});

  @override
  State<_PresencePolicyDialog> createState() => _PresencePolicyDialogState();
}

class _PresencePolicyDialogState extends State<_PresencePolicyDialog> {
  late final TextEditingController _grantedTrigger;
  late final TextEditingController _grantedAction;
  late final TextEditingController _deniedTrigger;
  late final TextEditingController _deniedAction;
  late final TextEditingController _retryTrigger;
  late final TextEditingController _retryAction;
  late final TextEditingController _failedTrigger;
  late final TextEditingController _failedAction;

  @override
  void initState() {
    super.initState();
    _grantedTrigger = TextEditingController(text: widget.initialPolicy.granted?.triggerType ?? '');
    _grantedAction = TextEditingController(text: widget.initialPolicy.granted?.actionType ?? '');
    _deniedTrigger = TextEditingController(text: widget.initialPolicy.denied?.triggerType ?? '');
    _deniedAction = TextEditingController(text: widget.initialPolicy.denied?.actionType ?? '');
    _retryTrigger = TextEditingController(text: widget.initialPolicy.retryRequired?.triggerType ?? '');
    _retryAction = TextEditingController(text: widget.initialPolicy.retryRequired?.actionType ?? '');
    _failedTrigger = TextEditingController(text: widget.initialPolicy.failed?.triggerType ?? '');
    _failedAction = TextEditingController(text: widget.initialPolicy.failed?.actionType ?? '');
  }

  @override
  void dispose() {
    _grantedTrigger.dispose();
    _grantedAction.dispose();
    _deniedTrigger.dispose();
    _deniedAction.dispose();
    _retryTrigger.dispose();
    _retryAction.dispose();
    _failedTrigger.dispose();
    _failedAction.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit Installation Policy'),
      content: SizedBox(
        width: 560,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _PolicyRuleEditor(label: 'Granted', triggerController: _grantedTrigger, actionController: _grantedAction),
              _PolicyRuleEditor(label: 'Denied', triggerController: _deniedTrigger, actionController: _deniedAction),
              _PolicyRuleEditor(label: 'Retry Required', triggerController: _retryTrigger, actionController: _retryAction),
              _PolicyRuleEditor(label: 'Failed', triggerController: _failedTrigger, actionController: _failedAction),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.pop(
              context,
              PresenceGroupPolicy(
                granted: PresencePolicyRule(triggerType: _grantedTrigger.text.trim(), actionType: _grantedAction.text.trim()),
                denied: PresencePolicyRule(triggerType: _deniedTrigger.text.trim(), actionType: _deniedAction.text.trim()),
                retryRequired: PresencePolicyRule(triggerType: _retryTrigger.text.trim(), actionType: _retryAction.text.trim()),
                failed: PresencePolicyRule(triggerType: _failedTrigger.text.trim(), actionType: _failedAction.text.trim()),
              ),
            );
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _PolicyRuleEditor extends StatelessWidget {
  final String label;
  final TextEditingController triggerController;
  final TextEditingController actionController;

  const _PolicyRuleEditor({
    required this.label,
    required this.triggerController,
    required this.actionController,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          TextFormField(
            controller: triggerController,
            decoration: const InputDecoration(labelText: 'Trigger Type', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: actionController,
            decoration: const InputDecoration(labelText: 'Action Type', border: OutlineInputBorder()),
          ),
        ],
      ),
    );
  }
}

class _EnsurePresenceGroupDialog extends StatefulWidget {
  const _EnsurePresenceGroupDialog();

  @override
  State<_EnsurePresenceGroupDialog> createState() => _EnsurePresenceGroupDialogState();
}

class _PresenceQrScannerSheet extends StatefulWidget {
  const _PresenceQrScannerSheet();

  @override
  State<_PresenceQrScannerSheet> createState() => _PresenceQrScannerSheetState();
}

class _PresenceQrScannerSheetState extends State<_PresenceQrScannerSheet> {
  final TextEditingController _controller = TextEditingController();
  final MobileScannerController _scannerController = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );
  bool _hasDetectedCode = false;

  @override
  void dispose() {
    _scannerController.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _submitValue(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || _hasDetectedCode) {
      return;
    }
    _hasDetectedCode = true;
    Navigator.of(context).pop(trimmed);
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return SingleChildScrollView(
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, bottomInset + 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Web QR Scanner', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            const Text('Scan from the device camera when available, or paste scanned QR data manually. This accepts raw station tokens and full JSON payloads such as owner identity QR data.'),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                height: 280,
                child: MobileScanner(
                  controller: _scannerController,
                  onDetect: (capture) {
                    if (_hasDetectedCode) {
                      return;
                    }
                    for (final barcode in capture.barcodes) {
                      final value = barcode.rawValue;
                      if (value != null && value.trim().isNotEmpty) {
                        _submitValue(value);
                        return;
                      }
                    }
                  },
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              minLines: 4,
              maxLines: 10,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Manual QR Data',
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: () => _submitValue(_controller.text),
                  child: const Text('Submit'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _EnsurePresenceGroupDialogState extends State<_EnsurePresenceGroupDialog> {
  final _displayNameController = TextEditingController();
  final _userUuidController = TextEditingController();

  @override
  void dispose() {
    _displayNameController.dispose();
    _userUuidController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Ensure Presence Group'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _displayNameController,
              decoration: const InputDecoration(labelText: 'Display Name', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _userUuidController,
              decoration: const InputDecoration(
                labelText: 'User UUID',
                border: OutlineInputBorder(),
                helperText: 'Optional: leave blank to ensure an installation-level group.',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: () {
            final displayName = _displayNameController.text.trim();
            if (displayName.isEmpty) {
              return;
            }
            Navigator.pop(context, {
              'display_name': displayName,
              'user_uuid': _userUuidController.text.trim().isEmpty ? null : _userUuidController.text.trim(),
            });
          },
          child: const Text('Ensure'),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.secondary),
          const SizedBox(height: 12),
          Text(
            value,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(title, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _TraceChip extends StatelessWidget {
  final String label;

  const _TraceChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.secondary.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.secondary,
              fontWeight: FontWeight.w600,
            ),
      ),
    );
  }
}