import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../utils/offline_fonts.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/camera_status_providers.dart';
import '../../../core/theme/theme_kit.dart';
import '../../widgets/camera/camera_card.dart';
import '../../widgets/camera/rtsp_camera_dialog.dart';
import '../../widgets/camera/add_edge_camera_dialog.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../../widgets/automatic_face_detection_status.dart';
import 'multi_stream_page.dart';
import 'camera_pipeline_settings_screen.dart';
import 'instant_detection_logs_pane.dart';
import '../../../screens/analytics_screen.dart';
import '../../../presentation/widgets/common/ux_breakpoints.dart';
import '../../../presentation/widgets/common/content_pane.dart';

/// Right content pane mode on Cameras (master/detail).
enum _CameraPaneMode { analytics, instantLogs, settings }

/// Enhanced cameras screen with real-time status monitoring
class CamerasScreen extends ConsumerStatefulWidget {
  const CamerasScreen({super.key, this.initialDeviceId});

  /// When set (e.g. deep link `/cameras/:id`), open that camera's content pane.
  final String? initialDeviceId;

  @override
  ConsumerState<CamerasScreen> createState() => _CamerasScreenState();
}

class _CamerasScreenState extends ConsumerState<CamerasScreen> {
  // REMOVED: bool _showMonitoringDashboard = false; // Complex monitoring dashboard removed
  bool _showLiveStreams = false; // Disable streaming by default to prevent auto-connection
  bool _showArchivedCameras = false; // Toggle to show/hide archived cameras
  String? _selectedDeviceId;

  /// Right pane: Analytics (default) / Instant Detection logs / Pipeline settings.
  _CameraPaneMode _paneMode = _CameraPaneMode.analytics;

  Camera _selectedCamera(CameraListState state) {
    for (final c in state.cameras) {
      if (c.deviceId == _selectedDeviceId) return c;
    }
    return state.cameras.first;
  }

  void _selectCamera(String deviceId) {
    setState(() {
      _selectedDeviceId = deviceId;
      _paneMode = _CameraPaneMode.analytics;
    });
  }

  void _clearMobileSelection() {
    setState(() {
      _selectedDeviceId = null;
      _paneMode = _CameraPaneMode.analytics;
    });
    // Deep links land on `/cameras/:id`; return to the list route.
    if (widget.initialDeviceId != null) {
      context.go('/cameras');
    }
  }

  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  CameraType? _typeFilter; // null = All camera types

