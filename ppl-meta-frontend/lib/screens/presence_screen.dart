import 'dart:convert';
import 'dart:async';

import 'package:excel/excel.dart' hide Border;
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
import '../utils/platform_file_download.dart';
import '../widgets/custom_app_bar.dart';
import '../core/providers/camera_providers.dart';

class PresenceScreen extends ConsumerStatefulWidget {
  final bool stationMode;

  const PresenceScreen({super.key, this.stationMode = false});

  @override
  ConsumerState<PresenceScreen> createState() => _PresenceScreenState();
}

class _PresenceScreenState extends ConsumerState<PresenceScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  PresenceAnalyticsSummary? _summary;
  PresenceInstallationContext? _installationContext;
  List<PresenceAnalyticsBucket> _sessionModes = const [];
  List<PresenceAnalyticsBucket> _grantTypes = const [];
  List<PresenceSessionTraceSummary> _recentSessions = const [];
  PresenceSessionTracePage _sessionsPage = const PresenceSessionTracePage(
    items: <PresenceSessionTraceSummary>[],
    total: 0,
    returned: 0,
    limit: 20,
    offset: 0,
    hasMore: false,
  );
  PresenceUserDayAwardPage _userDayAwardPage = const PresenceUserDayAwardPage(
    items: <PresenceUserDayAwardSummary>[],
    total: 0,
    returned: 0,
    limit: 20,
    offset: 0,
    hasMore: false,
    availableUsers: <String>[],
  );
  List<PresenceCameraOption> _cameras = const [];
  List<PresenceIndividualGroupOption> _availableIndividualGroups = const [];
  PresenceLiveSession? _activeSession;
  PresenceQrPayload? _currentQr;
  PresenceResultDetails? _activeResult;
  bool _isLoading = true;
  bool _isSessionsLoading = false;
  bool _isUserDayAwardsLoading = false;
  bool _isDownloadingSessions = false;
  bool _isSubmittingAdminAction = false;
  String? _error;
  String? _sessionsError;
  String? _userDayAwardsError;
  bool _autoRefreshExecution = false;
  Timer? _executionPollTimer;
  final TextEditingController _deviceDisplayNameController = TextEditingController();
  final TextEditingController _locationLabelController = TextEditingController();
  final TextEditingController _sessionsUserQueryController = TextEditingController();
  final TextEditingController _userDayAwardUserController = TextEditingController();
  String? _lastTerminalAlertSessionKey;
  String? _lastGrantedAlertSessionKey;
  static const int _sessionsPageSize = 20;
  static const int _userDayAwardsPageSize = 20;
  late DateTime _sessionsStartDate;
  late DateTime _sessionsEndDate;
  late DateTime _userDayAwardsStartDate;
  late DateTime _userDayAwardsEndDate;
  String? _sessionsCameraUuid;
  String? _sessionsGrantType;
  String? _selectedUserDayAwardQuery;
  final Map<String, List<PresenceSessionTraceSummary>> _userDayAwardSessions = {};
  final Set<String> _loadingUserDayAwardRows = <String>{};
  final Set<String> _expandedUserDayAwardRows = <String>{};
  final Map<String, String> _userDayAwardRowFilters = <String, String>{};

  String get _deviceReference => widget.stationMode ? 'presence-web-station' : 'presence-web-console';

  PresenceIndividualGroupOption? get _activePresenceIndividualGroup {
    final installationContext = _installationContext;
    if (installationContext == null) {
      return null;
    }
    final activeGroupId = installationContext.activePresenceIndividualGroupId;
    if (activeGroupId != null && activeGroupId.isNotEmpty) {
      for (final group in _availableIndividualGroups) {
        if (group.individualGroupId == activeGroupId) {
          return group;
        }
      }
      return PresenceIndividualGroupOption(
        individualGroupId: activeGroupId,
        name: installationContext.activePresenceIndividualGroupName ?? 'presence',
        description: null,
        memberCount: 0,
      );
    }
    final activeGroupName = installationContext.activePresenceIndividualGroupName;
    if (activeGroupName != null && activeGroupName.isNotEmpty) {
      for (final group in _availableIndividualGroups) {
        if (group.name.toLowerCase() == activeGroupName.toLowerCase()) {
          return group;
        }
      }
    }
    return null;
  }

  List<PresenceIndividualGroupOption> get _presenceMatchGroups {
    final groups = List<PresenceIndividualGroupOption>.from(_availableIndividualGroups);
    final activeGroup = _activePresenceIndividualGroup;
    if (activeGroup != null &&
        groups.every((group) => group.individualGroupId != activeGroup.individualGroupId)) {
      groups.insert(0, activeGroup);
    }
    return groups;
  }

  PresenceApiClient get _apiClient => ref.read(presenceApiClientProvider);

  String? get _defaultUserDayAwardQuery {
    final currentUser = ref.read(currentUserProvider);
    final email = currentUser?.email?.trim();
    if (email != null && email.isNotEmpty) {
      return email;
    }
    final username = currentUser?.username?.trim();
    if (username != null && username.isNotEmpty) {
      return username;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    _sessionsEndDate = DateTime.now();
    _sessionsStartDate = _sessionsEndDate.subtract(const Duration(days: 3));
    _userDayAwardsEndDate = DateTime.now();
    _userDayAwardsStartDate = _userDayAwardsEndDate.subtract(const Duration(days: 3));
    _deviceDisplayNameController.text = widget.stationMode ? 'Presence Web Station' : 'Presence Web Console';
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadPresenceDashboard();
      _loadSessionsPage();
      if (widget.stationMode) {
        _refreshExecutionState(renderIfMissing: true);
      }
    });
  }

  @override
  void dispose() {
    _executionPollTimer?.cancel();
    _tabController.dispose();
    _deviceDisplayNameController.dispose();
    _locationLabelController.dispose();
    _sessionsUserQueryController.dispose();
    _userDayAwardUserController.dispose();
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
      _apiClient.getAvailableIndividualGroups(),
    ]);

    final summaryResponse = results[0] as ApiResponse<PresenceAnalyticsSummary>;
    final installationResponse = results[1] as ApiResponse<PresenceInstallationContext>;
    final modeResponse = results[2] as ApiResponse<List<PresenceAnalyticsBucket>>;
    final grantResponse = results[3] as ApiResponse<List<PresenceAnalyticsBucket>>;
    final traceResponse = results[4] as ApiResponse<List<PresenceSessionTraceSummary>>;
    final camerasResponse = results[5] as ApiResponse<List<PresenceCameraOption>>;
    final availableGroupsResponse = results[6] as ApiResponse<List<PresenceIndividualGroupOption>>;

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
      _availableIndividualGroups = availableGroupsResponse.data ?? const [];
      _error = installationResponse.success &&
              modeResponse.success &&
              grantResponse.success &&
              traceResponse.success &&
              camerasResponse.success &&
              availableGroupsResponse.success
          ? null
          : traceResponse.error ??
              modeResponse.error ??
              grantResponse.error ??
              installationResponse.error ??
              camerasResponse.error ??
              availableGroupsResponse.error;
      _isLoading = false;
    });

    unawaited(_loadSessionsPage());
    unawaited(_loadUserDayAwardPage(offset: 0));
  }

  Future<void> _loadUserDayAwardPage({int? offset}) async {
    if ((_selectedUserDayAwardQuery == null || _selectedUserDayAwardQuery!.trim().isEmpty)) {
      _selectedUserDayAwardQuery = _defaultUserDayAwardQuery;
      _userDayAwardUserController.text = _selectedUserDayAwardQuery ?? '';
    }

    setState(() {
      _isUserDayAwardsLoading = true;
      _userDayAwardsError = null;
    });

    final response = await _apiClient.getUserDayAwardSummaryPage(
      limit: _userDayAwardsPageSize,
      offset: offset ?? _userDayAwardPage.offset,
      userQuery: _selectedUserDayAwardQuery,
      startDate: DateTime(
        _userDayAwardsStartDate.year,
        _userDayAwardsStartDate.month,
        _userDayAwardsStartDate.day,
      ),
      endDate: DateTime(
        _userDayAwardsEndDate.year,
        _userDayAwardsEndDate.month,
        _userDayAwardsEndDate.day,
        23,
        59,
        59,
      ),
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isUserDayAwardsLoading = false;
      if (response.success && response.data != null) {
        _userDayAwardPage = response.data!;
        final activeRowKeys = _userDayAwardPage.items.map((item) => item.rowKey).toSet();
        _expandedUserDayAwardRows.removeWhere((rowKey) => !activeRowKeys.contains(rowKey));
        _userDayAwardRowFilters.removeWhere((rowKey, _) => !activeRowKeys.contains(rowKey));
      }
      _userDayAwardsError = response.success ? null : (response.error ?? 'Failed to load user-day awards');
    });
  }

  Future<void> _loadUserDayAwardSessions(PresenceUserDayAwardSummary summary) async {
    final rowKey = summary.rowKey;
    if (_loadingUserDayAwardRows.contains(rowKey) || _userDayAwardSessions.containsKey(rowKey)) {
      return;
    }

    setState(() {
      _loadingUserDayAwardRows.add(rowKey);
    });

    final sessions = <PresenceSessionTraceSummary>[];
    var offset = 0;
    const pageSize = 200;
    final startDate = DateTime(summary.date.year, summary.date.month, summary.date.day);
    final endDate = DateTime(summary.date.year, summary.date.month, summary.date.day, 23, 59, 59);
    final userQuery = summary.userEmail.isNotEmpty ? summary.userEmail : summary.userLabel;

    while (true) {
      final response = await _apiClient.getSessionTracePage(
        limit: pageSize,
        offset: offset,
        userQuery: userQuery,
        startDate: startDate,
        endDate: endDate,
      );

      if (!response.success || response.data == null) {
        break;
      }

      final page = response.data!;
      sessions.addAll(page.items.where((session) => session.decision == 'granted'));
      if (!page.hasMore || page.returned == 0) {
        break;
      }
      offset += page.returned;
    }

    if (!mounted) {
      return;
    }

    setState(() {
      _loadingUserDayAwardRows.remove(rowKey);
      _userDayAwardSessions[rowKey] = sessions;
    });
  }

  Future<void> _loadSessionsPage({int? offset}) async {
    setState(() {
      _isSessionsLoading = true;
      _sessionsError = null;
    });

    final response = await _apiClient.getSessionTracePage(
      limit: _sessionsPageSize,
      offset: offset ?? _sessionsPage.offset,
      userQuery: _sessionsUserQueryController.text.trim(),
      cameraUuid: _sessionsCameraUuid,
      grantType: _sessionsGrantType,
      startDate: DateTime(_sessionsStartDate.year, _sessionsStartDate.month, _sessionsStartDate.day),
      endDate: DateTime(_sessionsEndDate.year, _sessionsEndDate.month, _sessionsEndDate.day, 23, 59, 59),
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSessionsLoading = false;
      _sessionsPage = response.data ?? _sessionsPage;
      _sessionsError = response.success ? null : response.error ?? 'Failed to load sessions';
    });
  }

  Future<List<PresenceSessionTraceSummary>> _loadAllFilteredSessions() async {
    const exportPageSize = 200;
    final sessions = <PresenceSessionTraceSummary>[];
    var offset = 0;
    var total = 0;

    do {
      final response = await _apiClient.getSessionTracePage(
        limit: exportPageSize,
        offset: offset,
        userQuery: _sessionsUserQueryController.text.trim(),
        cameraUuid: _sessionsCameraUuid,
        grantType: _sessionsGrantType,
        startDate: DateTime(_sessionsStartDate.year, _sessionsStartDate.month, _sessionsStartDate.day),
        endDate: DateTime(_sessionsEndDate.year, _sessionsEndDate.month, _sessionsEndDate.day, 23, 59, 59),
      );

      if (!response.success || response.data == null) {
        throw Exception(response.error ?? 'Failed to load filtered sessions');
      }

      final page = response.data!;
      sessions.addAll(page.items);
      total = page.total;
      offset += page.returned;

      if (page.returned == 0) {
        break;
      }
    } while (offset < total);

    return sessions;
  }

  Future<void> _downloadSessionsWorkbook() async {
    if (_isDownloadingSessions) {
      return;
    }

    setState(() {
      _isDownloadingSessions = true;
      _sessionsError = null;
    });

    try {
      final sessions = await _loadAllFilteredSessions();
      final workbook = Excel.createExcel();
      final sheet = workbook['Sessions'];
      final timestampFormat = DateFormat('yyyy-MM-dd HH:mm:ss');
      final rows = <List<CellValue>>[
        [
          TextCellValue('Session UUID'),
          TextCellValue('Created At'),
          TextCellValue('Completed At'),
          TextCellValue('Status'),
          TextCellValue('Decision'),
          TextCellValue('Grant Type'),
          TextCellValue('Session Mode'),
          TextCellValue('Assurance Level'),
          TextCellValue('QR Status'),
          TextCellValue('Actor'),
          TextCellValue('Actor Email'),
          TextCellValue('Interaction'),
          TextCellValue('Source'),
          TextCellValue('Camera'),
          TextCellValue('Reason Code'),
          TextCellValue('Headline'),
          TextCellValue('Subtitle'),
        ],
      ];

      for (final session in sessions) {
        rows.add([
          TextCellValue(session.sessionUuid),
          TextCellValue(session.createdAt != null ? timestampFormat.format(session.createdAt!) : ''),
          TextCellValue(session.completedAt != null ? timestampFormat.format(session.completedAt!) : ''),
          TextCellValue(session.status),
          TextCellValue(session.decision),
          TextCellValue(session.grantType),
          TextCellValue(session.sessionMode),
          TextCellValue(session.assuranceLevel),
          TextCellValue(session.qrStatus),
          TextCellValue(session.actorLabel ?? ''),
          TextCellValue(session.actorEmail ?? ''),
          TextCellValue(session.interactionLabel ?? ''),
          TextCellValue(session.sourceLabel ?? ''),
          TextCellValue(session.cameraLabel ?? ''),
          TextCellValue(session.reasonCode ?? ''),
          TextCellValue(session.headline ?? ''),
          TextCellValue(session.subtitle ?? ''),
        ]);
      }

      for (final row in rows) {
        sheet.appendRow(row);
      }

      for (var column = 0; column < rows.first.length; column++) {
        sheet.setColumnAutoFit(column);
      }

      final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
      final filename = 'presence_sessions_$timestamp.xlsx';
      final bytes = workbook.encode();
      if (bytes == null) {
        throw Exception('Failed to generate workbook');
      }
      final savedPath = await downloadFileBytes(
        bytes: bytes,
        filename: filename,
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Downloaded ${sessions.length} sessions to ${savedPath ?? filename}'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _sessionsError = 'Failed to download sessions: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_sessionsError!),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isDownloadingSessions = false;
        });
      }
    }
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

  Future<void> _reservePresenceMatchGroup(PresenceIndividualGroupOption group) async {
    final installationUuid = _installationContext?.installationUuid;
    if (installationUuid == null || installationUuid.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.updateActivePresenceGroup(
      installationUuid: installationUuid,
      individualGroupId: group.individualGroupId,
      groupName: group.name,
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
              ? 'Reserved match group ${group.name} for presence.'
              : (response.error ?? 'Failed to reserve match group'),
        ),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      await _loadPresenceDashboard();
    }
  }

  Future<void> _unreservePresenceMatchGroup(PresenceIndividualGroupOption group) async {
    final installationUuid = _installationContext?.installationUuid;
    if (installationUuid == null || installationUuid.isEmpty) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.updateActivePresenceGroup(
      installationUuid: installationUuid,
      clearActiveGroup: true,
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
              ? 'Released match group ${group.name} from presence.'
              : (response.error ?? 'Failed to unreserve match group'),
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
          cameras: _cameras,
        );
      },
    );
  }

  Future<PresenceLiveSession?> _ensureExecutionSession({
    String? sessionMode,
    bool enableAutoRefresh = false,
    bool refreshAfterStart = false,
  }) async {
    final mode = sessionMode ?? (widget.stationMode ? 'qr_plus_camera' : 'qr_only');
    final installationUuid = _installationContext?.installationUuid;
    final currentUser = ref.read(currentUserProvider);
    final deviceReference = _deviceReference;
    if (installationUuid == null || installationUuid.isEmpty || deviceReference.isEmpty) {
      return null;
    }

    final activeSession = _activeSession;
  final sessionIsReusable = activeSession != null &&
    activeSession.sessionUuid.isNotEmpty &&
    activeSession.sessionMode == mode &&
    !_isTerminalSession(activeSession);
  final hasMatchingSession = sessionIsReusable;
    if (hasMatchingSession) {
      return activeSession;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.createSession(
      sessionMode: mode,
      deviceUuid: deviceReference,
      deviceName: currentUser?.username ?? 'presence-web-operator',
      devicePlatform: 'web',
      appVersion: 'presence-web-console',
    );

    if (!mounted) {
      return response.data;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _activeSession = response.data;
      _activeResult = null;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.success ? 'Presence session started.' : (response.error ?? 'Failed to start session')),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );

    if (response.success) {
      if (enableAutoRefresh) {
        _setAutoRefreshExecution(true);
      }
      if (refreshAfterStart) {
        await _refreshExecutionState(renderIfMissing: true);
      }
      await _loadPresenceDashboard();
      return response.data;
    }

    return null;
  }

  bool _isTerminalSession(PresenceLiveSession session) {
    final status = session.status.toLowerCase();
    final decision = (session.decision ?? '').toLowerCase();
    return status == 'completed' ||
        status == 'failed' ||
        decision == 'granted' ||
        decision == 'denied' ||
        decision == 'failed';
  }

  String _qrData(PresenceQrPayload payload) {
    if (payload.payload != null) {
      return jsonEncode(payload.payload);
    }
    return payload.qrToken ?? '';
  }

  Future<void> _renderPresenceQr() async {
    final installationUuid = _installationContext?.installationUuid;
    final deviceReference = _deviceReference;
    if (installationUuid == null || installationUuid.isEmpty || deviceReference.isEmpty) {
      return;
    }

    final session = await _ensureExecutionSession(sessionMode: 'qr_only');
    if (session == null || !mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = true;
    });

    final response = await _apiClient.renderQr(
      installationUuid: installationUuid,
      deviceReference: deviceReference,
      deviceDisplayName: _deviceDisplayNameController.text.trim().isEmpty ? null : _deviceDisplayNameController.text.trim(),
      location: _locationLabelController.text.trim().isEmpty ? null : {'label': _locationLabelController.text.trim()},
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSubmittingAdminAction = false;
      _currentQr = response.data;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.success ? 'Presence QR rendered.' : (response.error ?? 'Failed to render QR')),
        backgroundColor: response.success ? null : Colors.red,
      ),
    );
  }

  Future<void> _startCameraOnlyMatch() async {
    final session = await _ensureExecutionSession(
      sessionMode: 'camera_only',
      enableAutoRefresh: true,
    );
    if (session == null || !mounted) {
      return;
    }

    setState(() {
      _currentQr = null;
    });

    await _refreshExecutionState();
  }

  Future<void> _openOwnerQrScanner() async {
    final session = await _ensureExecutionSession(sessionMode: 'qr_only');
    if (session == null || !mounted) {
      return;
    }

    final scannedText = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _PresenceQrScannerSheet(),
    );
    if (scannedText == null || scannedText.trim().isEmpty) {
      return;
    }
    await _consumeScannedQr(scannedText.trim(), sessionMode: 'qr_only', requireOwnerQr: true);
  }

  Future<void> _openOwnerQrVideoScanner() async {
    final session = await _ensureExecutionSession(sessionMode: 'qr_plus_camera');
    if (session == null || !mounted) {
      return;
    }

    final scannedText = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _PresenceQrScannerSheet(),
    );
    if (scannedText == null || scannedText.trim().isEmpty) {
      return;
    }
    await _consumeScannedQr(scannedText.trim(), sessionMode: 'qr_plus_camera', requireOwnerQr: true);
  }

  Future<void> _consumeScannedQr(
    String rawValue, {
    String sessionMode = 'qr_only',
    bool requireOwnerQr = false,
  }) async {
    final installationUuid = _installationContext?.installationUuid;
    final deviceReference = _deviceReference;
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

    final activeSession = await _ensureExecutionSession(sessionMode: sessionMode);
    if (activeSession == null) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isSubmittingAdminAction = false;
      });
      return;
    }

    ApiResponse<PresenceLiveSession> response;
    final isOwnerQrPayload = payload != null && payload['qr_type'] == 'owner_identity';
    if (requireOwnerQr && !isOwnerQrPayload) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isSubmittingAdminAction = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Scan the owner QR from the mobile app for this action.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (isOwnerQrPayload) {
      response = await _apiClient.submitOwnerQrHit(
        sessionUuid: activeSession.sessionUuid,
        qrPayload: payload,
        installationUuid: installationUuid,
      );
    } else {
      final qrToken = payload != null && payload['qr_token'] != null ? payload['qr_token'].toString() : rawValue;
      response = await _apiClient.submitQrHit(
        sessionUuid: activeSession.sessionUuid,
        qrToken: qrToken,
        installationUuid: installationUuid,
        qrPayload: payload,
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
                  : requireOwnerQr
                    ? 'Owner QR submitted.'
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
    final deviceReference = _deviceReference;
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
    final activeSessionMode = _activeSession?.sessionMode ?? (widget.stationMode ? 'qr_plus_camera' : 'qr_only');
    if (renderIfMissing && qrResponse.success && !(qrResponse.data?.found ?? false) && activeSessionMode != 'camera_only') {
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

    if (_autoRefreshExecution && _hasTerminalExecutionState()) {
      _setAutoRefreshExecution(false);
    }

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

  bool _hasTerminalExecutionState() {
    final session = _activeSession;
    final result = _activeResult;
    final sessionStatus = session?.status ?? '';
    final sessionDecision = session?.decision ?? '';
    final resultStatus = result?.status ?? '';
    final resultDecision = result?.decision ?? '';

    return sessionStatus == 'completed' ||
        sessionStatus == 'failed' ||
        sessionDecision == 'granted' ||
        sessionDecision == 'denied' ||
        sessionDecision == 'failed' ||
        resultStatus == 'completed' ||
        resultDecision == 'granted' ||
        resultDecision == 'denied' ||
        resultDecision == 'failed';
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
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight + kTextTabBarHeight),
        child: CustomAppBar(
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

    return Column(
      children: [
        Container(
          color: AppColors.surface,
          child: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(icon: Icon(Icons.dashboard_outlined), text: 'Overview'),
              Tab(icon: Icon(Icons.play_circle_outline), text: 'Actions'),
              Tab(icon: Icon(Icons.analytics_outlined), text: 'Analytics'),
              Tab(icon: Icon(Icons.list_alt_outlined), text: 'Sessions'),
              Tab(icon: Icon(Icons.settings_outlined), text: 'Settings'),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildOverviewTab(context),
              _buildActionsTab(context),
              _buildAnalyticsTab(context),
              _buildSessionsTab(context),
              _buildSettingsTab(context),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTabbedList(List<Widget> children) {
    return RefreshIndicator(
      onRefresh: _loadPresenceDashboard,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ...children,
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

  Widget _buildOverviewTab(BuildContext context) {
    return _buildTabbedList([
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
      _buildRecentSessions(context),
    ]);
  }

  Widget _buildActionsTab(BuildContext context) {
    return _buildTabbedList([
      _buildExecutionSection(context),
    ]);
  }

  Widget _buildAnalyticsTab(BuildContext context) {
    return _buildTabbedList([
      _buildUserDayAwardsHierarchySection(context),
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
    ]);
  }

  Widget _buildUserDayAwardsHierarchySection(BuildContext context) {
    final availableUsers = _userDayAwardPage.availableUsers.toSet().toList()..sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    final selectedUser = _selectedUserDayAwardQuery ?? '';
    if (selectedUser.isNotEmpty && !availableUsers.contains(selectedUser)) {
      availableUsers.insert(0, selectedUser);
    }

    final pageStart = _userDayAwardPage.total == 0 ? 0 : _userDayAwardPage.offset + 1;
    final pageEnd = _userDayAwardPage.offset + _userDayAwardPage.returned;

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
            'User-Day Presence Awards',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            'Daily per-user award totals with first/last award timestamps. Expand a row to see award sessions.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SizedBox(
                width: 360,
                child: Autocomplete<String>(
                  initialValue: TextEditingValue(text: _userDayAwardUserController.text),
                  optionsBuilder: (textEditingValue) {
                    final query = textEditingValue.text.trim().toLowerCase();
                    if (query.isEmpty) {
                      return availableUsers;
                    }
                    return availableUsers.where((user) => user.toLowerCase().contains(query));
                  },
                  onSelected: (selection) {
                    _userDayAwardUserController.text = selection;
                    _selectedUserDayAwardQuery = selection;
                    _userDayAwardSessions.clear();
                    _loadUserDayAwardPage(offset: 0);
                  },
                  fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
                    controller.value = TextEditingValue(
                      text: _userDayAwardUserController.text,
                      selection: TextSelection.collapsed(offset: _userDayAwardUserController.text.length),
                    );
                    return TextField(
                      controller: controller,
                      focusNode: focusNode,
                      decoration: const InputDecoration(
                        labelText: 'User',
                        hintText: 'Search users',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (value) {
                        _userDayAwardUserController.text = value.trim();
                        _selectedUserDayAwardQuery = value.trim().isEmpty ? _defaultUserDayAwardQuery : value.trim();
                        _userDayAwardSessions.clear();
                        _loadUserDayAwardPage(offset: 0);
                      },
                    );
                  },
                ),
              ),
              FilledButton.icon(
                onPressed: _isUserDayAwardsLoading
                    ? null
                    : () {
                        _selectedUserDayAwardQuery = _userDayAwardUserController.text.trim().isEmpty
                            ? _defaultUserDayAwardQuery
                            : _userDayAwardUserController.text.trim();
                        _userDayAwardSessions.clear();
                        _loadUserDayAwardPage(offset: 0);
                      },
                icon: const Icon(Icons.filter_alt_outlined),
                label: const Text('Apply'),
              ),
              _buildDateFilterButton(
                context,
                label: 'Start',
                value: _userDayAwardsStartDate,
                onPicked: (value) {
                  setState(() {
                    _userDayAwardsStartDate = value;
                    if (_userDayAwardsEndDate.isBefore(value)) {
                      _userDayAwardsEndDate = value;
                    }
                  });
                  _userDayAwardSessions.clear();
                  _loadUserDayAwardPage(offset: 0);
                },
              ),
              _buildDateFilterButton(
                context,
                label: 'End',
                value: _userDayAwardsEndDate,
                onPicked: (value) {
                  setState(() {
                    _userDayAwardsEndDate = value;
                    if (_userDayAwardsStartDate.isAfter(value)) {
                      _userDayAwardsStartDate = value;
                    }
                  });
                  _userDayAwardSessions.clear();
                  _loadUserDayAwardPage(offset: 0);
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Showing $pageStart-$pageEnd of ${_userDayAwardPage.total} user-day rows.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 12),
          if (_isUserDayAwardsLoading && _userDayAwardPage.items.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_userDayAwardPage.items.isEmpty)
            Text(
              'No award activity found for the selected user filter.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._userDayAwardPage.items.map((summary) {
              final rowKey = summary.rowKey;
              final isExpanded = _expandedUserDayAwardRows.contains(rowKey);
              final activeFilter = _userDayAwardRowFilters[rowKey] ?? 'ALL';
              final firstAward = summary.firstAwardAt != null ? DateFormat('HH:mm:ss').format(summary.firstAwardAt!) : '-';
              final lastAward = summary.lastAwardAt != null ? DateFormat('HH:mm:ss').format(summary.lastAwardAt!) : '-';
              final dateLabel = '${DateFormat('yyyy-MM-dd').format(summary.date)} ${DateFormat('EEE').format(summary.date).toUpperCase()}';
              const chipOrder = ['QR', 'Cam', 'Cam & QR'];
              final sortedGrantEntries = summary.grantTypeTotals.entries.toList()
                ..sort((a, b) {
                  final leftLabel = _userDayGrantLabel(a.key);
                  final rightLabel = _userDayGrantLabel(b.key);
                  final leftIndex = chipOrder.indexOf(leftLabel);
                  final rightIndex = chipOrder.indexOf(rightLabel);
                  final leftRank = leftIndex >= 0 ? leftIndex : 999;
                  final rightRank = rightIndex >= 0 ? rightIndex : 999;
                  if (leftRank != rightRank) {
                    return leftRank.compareTo(rightRank);
                  }
                  return leftLabel.compareTo(rightLabel);
                });

              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ExpansionTile(
                  key: ValueKey('user_day_$rowKey\_$isExpanded\_$activeFilter'),
                  initiallyExpanded: isExpanded,
                  onExpansionChanged: (expanded) {
                    setState(() {
                      if (expanded) {
                        _expandedUserDayAwardRows.add(rowKey);
                      } else {
                        _expandedUserDayAwardRows.remove(rowKey);
                        _userDayAwardRowFilters.remove(rowKey);
                      }
                    });
                    if (expanded) {
                      _loadUserDayAwardSessions(summary);
                    }
                  },
                  title: Text('${summary.identity} • $dateLabel'),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ...sortedGrantEntries.map(
                          (entry) => _buildUserDayGrantFilterChip(
                            context,
                            rowKey: rowKey,
                            label: _userDayGrantLabel(entry.key),
                            count: entry.value,
                            isActive: activeFilter == _userDayGrantLabel(entry.key),
                          ),
                        ),
                        _buildQrToCamTransitionChip(
                          context,
                          count: summary.qrToCamTransitionCount,
                          windowMinutes: summary.qrToCamTransitionWindowMinutes,
                          isActive: activeFilter == 'QR_TO_CAM',
                          onTap: () {
                            setState(() {
                              _expandedUserDayAwardRows.add(rowKey);
                              if (activeFilter == 'QR_TO_CAM') {
                                _userDayAwardRowFilters.remove(rowKey);
                              } else {
                                _userDayAwardRowFilters[rowKey] = 'QR_TO_CAM';
                              }
                            });
                            _loadUserDayAwardSessions(summary);
                          },
                        ),
                        _TraceChip(label: 'Total ${summary.totalAwards}'),
                        if (firstAward != '-' || lastAward != '-')
                          _TraceChip(label: '$firstAward – $lastAward'),
                      ],
                    ),
                  ),
                  childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                  children: [
                    if (_loadingUserDayAwardRows.contains(rowKey))
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: CircularProgressIndicator(),
                      )
                    else if ((_userDayAwardSessions[rowKey] ?? const []).isEmpty)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 8),
                        child: Text('No award sessions found for this row.'),
                      )
                    else
                      ..._buildSessionCards(
                        context,
                        _sessionsForUserDayRow(summary, filter: activeFilter),
                      ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton.icon(
                onPressed: _userDayAwardPage.offset <= 0 || _isUserDayAwardsLoading
                    ? null
                    : () => _loadUserDayAwardPage(
                          offset: (_userDayAwardPage.offset - _userDayAwardsPageSize).clamp(0, _userDayAwardPage.offset),
                        ),
                icon: const Icon(Icons.chevron_left),
                label: const Text('Previous'),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: !_userDayAwardPage.hasMore || _isUserDayAwardsLoading
                    ? null
                    : () => _loadUserDayAwardPage(offset: _userDayAwardPage.offset + _userDayAwardsPageSize),
                icon: const Icon(Icons.chevron_right),
                label: const Text('Next'),
              ),
            ],
          ),
          if (_userDayAwardsError != null) ...[
            const SizedBox(height: 12),
            Text(
              _userDayAwardsError!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.orangeAccent),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSettingsTab(BuildContext context) {
    return _buildTabbedList([
      _buildAdminSection(context),
    ]);
  }

  Widget _buildSessionsTab(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        await _loadPresenceDashboard();
        await _loadSessionsPage(offset: 0);
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Sessions',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'All presence sessions with server-side pagination and filtering.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 20),
          _buildSessionsFilters(context),
          const SizedBox(height: 20),
          _buildSessionsResults(context),
          if (_sessionsError != null) ...[
            const SizedBox(height: 16),
            Text(
              _sessionsError!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.orangeAccent),
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
    return _buildSessionListPanel(
      context,
      title: 'Recent Sessions',
      subtitle: 'Latest presence interactions rendered as operator-readable logs.',
      sessions: _recentSessions,
      emptyMessage: 'No recent presence sessions found.',
    );
  }

  Widget _buildSessionListPanel(
    BuildContext context, {
    required String title,
    required String subtitle,
    required List<PresenceSessionTraceSummary> sessions,
    required String emptyMessage,
    Widget? footer,
  }) {
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
          if (sessions.isEmpty)
            Text(
              emptyMessage,
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._buildSessionCards(context, sessions),
          if (footer != null) ...[
            const SizedBox(height: 16),
            footer,
          ],
        ],
      ),
    );
  }

  List<Widget> _buildSessionCards(BuildContext context, List<PresenceSessionTraceSummary> sessions) {
    final formatter = DateFormat('MMM d, HH:mm');
    return sessions.map((session) {
      final createdAt = session.createdAt != null ? formatter.format(session.createdAt!) : 'Unknown';
      final headline = session.headline ?? _fallbackSessionHeadline(session);
      final statusColor = _statusColorForSession(session, Theme.of(context).colorScheme);
      final metadata = <String>[
        createdAt,
        if (session.actorEmail != null && session.actorEmail!.isNotEmpty) session.actorEmail!,
        if (session.subtitle != null && session.subtitle!.isNotEmpty) session.subtitle!,
      ];
      return Card(
        margin: const EdgeInsets.only(bottom: 12),
        color: statusColor.withValues(alpha: 0.10),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: statusColor.withValues(alpha: 0.45)),
        ),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          onTap: () => _showSessionInspector(session),
          leading: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              _interactionIconForSession(session),
              color: statusColor,
              size: 22,
            ),
          ),
          title: Text(headline),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  metadata.join(' • '),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _TraceChip(
                      label: _statusLabelForSession(session),
                      backgroundColor: statusColor.withValues(alpha: 0.18),
                      foregroundColor: statusColor,
                    ),
                    _TraceChip(label: _interactionLabelForSession(session)),
                    if (session.cameraLabel != null && session.cameraLabel!.isNotEmpty)
                      _TraceChip(label: session.cameraLabel!),
                  ],
                ),
              ],
            ),
          ),
          trailing: const Icon(Icons.chevron_right),
        ),
      );
    }).toList();
  }

  Widget _buildSessionsFilters(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)),
      ),
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 240,
            child: TextField(
              controller: _sessionsUserQueryController,
              decoration: const InputDecoration(
                labelText: 'User',
                hintText: 'Email, username, or id',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.search),
              ),
              onSubmitted: (_) => _loadSessionsPage(offset: 0),
            ),
          ),
          SizedBox(
            width: 220,
            child: DropdownButtonFormField<String?>(
              isExpanded: true,
              value: _sessionsCameraUuid,
              decoration: const InputDecoration(
                labelText: 'Camera',
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('All cameras')),
                ..._cameras.map(
                  (camera) => DropdownMenuItem<String?>(value: camera.deviceId, child: Text(camera.name)),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _sessionsCameraUuid = value;
                });
                _loadSessionsPage(offset: 0);
              },
            ),
          ),
          SizedBox(
            width: 220,
            child: DropdownButtonFormField<String?>(
              isExpanded: true,
              value: _sessionsGrantType,
              decoration: const InputDecoration(
                labelText: 'Grant type',
                border: OutlineInputBorder(),
              ),
              items: [
                const DropdownMenuItem<String?>(value: null, child: Text('All grant types')),
                ..._grantTypes.map(
                  (grant) => DropdownMenuItem<String?>(value: grant.key, child: Text(grant.label)),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _sessionsGrantType = value;
                });
                _loadSessionsPage(offset: 0);
              },
            ),
          ),
          _buildDateFilterButton(
            context,
            label: 'Start',
            value: _sessionsStartDate,
            onPicked: (value) {
              setState(() {
                _sessionsStartDate = value;
                if (_sessionsEndDate.isBefore(value)) {
                  _sessionsEndDate = value;
                }
              });
              _loadSessionsPage(offset: 0);
            },
          ),
          _buildDateFilterButton(
            context,
            label: 'End',
            value: _sessionsEndDate,
            onPicked: (value) {
              setState(() {
                _sessionsEndDate = value;
                if (_sessionsStartDate.isAfter(value)) {
                  _sessionsStartDate = value;
                }
              });
              _loadSessionsPage(offset: 0);
            },
          ),
          FilledButton.icon(
            onPressed: () => _loadSessionsPage(offset: 0),
            icon: const Icon(Icons.filter_alt_outlined),
            label: const Text('Apply'),
          ),
          OutlinedButton.icon(
            onPressed: _isDownloadingSessions || _isSessionsLoading ? null : _downloadSessionsWorkbook,
            icon: _isDownloadingSessions
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.download_outlined),
            label: Text(_isDownloadingSessions ? 'Downloading...' : 'Download Excel'),
          ),
        ],
      ),
    );
  }

  Widget _buildDateFilterButton(
    BuildContext context, {
    required String label,
    required DateTime value,
    required ValueChanged<DateTime> onPicked,
  }) {
    return OutlinedButton.icon(
      onPressed: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: value,
          firstDate: DateTime.now().subtract(const Duration(days: 365)),
          lastDate: DateTime.now().add(const Duration(days: 30)),
        );
        if (picked != null) {
          onPicked(picked);
        }
      },
      icon: const Icon(Icons.event_outlined),
      label: Text('$label: ${DateFormat('MMM d, y').format(value)}'),
    );
  }

  Widget _buildSessionsResults(BuildContext context) {
    if (_isSessionsLoading && _sessionsPage.items.isEmpty) {
      return const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()));
    }
    final pageStart = _sessionsPage.total == 0 ? 0 : _sessionsPage.offset + 1;
    final pageEnd = _sessionsPage.offset + _sessionsPage.returned;
    return _buildSessionListPanel(
      context,
      title: 'All Sessions',
      subtitle: 'Showing $pageStart-$pageEnd of ${_sessionsPage.total} sessions.',
      sessions: _sessionsPage.items,
      emptyMessage: 'No sessions matched the current filters.',
      footer: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Page size $_sessionsPageSize',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[400]),
          ),
          Wrap(
            spacing: 12,
            children: [
              OutlinedButton.icon(
                onPressed: _sessionsPage.offset <= 0 || _isSessionsLoading
                    ? null
                    : () => _loadSessionsPage(offset: (_sessionsPage.offset - _sessionsPageSize).clamp(0, _sessionsPage.offset)),
                icon: const Icon(Icons.chevron_left),
                label: const Text('Previous'),
              ),
              FilledButton.icon(
                onPressed: !_sessionsPage.hasMore || _isSessionsLoading
                    ? null
                    : () => _loadSessionsPage(offset: _sessionsPage.offset + _sessionsPageSize),
                icon: const Icon(Icons.chevron_right),
                label: const Text('Next'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _fallbackSessionHeadline(PresenceSessionTraceSummary session) {
    final actor = session.actorLabel ?? session.actorEmail ?? 'unknown user';
    final interaction = _interactionLabelForSession(session).toLowerCase();
    final status = _statusLabelForSession(session).toLowerCase();
    return '$interaction for $actor is $status.';
  }

  String _statusLabelForSession(PresenceSessionTraceSummary session) {
    if (session.decision == 'granted') {
      return 'Granted';
    }
    if (session.decision == 'denied') {
      return 'Denied';
    }
    if (session.decision == 'failed' || session.status == 'failed') {
      return 'Failed';
    }
    if (session.decision == 'retry_required') {
      return 'Retry Required';
    }
    return 'Pending';
  }

  String _userDayGrantLabel(String rawGrantType) {
    final normalized = rawGrantType.trim().toLowerCase();
    if (normalized == 'verified_presence' || normalized == 'presence_verified_match') {
      return 'Cam & QR';
    }
    if (normalized == 'presence_match') {
      return 'Cam';
    }
    if (normalized == 'check_in' || normalized == 'presence_check_in') {
      return 'QR';
    }
    return rawGrantType;
  }

  Widget _buildQrToCamTransitionChip(
    BuildContext context, {
    required int count,
    required int windowMinutes,
    required VoidCallback onTap,
    bool isActive = false,
  }) {
    final backgroundColor = isActive
        ? Colors.green.withValues(alpha: 0.30)
        : Colors.green.withValues(alpha: 0.16);
    final foregroundColor = Colors.lightGreenAccent.shade100;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(999),
        border: isActive ? Border.all(color: Colors.lightGreenAccent.shade100.withValues(alpha: 0.5)) : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'QR',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: foregroundColor,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(width: 4),
          Icon(Icons.arrow_forward, size: 14, color: foregroundColor),
          const SizedBox(width: 4),
          Text(
            'Cam',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: foregroundColor,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(width: 8),
          Text(
            '$count',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: foregroundColor,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(width: 6),
          Text(
            '($windowMinutes m)',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: foregroundColor.withValues(alpha: 0.9),
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
      ),
    );
  }

  Widget _buildUserDayGrantFilterChip(
    BuildContext context, {
    required String rowKey,
    required String label,
    required int count,
    required bool isActive,
  }) {
    return InkWell(
      onTap: () {
        setState(() {
          _expandedUserDayAwardRows.add(rowKey);
          if (isActive) {
            _userDayAwardRowFilters.remove(rowKey);
          } else {
            _userDayAwardRowFilters[rowKey] = label;
          }
        });
      },
      borderRadius: BorderRadius.circular(999),
      child: _TraceChip(
        label: '$label $count',
        backgroundColor: isActive ? AppColors.secondary.withValues(alpha: 0.28) : null,
      ),
    );
  }

  List<PresenceSessionTraceSummary> _sessionsForUserDayRow(
    PresenceUserDayAwardSummary summary, {
    required String filter,
  }) {
    final sessions = _userDayAwardSessions[summary.rowKey] ?? const <PresenceSessionTraceSummary>[];
    if (filter == 'ALL') {
      return sessions;
    }
    if (filter == 'QR_TO_CAM') {
      final contributingIds = summary.qrToCamContributingSessionUuids.toSet();
      if (contributingIds.isEmpty) {
        return const <PresenceSessionTraceSummary>[];
      }
      return sessions.where((session) => contributingIds.contains(session.sessionUuid)).toList();
    }
    return sessions
        .where((session) => _userDayGrantLabel(session.grantType) == filter)
        .toList();
  }

  String _interactionLabelForSession(PresenceSessionTraceSummary session) {
    if (session.interactionLabel != null && session.interactionLabel!.isNotEmpty) {
      final normalized = session.interactionLabel!.toLowerCase();
      if (normalized.contains('verified presence') ||
          normalized.contains('qr + video') ||
          normalized.contains('owner qr + video') ||
          normalized.contains('presence_verified_match')) {
        return 'Cam & QR';
      }
      if (normalized.contains('presence match') ||
          normalized.contains('video-only people match') ||
          normalized.contains('presence_match')) {
        return 'Cam';
      }
      if (normalized.contains('checkin') ||
          normalized.contains('check-in') ||
          normalized.contains('check in') ||
          normalized.contains('qr-only grant') ||
          normalized.contains('presence_check_in') ||
          normalized.contains('owner qr verification')) {
        return 'QR';
      }
      return session.interactionLabel!;
    }
    switch (session.sessionMode) {
      case 'qr_only':
        return 'QR';
      case 'camera_only':
        return 'Cam';
      case 'qr_plus_camera':
        return 'Cam & QR';
      default:
        return 'Cam & QR';
    }
  }

  IconData _interactionIconForSession(PresenceSessionTraceSummary session) {
    final interaction = (session.interactionLabel ?? '').toLowerCase();
    if (interaction.contains('owner qr')) {
      return Icons.badge_outlined;
    }
    if (session.sessionMode == 'qr_only') {
      return Icons.qr_code_2;
    }
    if (session.sessionMode == 'camera_only') {
      return Icons.videocam;
    }
    if (session.sessionMode == 'qr_plus_camera') {
      return Icons.video_call;
    }
    return Icons.fact_check_outlined;
  }

  Color _statusColorForSession(PresenceSessionTraceSummary session, ColorScheme colorScheme) {
    if (session.decision == 'granted') {
      return Colors.greenAccent;
    }
    if (session.decision == 'denied') {
      return Colors.orangeAccent;
    }
    if (session.decision == 'failed' || session.status == 'failed') {
      return colorScheme.error;
    }
    if (session.decision == 'retry_required') {
      return Colors.amberAccent;
    }
    return colorScheme.primary;
  }

  Widget _buildAdminSection(BuildContext context) {
    final installation = _installationContext;
    final activePresenceIndividualGroup = _activePresenceIndividualGroup;
    final reservedCameraUuid = installation?.reservedCameraUuid;
    final reservedCameraName = reservedCameraUuid == null
      ? null
      : _cameras
        .where((camera) => camera.deviceId == reservedCameraUuid)
        .map((camera) => camera.name.isEmpty ? camera.deviceId : camera.name)
        .cast<String?>()
        .firstWhere((name) => name != null, orElse: () => reservedCameraUuid);
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
                if (reservedCameraName != null)
                  _TraceChip(label: 'Camera $reservedCameraName'),
                if (activePresenceIndividualGroup != null)
                  _TraceChip(label: 'Group ${activePresenceIndividualGroup.name}'),
              ],
            ),
            const SizedBox(height: 16),
          ],
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
            'Presence Match Groups',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            'Reserve one group as the active ppl-match group for presence.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[400]),
          ),
          const SizedBox(height: 12),
          if (_presenceMatchGroups.isEmpty)
            Text(
              'No individual groups are available yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            ..._presenceMatchGroups.map((group) {
              final isActive = activePresenceIndividualGroup != null &&
                  group.individualGroupId == activePresenceIndividualGroup.individualGroupId;
              return Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  title: Text(group.name),
                  subtitle: Text('${group.individualGroupId} • ${group.memberCount} members'),
                  trailing: isActive
                      ? TextButton(
                          onPressed: _isSubmittingAdminAction ? null : () => _unreservePresenceMatchGroup(group),
                          child: const Text('Unreserve'),
                        )
                      : TextButton(
                          onPressed: _isSubmittingAdminAction ? null : () => _reservePresenceMatchGroup(group),
                          child: const Text('Reserve'),
                        ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildExecutionSection(BuildContext context) {
    final outlinedBorderColor = Theme.of(context).colorScheme.outline.withValues(alpha: 0.5);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_isSubmittingAdminAction)
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        LayoutBuilder(
          builder: (context, constraints) {
            final isCompact = constraints.maxWidth < 560;
            final buttonWidth = isCompact
                ? (constraints.maxWidth - 12) / 2
                : (constraints.maxWidth - 36) / 4;
            final buttonHeight = isCompact ? 132.0 : 168.0;
            final iconSize = isCompact ? 42.0 : 56.0;

            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SizedBox(
                  width: buttonWidth.clamp(140.0, 280.0),
                  height: buttonHeight,
                  child: OutlinedButton(
                    onPressed: _isSubmittingAdminAction ? null : _renderPresenceQr,
                    style: OutlinedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      side: BorderSide(color: outlinedBorderColor),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.qr_code_2, size: iconSize),
                        const SizedBox(height: 12),
                        Text(
                          'Render QR',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(
                  width: buttonWidth.clamp(140.0, 280.0),
                  height: buttonHeight,
                  child: OutlinedButton(
                    onPressed: _isSubmittingAdminAction ? null : _startCameraOnlyMatch,
                    style: OutlinedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      side: BorderSide(color: outlinedBorderColor),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.videocam, size: iconSize),
                        const SizedBox(height: 12),
                        Text(
                          'Video Match',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(
                  width: buttonWidth.clamp(140.0, 280.0),
                  height: buttonHeight,
                  child: OutlinedButton(
                    onPressed: _isSubmittingAdminAction ? null : _openOwnerQrScanner,
                    style: OutlinedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      side: BorderSide(color: outlinedBorderColor),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.badge_outlined, size: iconSize),
                        const SizedBox(height: 12),
                        Text(
                          'Scan Owner QR',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(
                  width: buttonWidth.clamp(140.0, 280.0),
                  height: buttonHeight,
                  child: OutlinedButton(
                    onPressed: widget.stationMode || _isSubmittingAdminAction
                        ? null
                        : _openOwnerQrVideoScanner,
                    style: OutlinedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      side: BorderSide(color: outlinedBorderColor),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                      ),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.video_call, size: iconSize),
                        const SizedBox(height: 12),
                        Text(
                          'Scan Owner QR + Video',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
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
          if (_currentQr != null && (_activeSession?.sessionMode ?? '') != 'camera_only') ...[
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
              Align(
                alignment: Alignment.centerRight,
                child: IconButton(
                  onPressed: _copyQrToken,
                  tooltip: 'Copy QR data',
                  icon: const Icon(Icons.copy),
                ),
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
    );
  }
}

class _PresenceSessionInspector extends StatefulWidget {
  final PresenceSessionTraceSummary session;
  final PresenceApiClient apiClient;
  final List<PresenceCameraOption> cameras;

  const _PresenceSessionInspector({
    required this.session,
    required this.apiClient,
    required this.cameras,
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
                  ), cameras: widget.cameras),
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
  final List<PresenceCameraOption> cameras;

  const _SessionOverviewCard({required this.session, required this.cameras});

  String? _cameraLabel() {
    final cameraId = session.resolvedCameraUuid;
    if (cameraId == null || cameraId.isEmpty) {
      return null;
    }
    final matched = cameras.where((camera) => camera.deviceId == cameraId).toList();
    if (matched.isEmpty) {
      return cameraId;
    }
    final name = matched.first.name;
    return name.isEmpty ? cameraId : name;
  }

  @override
  Widget build(BuildContext context) {
    final cameraLabel = _cameraLabel();
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
          if (cameraLabel != null) _TraceChip(label: 'Camera $cameraLabel'),
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

class _ManagePresenceGroupDialog extends StatefulWidget {
  final PresenceIndividualGroupOption? currentGroup;
  final List<PresenceIndividualGroupOption> availableGroups;

  const _ManagePresenceGroupDialog({
    required this.currentGroup,
    required this.availableGroups,
  });

  @override
  State<_ManagePresenceGroupDialog> createState() => _ManagePresenceGroupDialogState();
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

class _ManagePresenceGroupDialogState extends State<_ManagePresenceGroupDialog> {
  final _displayNameController = TextEditingController();
  PresenceIndividualGroupOption? _selectedGroup;

  @override
  void initState() {
    super.initState();
    _selectedGroup = widget.currentGroup;
    _displayNameController.text = widget.currentGroup?.name ?? '';
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasCurrentGroup = widget.currentGroup != null;
    return AlertDialog(
      title: Text(hasCurrentGroup ? 'Manage Match Group' : 'Create Match Group'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.currentGroup != null) ...[
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(widget.currentGroup!.name),
                subtitle: Text(widget.currentGroup!.individualGroupId),
                trailing: Text('${widget.currentGroup!.memberCount} members'),
              ),
              const SizedBox(height: 12),
            ],
            Autocomplete<PresenceIndividualGroupOption>(
              initialValue: TextEditingValue(text: _displayNameController.text),
              optionsBuilder: (textEditingValue) {
                final query = textEditingValue.text.trim().toLowerCase();
                if (query.isEmpty) {
                  return widget.availableGroups;
                }
                return widget.availableGroups.where(
                  (group) => group.name.toLowerCase().contains(query),
                );
              },
              displayStringForOption: (option) => option.name,
              onSelected: (group) {
                _selectedGroup = group;
                _displayNameController.text = group.name;
              },
              fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
                controller.value = TextEditingValue(
                  text: _displayNameController.text,
                  selection: TextSelection.collapsed(offset: _displayNameController.text.length),
                );
                controller.addListener(() {
                  _displayNameController.value = controller.value;
                  if (_selectedGroup != null && controller.text.trim() != _selectedGroup!.name) {
                    _selectedGroup = null;
                  }
                });
                return TextFormField(
                  controller: controller,
                  focusNode: focusNode,
                  decoration: InputDecoration(
                    labelText: 'Match Group Name',
                    helperText: hasCurrentGroup
                        ? 'Select an existing individual group or enter a new name to create it.'
                        : 'Enter the individual group name Presence should use for matching.',
                    border: const OutlineInputBorder(),
                  ),
                  onFieldSubmitted: (_) => onFieldSubmitted(),
                );
              },
              optionsViewBuilder: (context, onSelected, options) {
                return Align(
                  alignment: Alignment.topLeft,
                  child: Material(
                    color: Theme.of(context).colorScheme.surface,
                    elevation: 4,
                    borderRadius: BorderRadius.circular(12),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 480, maxHeight: 240),
                      child: ListView.builder(
                        padding: EdgeInsets.zero,
                        shrinkWrap: true,
                        itemCount: options.length,
                        itemBuilder: (context, index) {
                          final group = options.elementAt(index);
                          return ListTile(
                            title: Text(group.name),
                            subtitle: Text(group.individualGroupId),
                            trailing: Text('${group.memberCount} members'),
                            onTap: () => onSelected(group),
                          );
                        },
                      ),
                    ),
                  ),
                );
              },
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
              'group_name': displayName,
              'individual_group_id': _selectedGroup?.individualGroupId,
            });
          },
          child: Text(hasCurrentGroup ? 'Save' : 'Create'),
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
  final Color? backgroundColor;
  final Color? foregroundColor;

  const _TraceChip({
    required this.label,
    this.backgroundColor,
    this.foregroundColor,
  });

  @override
  Widget build(BuildContext context) {
    final resolvedBackgroundColor = backgroundColor ?? AppColors.secondary.withValues(alpha: 0.12);
    final resolvedForegroundColor = foregroundColor ?? AppColors.secondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: resolvedBackgroundColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: resolvedForegroundColor,
              fontWeight: FontWeight.w600,
            ),
      ),
    );
  }
}