  @override
  void initState() {
    super.initState();
    _selectedDeviceId = widget.initialDeviceId;
    // Load cameras when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cameraListState = ref.watch(cameraListProvider);

    bool isCameraActiveForMultiview(Camera camera) {
      final status = ref.read(cameraStatusProvider(camera.deviceId));
      final normalized = camera.status.toLowerCase();
      final cameraSaysActive = normalized == 'connected' || normalized == 'streaming';
      final wsSaysActive = (status?.isConnected ?? false) || (status?.isStreaming ?? false);
      return wsSaysActive || cameraSaysActive;
    }

    final bool masterDetail = isWide(context);
    final bool mobileDetailOpen =
        !masterDetail && _selectedDeviceId != null && cameraListState.cameras.isNotEmpty;
    final String appBarTitle = mobileDetailOpen
        ? _selectedCamera(cameraListState).name
        : 'Cameras';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: CustomAppBar(
        title: appBarTitle,
        showBackButton: mobileDetailOpen,
        showHomeButton: !mobileDetailOpen,
        onBackPressed: mobileDetailOpen ? _clearMobileSelection : null,
        actions: [
          // Multi-stream viewer button
          IconButton(
            onPressed: () {
              final connectedCameras = cameraListState.cameras
                  .where(isCameraActiveForMultiview)
                  .toList();
              
              if (connectedCameras.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('No connected cameras. Connect cameras first to view streams.'),
                    duration: Duration(seconds: 3),
                  ),
                );
                return;
              }
              
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => MultiStreamPage(cameras: cameraListState.cameras),
                ),
              );
            },
            icon: const Icon(Icons.view_comfy),
            color: AppColors.primary,
            tooltip: 'View All Streams',
          ),
          
          // Live streaming toggle
          IconButton(
            onPressed: () {
              setState(() {
                _showLiveStreams = !_showLiveStreams;
              });
            },
            icon: Icon(
              _showLiveStreams ? Icons.videocam : Icons.videocam_off,
              color: _showLiveStreams ? Colors.green : AppColors.textSecondary,
            ),
            tooltip: _showLiveStreams ? 'Hide Live Streams' : 'Show Live Streams',
          ),
          
          // Toggle archived cameras visibility
          IconButton(
            onPressed: () {
              setState(() {
                _showArchivedCameras = !_showArchivedCameras;
              });
              // Reload cameras with updated filter
              ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
            },
            icon: Icon(
              Icons.archive,
              color: _showArchivedCameras ? Colors.orange : AppColors.textSecondary,
            ),
            tooltip: _showArchivedCameras ? 'Hide Archived Cameras' : 'Show Archived Cameras',
          ),
          
          // Toggle monitoring dashboard - DISABLED (complex monitoring removed)
          /* IconButton(
            onPressed: () {
              setState(() {
                _showMonitoringDashboard = !_showMonitoringDashboard;
              });
            },
            icon: Icon(
              _showMonitoringDashboard ? Icons.dashboard : Icons.dashboard_outlined,
              color: AppColors.primary,
            ),
            tooltip: 'Toggle Monitoring Dashboard',
          ), */
          
          // Global monitoring toggle - DISABLED (complex monitoring removed)
          /* IconButton(
            onPressed: () {
              if (monitoringEnabled) {
                ref.read(cameraMonitoringProvider.notifier).stopAllMonitoring();
              } else {
                // Start monitoring for all cameras
                for (final camera in cameraListState.cameras) {
                  ref.read(cameraMonitoringProvider.notifier).startMonitoring(camera.deviceId);
                }
              }
            },
            icon: Icon(
              monitoringEnabled ? Icons.monitor : Icons.monitor_outlined,
              color: monitoringEnabled ? Colors.green : AppColors.textSecondary,
            ),
            tooltip: monitoringEnabled ? 'Stop All Monitoring' : 'Start All Monitoring',
          ), */
          
          // Scan for connected local cameras, then reload the full list
          IconButton(
            onPressed: cameraListState.isDetecting
                ? null
                : () async {
                    try {
                      await ref.read(cameraListProvider.notifier).detectCameras(
                            saveToDb: true,
                            includeArchived: _showArchivedCameras,
                          );
                      if (!mounted) return;
                      final cameras = ref.read(cameraListProvider).cameras;
                      final usbCount =
                          cameras.where((c) => c.type == CameraType.usb).length;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            usbCount == 0
                                ? 'Scan complete. No local cameras found.'
                                : 'Scan complete. ${cameras.length} camera(s) in list.',
                          ),
                          backgroundColor:
                              usbCount == 0 ? Colors.orange : Colors.green,
                        ),
                      );
                    } catch (e) {
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Camera scan failed: $e'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  },
            icon: cameraListState.isDetecting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(
                    Icons.refresh,
                    color: AppColors.primary,
                  ),
            tooltip: 'Scan for connected cameras',
          ),
          
          // Add RTSP Camera
          IconButton(
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => const RTSPCameraDialog(
                  isEditing: false,
                ),
              ).then((result) {
                if (result == true) {
                  // Reload cameras after adding
                  ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
                }
              });
            },
            icon: Icon(
              Icons.add,
              color: AppColors.primary,
            ),
            tooltip: 'Add RTSP Camera',
          ),
          
          // Add Edge Camera
          IconButton(
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => const AddEdgeCameraDialog(),
              ).then((result) {
                if (result == true) {
                  // Reload cameras after adding
                  ref.read(cameraListProvider.notifier).loadCameras();
                }
              });
            },
            icon: Icon(
              Icons.camera_outdoor,
              color: AppColors.accent,
            ),
            tooltip: 'Add Edge Camera',
          ),
        ],
      ),
      body: Column(
        children: [
          // REMOVED: Monitoring dashboard (complex monitoring removed)
          /* if (_showMonitoringDashboard) ...[
            Container(
              height: 240,
              child: const CameraMonitoringDashboard(),
            ),
            const Divider(height: 1),
            
            // NEW: Automatic Face Detection Status
            const AutomaticFaceDetectionStatus(),
          ], */
          
          // Master/detail on wide screens; on narrow, tapping a card swaps the
          // list for the same content pane (analytics ⇄ pipeline settings).
          if (masterDetail)
            Expanded(
              child: Row(
                children: [
                  SizedBox(
                    width: kMasterPaneWidth,
                    child: _buildCamerasContent(cameraListState),
                  ),
                  const VerticalDivider(width: 1),
                  const SizedBox(width: 4),
                  Expanded(
                    child: _rightPane(cameraListState),
                  ),
                ],
              ),
            )
          else
            Expanded(
              child: mobileDetailOpen
                  ? _rightPane(cameraListState)
                  : _buildCamerasContent(cameraListState),
            ),
        ],
      ),
    );
  }

  Widget _buildCamerasContent(CameraListState cameraListState) {
    if (cameraListState.isLoading || cameraListState.isDetecting) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }
    
    if (cameraListState.error != null) {
      return _buildErrorView(cameraListState.error!);
    }
    
    return _buildCamerasList(cameraListState.cameras);
  }

  Widget _buildCamerasList(List<Camera> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState();
    }

    // In wide (desktop) mode taps select the camera into the content pane
    // instead of navigating away to the detail route.
    final bool isMasterDetail = isWide(context);

    final query = _searchQuery.trim().toLowerCase();
    final List<Camera> filtered = cameras.where((c) {
      final matchesQuery = query.isEmpty ||
          c.name.toLowerCase().contains(query) ||
          c.deviceId.toLowerCase().contains(query);
      final matchesType = _typeFilter == null || c.type == _typeFilter;
      return matchesQuery && matchesType;
    }).toList();

    // Default-select the first visible camera so the sidebar highlights it and
    // the right detail pane shows its content on load.
    final String? effectiveSelectedId =
        _selectedDeviceId ?? (filtered.isNotEmpty ? filtered.first.deviceId : null);

    if (filtered.isEmpty) {
      return Column(
        children: [
          ListableItemsActionBar(
            searchController: _searchController,
            onSearchChanged: (value) => setState(() => _searchQuery = value),
            filterContent: Center(child: _buildFilterToggles()),
          ),
          Expanded(child: _buildNoMatches()),
        ],
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
      },
      child: LayoutBuilder(
        builder: (context, constraints) {
          final isWide = constraints.maxWidth >= 900;
          return Column(
            children: [
              // Sticky search + type filter action bar (always visible)
              ListableItemsActionBar(
                searchController: _searchController,
                onSearchChanged: (value) => setState(() => _searchQuery = value),
                filterContent: Center(child: _buildFilterToggles()),
              ),
              Expanded(
                child: CustomScrollView(
                  slivers: [
                    const SliverToBoxAdapter(child: SizedBox(height: 8)),
                    if (isWide)
                      SliverPadding(
                        padding: const EdgeInsets.all(16),
                        sliver: SliverToBoxAdapter(
                          child: LayoutBuilder(
                            builder: (context, constraints) {
                              final cols = constraints.maxWidth >= 1400 ? 3 : 2;
                              final spacing = 16.0;
                              final cardWidth =
                                  (constraints.maxWidth - spacing * (cols - 1)) / cols;
                              return Wrap(
                                spacing: spacing,
                                runSpacing: spacing,
                                children: [
                                  for (final camera in filtered)
                                    SizedBox(
                                      width: cardWidth,
                                      child: CameraCard(
                                        camera: camera,
                                        selected: isMasterDetail &&
                                            camera.deviceId == effectiveSelectedId,
                                        onTap: () => _selectCamera(camera.deviceId),
                                      ),
                                    ),
                                ],
                              );
                            },
                          ),
                        ),
                      )
                    else
                      SliverPadding(
                        padding: const EdgeInsets.all(16),
                        sliver: SliverList(
                          delegate: SliverChildBuilderDelegate(
                            (context, index) => Padding(
                              padding: const EdgeInsets.only(bottom: 16),
                              child: CameraCard(
                                camera: filtered[index],
                                selected: isMasterDetail &&
                                    filtered[index].deviceId == effectiveSelectedId,
                                onTap: () =>
                                    _selectCamera(filtered[index].deviceId),
                              ),
                            ),
                            childCount: filtered.length,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  /// Right content pane (desktop master/detail): Analytics / Instant logs /
  /// Pipeline settings for the selected camera.
  Widget _rightPane(CameraListState state) {
    if (state.cameras.isEmpty) {
      return _buildEmptyPane();
    }
    final camera = _selectedCamera(state);
    final scheme = Theme.of(context).colorScheme;
    final modeIndex = _paneMode.index;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ContentBar(
          title: camera.name,
          trailing: ContentBar.tripleModePill(
            selectedIndex: modeIndex,
            onChanged: (i) => setState(
              () => _paneMode = _CameraPaneMode.values[i],
            ),
            scheme: scheme,
            icons: const [
              Icons.insert_chart_outlined,
              Icons.receipt_long_outlined,
              Icons.settings_outlined,
            ],
            tooltips: const [
              'Analytics',
              'Instant Detection logs',
              'Pipeline settings',
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: switch (_paneMode) {
            _CameraPaneMode.settings => CameraPipelineSettingsScreen(
                key: ValueKey('settings-${camera.deviceId}'),
                camera: camera,
                showAppBar: false,
              ),
            _CameraPaneMode.instantLogs => InstantDetectionLogsPane(
                key: ValueKey('id-logs-${camera.deviceId}'),
                cameraDeviceId: camera.deviceId,
              ),
            _CameraPaneMode.analytics => AnalyticsScreen(
                key: ValueKey('analytics-${camera.deviceId}'),
                initialCameraId: camera.deviceId,
                initialDataSource: 'instant_detection',
                showAppBar: false,
              ),
          },
        ),
      ],
    );
  }

  /// Placeholder shown in the content pane when there are no cameras.
  Widget _buildEmptyPane() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.videocam_off_outlined,
            size: 64,
            color: AppColors.textSecondary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'Select a camera to view its live stream and controls',
            style: OfflineFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  /// Camera type filter toggles shown under the search field.
  Widget _buildFilterToggles() {
    const types = <CameraType?>[
      null,
      CameraType.usb,
      CameraType.rtsp,
      CameraType.edge,
      CameraType.mobile,
    ];

    const icons = <IconData>[
      Icons.dashboard_outlined, // All
      Icons.videocam,           // Connected (local / embedded / USB)
      AppIcons.cameras,         // RTSP
      Icons.router,             // Edge
      Icons.smartphone,         // Mobile
    ];

    String labelFor(CameraType? type) {
      if (type == null) return 'All';
      if (type == CameraType.usb) return 'Connected';
      return type.displayName.split(' ').first;
    }

    return ToggleButtons(
      constraints: const BoxConstraints(minHeight: 32),
      borderRadius: BorderRadius.circular(AppRadius.sm),
      isSelected: types.map((t) => t == _typeFilter).toList(),
      onPressed: (index) {
        setState(() => _typeFilter = types[index]);
      },
      selectedColor: AppColors.accent,
      fillColor: AppColors.accent.withValues(alpha: 0.1),
      borderColor: AppColors.gray700,
      selectedBorderColor: AppColors.accent.withValues(alpha: 0.4),
      children: [
        for (var i = 0; i < types.length; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icons[i], size: AppIconSize.sm),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  labelFor(types[i]),
                  style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
      ],
    );
  }

  /// Placeholder shown when the search yields no matches.
  Widget _buildNoMatches() {
    return Center(
      child: Text(
        'No cameras match your search',
        style: OfflineFonts.inter(
          fontSize: 14,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }

  Widget _buildInfoChip({required IconData icon, required String label}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: AppColors.textSecondary),
        const SizedBox(width: 4),
        Text(
          label,
          style: OfflineFonts.inter(
            fontSize: 12,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.camera_alt_outlined,
            size: 64,
            color: AppColors.textSecondary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No cameras detected',
            style: OfflineFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Connect cameras and tap "Detect Cameras" to get started',
            style: OfflineFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary.withOpacity(0.7),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _showDetectCamerasDialog,
            icon: const Icon(Icons.camera_alt),
            label: const Text('Detect Cameras'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red.withOpacity(0.7),
          ),
          const SizedBox(height: 16),
          Text(
            'Error loading cameras',
            style: OfflineFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.red,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error.toString(),
            style: OfflineFonts.inter(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              ref.read(cameraListProvider.notifier).loadCameras(includeArchived: _showArchivedCameras);
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _runDetectCameras() async {
    try {
      await ref.read(cameraListProvider.notifier).detectCameras(
            saveToDb: true,
            includeArchived: _showArchivedCameras,
          );

      if (!mounted) return;
      final cameras = ref.read(cameraListProvider).cameras;
      if (cameras.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'No cameras detected. Check backend logs for errors.',
            ),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 5),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Detected ${cameras.length} camera(s)!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Detection failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showDetectCamerasDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Detect Cameras'),
        content: const Text(
          'This will scan for connected cameras and update the camera list. '
          'Make sure your cameras are properly connected.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await _runDetectCameras();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
            ),
            child: const Text('Detect'),
          ),
        ],
      ),
    );
  }
}
