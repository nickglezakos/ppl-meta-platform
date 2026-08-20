import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/trigger_model.dart'; 
import '../services/trigger_service.dart';
import '../core/models/camera.dart';
import '../core/theme/app_theme.dart';
import '../core/providers/camera_providers.dart';
import '../core/api/api_client.dart';
import '../services/individual_groups_api_client.dart';
import '../models/individual_group_models.dart';
import '../presentation/widgets/common/ux_breakpoints.dart';
import '../presentation/widgets/common/content_pane.dart';
import '../presentation/widgets/common/unified_toggle.dart';

class TriggersTab extends ConsumerStatefulWidget {
  const TriggersTab({super.key});

  @override
  ConsumerState<TriggersTab> createState() => _TriggersTabState();
}

class _TriggersTabState extends ConsumerState<TriggersTab> {
  final TriggerService _triggerService = TriggerService();
  final Map<String, String> _groupNameById = {};
  // Legacy age bracket fields migrate to age_threshold on edit.
  // Maps field name → age threshold value (start of bracket).
  static const Map<String, double> _legacyAgeFieldToThreshold = {
    'age_count_0_12': 6,
    'age_count_13_17': 13,
    'age_count_18_24': 18,
    'age_count_25_34': 25,
    'age_count_35_44': 35,
    'age_count_45_54': 45,
    'age_count_55_64': 55,
    'age_count_65_plus': 65,
    'percent_age_0_12': 6,
    'percent_age_13_17': 13,
    'percent_age_18_24': 18,
    'percent_age_25_34': 25,
    'percent_age_35_44': 35,
    'percent_age_45_54': 45,
    'percent_age_55_64': 55,
    'percent_age_65_plus': 65,
  };

  static const Set<String> _percentageConditionFields = {
    'percent_male',
    'percent_female',
  };

  bool _isLoading = true;
  String? _errorMessage;
  List<TriggerModel> _triggers = [];
  List<Map<String, String>> _availableActions = [];
  bool? _filterIsActive;
  int _currentPage = 1;
  int _totalPages = 1;

  // Master/detail + search (unified UX, Phase 4)
  TriggerModel? _selectedTrigger;
  bool _editingTrigger = false;
  Widget? _inlineTriggerEditor;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTriggers();
      _loadAvailableActions();
      _loadAvailableGroups();
    });
  }

  bool _isAgeThresholdField(String field) => field == 'age_threshold';

  /// Migrates legacy age bracket / percent_age fields to age_threshold.
  DemographicCondition _normalizeConditionForEdit(DemographicCondition condition) {
    final thresholdAge = _legacyAgeFieldToThreshold[condition.field];
    if (thresholdAge != null) {
      return DemographicCondition(
        field: 'age_threshold',
        operator: condition.operator,
        value: thresholdAge,
      );
    }

    if (condition.field == 'percent_age') {
      return DemographicCondition(
        field: 'age_threshold',
        operator: condition.operator,
        value: condition.value,
      );
    }

    return condition;
  }

  bool _isPercentageConditionField(String field) {
    return _percentageConditionFields.contains(field);
  }

  String _canonicalConditionField(String field) {
    // age_count_* and percent_age_* are migrated at load time.
    return field;
  }

  double _defaultConditionValueForField(String field) {
    if (_isPercentageConditionField(field)) return 50;
    if (_isAgeThresholdField(field)) return 18;
    return 1;
  }

  double _normalizedConditionValueForField({
    required String previousField,
    required String nextField,
    required double currentValue,
  }) {
    if (previousField == nextField) return currentValue;
    return _defaultConditionValueForField(nextField);
  }

  String _conditionValueLabel(String field) {
    if (_isPercentageConditionField(field)) return 'Percent';
    if (_isAgeThresholdField(field)) return 'Age';
    return 'Count';
  }

  String? _conditionValueSuffix(String field) {
    if (_isPercentageConditionField(field)) return '%';
    if (_isAgeThresholdField(field)) return 'yrs';
    return null;
  }

  String _formatConditionInputValue(double value) {
    if (value == value.roundToDouble()) {
      return value.toInt().toString();
    }
    return value.toString();
  }

  Future<void> _loadAvailableGroups() async {
    try {
      final groupsApiClient = IndividualGroupsApiClient(ref.read(apiClientProvider));
      final groupsResponse = await groupsApiClient.listGroups(limit: 200);
      if (groupsResponse.success && groupsResponse.data != null) {
        setState(() {
          _groupNameById
            ..clear()
            ..addEntries(
              groupsResponse.data!.groups.map(
                (group) => MapEntry(group.id, group.name),
              ),
            );
        });
      }
    } catch (e) {
      debugPrint('⚠️ Failed to load group names for triggers table: $e');
    }
  }

  Future<void> _loadAvailableActions() async {
    try {
      final apiClient = ref.read(apiClientProvider);

      debugPrint('🔍 [DEBUG] Loading available actions...');
      debugPrint('🔍 [DEBUG] ApiClient baseUrl: ${apiClient.dio.options.baseUrl}');
      debugPrint('🔍 [DEBUG] Request path: /api/v1/user-actions');
      debugPrint('🔍 [DEBUG] Full URL will be: ${apiClient.dio.options.baseUrl}/api/v1/user-actions');

      final response = await apiClient.get(
        '/api/v1/user-actions',
        queryParameters: {'page': '1', 'page_size': '100'},
      );

      debugPrint('🔍 [DEBUG] Response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = response.data;
        setState(() {
          _availableActions = (data['actions'] as List)
              .map((action) => {
                    'uuid': action['uuid'] as String,
                    'name': action['name'] as String,
                    'type': (action['action_type'] as String?) ?? '',
                  })
              .toList();
        });
        debugPrint('✅ Loaded ${_availableActions.length} available actions');
      }
    } catch (e) {
      debugPrint('❌ Error loading available actions: $e');
      debugPrint('🔍 [DEBUG] Error type: ${e.runtimeType}');
      debugPrint('🔍 [DEBUG] Error details: $e');
    }
  }

  
  Future<List<Camera>> _fetchCameras() async {
    try {
      debugPrint('🔐 Fetching cameras using CameraService (same as cameras screen)...');
      
      // Use the SAME camera service that the cameras screen uses
      final cameraService = ref.read(cameraServiceProvider);
      final cameras = await cameraService.getCameras();
      
      debugPrint('✅ Fetched ${cameras.length} cameras using CameraService');
      return cameras;
    } catch (e) {
      debugPrint('❌ Error fetching cameras: $e');
      // Return empty list instead of throwing
      return [];
    }
  }

  Future<void> _loadTriggers() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await _triggerService.fetchTriggers(
        page: _currentPage,
        pageSize: 50,
        isActive: _filterIsActive,
      );
      
      debugPrint('✅ Triggers loaded: ${response.triggers.length} triggers, total pages: ${response.totalPages}');
      
      setState(() {
        _triggers = response.triggers;
        _totalPages = response.totalPages;
        _isLoading = false;
        // Default-select the first trigger so the right settings pane is
        // populated on load (unless the user already picked one).
        _selectedTrigger ??=
            _triggers.isNotEmpty ? _triggers.first : null;
      });
    } catch (e) {
      debugPrint('❌ Error loading triggers: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }



  Future<void> _updateTriggerAction(TriggerModel trigger, String? actionUuid) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      
      final response = await apiClient.put(
        '/api/v1/triggers/${trigger.uuid}',
        data: {'action_uuids': actionUuid != null ? [actionUuid] : []},
      );
      
      if (response.statusCode == 200) {
        if (!mounted) return;
        _loadTriggers();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Trigger action updated successfully')),
        );
      } else {
        throw Exception('Failed to update trigger action');
      }
    } catch (e) {
      debugPrint('❌ Error updating trigger action: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error updating trigger action: $e')),
      );
    }
  }

  Future<void> _updateTriggerActions(TriggerModel trigger, List<String> actionUuids) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      
      final response = await apiClient.put(
        '/api/v1/triggers/${trigger.uuid}',
        data: {'action_uuids': actionUuids},
      );
      
      if (response.statusCode == 200) {
        if (!mounted) return;
        _loadTriggers();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Trigger actions updated successfully')),
        );
      } else {
        throw Exception('Failed to update trigger actions');
      }
    } catch (e) {
      debugPrint('❌ Error updating trigger actions: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error updating trigger actions: $e')),
      );
    }
  }

  Widget _buildActionChips(TriggerModel trigger) {
    final uuids = trigger.actionUuids ?? (trigger.actionUuid != null ? [trigger.actionUuid!] : []);
    final names = trigger.actionNames ?? (trigger.actionName != null ? [trigger.actionName!] : []);

    if (uuids.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade700),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('None', style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
            const SizedBox(width: 4),
            Icon(Icons.arrow_drop_down, color: Colors.grey.shade500, size: 18),
          ],
        ),
      );
    }

    return Wrap(
      spacing: 4,
      runSpacing: 4,
      children: [
        for (int i = 0; i < uuids.length; i++)
          Chip(
            label: Text(
              i < names.length ? names[i] : uuids[i].substring(0, 8),
              style: const TextStyle(color: Colors.white70, fontSize: 11),
            ),
            backgroundColor: AppColors.primary,
            padding: EdgeInsets.zero,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
          ),
        Icon(Icons.edit, color: Colors.grey.shade500, size: 14),
      ],
    );
  }

  Future<bool> _unifiedToggleTrigger(TriggerModel trigger) async {
    try {
      final apiClient = ref.read(apiClientProvider);

      final response = await apiClient.put(
        '/api/v1/triggers/${trigger.uuid}',
        data: {'is_active': !trigger.isActive},
      );

      if (response.statusCode == 200) {
        if (mounted) await _loadTriggers();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('❌ Error toggling trigger: $e');
      return false;
    }
  }

  Future<void> _deleteTrigger(TriggerModel trigger) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Trigger'),
        content: Text('Are you sure you want to delete "${trigger.name ?? trigger.uuid}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final apiClient = ref.read(apiClientProvider);
      
      final response = await apiClient.delete(
        '/api/v1/triggers/${trigger.uuid}',
      );
      
      if (response.statusCode == 200 || response.statusCode == 204) {
        if (!mounted) return;
        _loadTriggers();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Trigger deleted successfully')),
        );
      } else {
        throw Exception('Failed to delete trigger');
      }
    } catch (e) {
      debugPrint('❌ Error deleting trigger: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error deleting trigger: $e')),
      );
    }
  }

  String _latestMatchSummary(TriggerModel trigger) {
    if (trigger.triggerMode != 'ppl_match' && trigger.triggerMode != 'vprofile_match') {
      return '—';
    }
    final match = trigger.lastMatchInfo;
    if (match == null || match.isEmpty) {
      return 'No match yet';
    }

    final bestMatch = match['best_match'];
    if (bestMatch is Map<String, dynamic>) {
      final memberName = bestMatch['member_name']?.toString();
      final memberUuid = bestMatch['member_uuid']?.toString();
      final similarity = bestMatch['similarity_score'];
      final similarityText = similarity is num ? similarity.toStringAsFixed(2) : null;
      final personLabel = memberName ?? memberUuid ?? 'Unknown member';
      final scoreLabel = similarityText == null ? '' : ' • Score: $similarityText';
      return '$personLabel$scoreLabel';
    }

    final matchedMemberUuid = match['matched_member_uuid']?.toString();
    final similarity = match['similarity_score'];
    final similarityText = similarity is num ? similarity.toStringAsFixed(2) : null;
    final personLabel = matchedMemberUuid ?? 'Matched member';
    final scoreLabel = similarityText == null ? '' : ' • Score: $similarityText';
    return '$personLabel$scoreLabel';
  }

  String _latestMatchTime(TriggerModel trigger) {
    final matchedAt = trigger.lastMatchedAt;
    if (matchedAt == null) {
      return '';
    }
    final local = matchedAt.toLocal();
    final mm = local.month.toString().padLeft(2, '0');
    final dd = local.day.toString().padLeft(2, '0');
    final hh = local.hour.toString().padLeft(2, '0');
    final min = local.minute.toString().padLeft(2, '0');
    return '$mm/$dd ${local.year} $hh:$min';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, _) {
          final master = Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
            // Header
            LayoutBuilder(
              builder: (context, constraints) {
                final isCompact = constraints.maxWidth < 720;

                final createButton = ElevatedButton.icon(
                  onPressed: () => _showCreateEditDialog(),
                  icon: const Icon(Icons.add),
                  label: const Text('Create Trigger'),
                );

                final filterDropdown = DropdownButton<bool?>(
                  value: _filterIsActive,
                  hint: const Text('All Statuses'),
                  isExpanded: isCompact,
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Statuses')),
                    DropdownMenuItem(value: true, child: Text('Active Only')),
                    DropdownMenuItem(value: false, child: Text('Inactive Only')),
                  ],
                  onChanged: (value) {
                    setState(() => _filterIsActive = value);
                    _loadTriggers();
                  },
                );

                final refreshButton = IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () async {
                    await _loadTriggers();
                    await _loadAvailableGroups();
                  },
                  tooltip: 'Refresh',
                );

                if (isCompact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Automation',
                        style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 12),
                      createButton,
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(child: filterDropdown),
                          const SizedBox(width: 8),
                          refreshButton,
                        ],
                      ),
                    ],
                  );
                }

                return Row(
                  children: [
                    const Text(
                      'Automation',
                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(width: 16),
                    createButton,
                    const Spacer(),
                    filterDropdown,
                    const SizedBox(width: 16),
                    refreshButton,
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            
            // Content
            _buildSearchField(),
            const SizedBox(height: 12),

            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _errorMessage != null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text('Error: $_errorMessage', style: const TextStyle(color: AppColors.error)),
                              const SizedBox(height: 16),
                              ElevatedButton(
                                onPressed: _loadTriggers,
                                child: const Text('Retry'),
                              ),
                            ],
                          ),
                        )
                      : _triggers.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.notifications_none, size: 64, color: Colors.grey),
                                  const SizedBox(height: 16),
                                  const Text('No triggers found'),
                                  const SizedBox(height: 16),
                                  ElevatedButton.icon(
                                    onPressed: () => _showCreateEditDialog(),
                                    icon: const Icon(Icons.add),
                                    label: const Text('Create First Trigger'),
                                  ),
                                ],
                              ),
                            )
                          : _buildTriggerCards(),
            ),
            
            // Pagination
            if (_totalPages > 1)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      onPressed: _currentPage > 1
                          ? () {
                              setState(() => _currentPage--);
                              _loadTriggers();
                            }
                          : null,
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Text('Page $_currentPage of $_totalPages'),
                    IconButton(
                      onPressed: _currentPage < _totalPages
                          ? () {
                              setState(() => _currentPage++);
                              _loadTriggers();
                            }
                          : null,
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
              ),
          ],
            ),
          );
          if (isWide(context)) {
            return Row(
              children: [
                SizedBox(width: kMasterPaneWidth, child: master),
                const VerticalDivider(width: 1),
                const SizedBox(width: 4),
                Expanded(child: _buildDetailPane()),
              ],
            );
          }
          return master;
        },
      ),
    );
  }

  // ─────────────────────────────────────────────────
  // Card grid
  // ─────────────────────────────────────────────────

  static const _modeLabels = {
    'demographic': 'Instant Demographic',
    'ppl_match': 'Instant People Match',
    'search': 'Search People Match',
    'search_demographic': 'Search Demographic',
    'vprofile_match': 'VProfile Multi-Group',
  };

  static const _modeIcons = {
    'demographic': Icons.tune,
    'ppl_match': Icons.psychology,
    'search': Icons.search,
    'search_demographic': Icons.analytics,
    'vprofile_match': Icons.people_outline,
  };

  static const _modeColors = {
    'demographic': AppColors.primary,
    'ppl_match': AppColors.secondary,
    'search': AppColors.secondary,
    'search_demographic': AppColors.error,
    'vprofile_match': AppColors.info,
  };

  Widget _buildSearchField() {
    return TextField(
      controller: _searchController,
      onChanged: (value) => setState(() => _searchQuery = value),
      decoration: InputDecoration(
        hintText: 'Search triggers',
        prefixIcon: const Icon(Icons.search),
        isDense: true,
        filled: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }

  Future<void> _toggleInlineTriggerEditor(TriggerModel trigger) async {
    if (_editingTrigger) {
      setState(() {
        _editingTrigger = false;
        _inlineTriggerEditor = null;
      });
      return;
    }

    final w = await _showCreateEditDialog(
      trigger: trigger,
      embedded: true,
      onCancel: () {
        if (mounted) {
          setState(() {
            _editingTrigger = false;
            _inlineTriggerEditor = null;
          });
        }
      },
      onSaved: () async {
        await _loadTriggers();
        if (!mounted) return;
        setState(() {
          _editingTrigger = false;
          _inlineTriggerEditor = null;
          if (trigger.uuid != null) {
            final reloaded =
                _triggers.where((t) => t.uuid == trigger.uuid);
            if (reloaded.isNotEmpty) _selectedTrigger = reloaded.first;
          }
        });
      },
    );
    if (!mounted || w == null) return;
    setState(() {
      _inlineTriggerEditor = w;
      _editingTrigger = true;
    });
  }

  Widget _buildDetailPane() {
    final trigger = _selectedTrigger;
    if (trigger == null) {
      return ContentPane(
        title: 'Trigger',
        subtitle: 'Select a trigger to inspect it',
        child: const Center(
          child: Text('Select a trigger from the list to view its details'),
        ),
      );
    }

    final mode = trigger.triggerMode;
    final modeLabel = _modeLabels[mode] ?? mode;

    return ContentPane(
      title: trigger.name ?? 'Unnamed',
      subtitle: modeLabel,
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Status',
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    UnifiedToggle(
                      value: trigger.isActive,
                      label: trigger.isActive ? 'Active' : 'Inactive',
                      onToggle: (next) => _unifiedToggleTrigger(trigger),
                    ),
                    const SizedBox(height: 12),
                    _detailRow('Mode', modeLabel),
                    _detailRow(
                      'Camera',
                      trigger.cameraName ?? trigger.cameraDeviceId ?? '—',
                    ),
                    _detailRow('Conditions', '${trigger.conditionsDisplay}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _toggleInlineTriggerEditor(trigger),
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Edit'),
                ),
                OutlinedButton.icon(
                  onPressed: () => _deleteTrigger(trigger),
                  icon: const Icon(Icons.delete_outline),
                  style: OutlinedButton.styleFrom(foregroundColor: AppColors.error),
                  label: const Text('Delete'),
                ),
              ],
            ),
            if (_editingTrigger && _inlineTriggerEditor != null) ...[
              const SizedBox(height: 12),
              _inlineTriggerEditor!,
            ],
          ],
        ),
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey.shade500,
                  ),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }

  Widget _buildTriggerCards() {
    return LayoutBuilder(builder: (context, constraints) {
      // Responsive column count: 1 on narrow, 2 on medium, 3 on wide.
      final crossAxisCount = constraints.maxWidth > 1200
          ? 3
          : constraints.maxWidth > 700
              ? 2
              : 1;

      final gridDelegate = SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: crossAxisCount == 3
            ? 1.55
            : crossAxisCount == 2
                ? 1.4
                : 1.2,
        mainAxisExtent: crossAxisCount == 3
            ? null
            : crossAxisCount == 2
            ? 244
            : 264,
      );

      final q = _searchQuery.trim().toLowerCase();
      final visible = q.isEmpty
          ? _triggers
          : _triggers
                .where((t) =>
                    (t.name ?? '').toLowerCase().contains(q) ||
                    (t.triggerMode ?? '').toLowerCase().contains(q))
                .toList();

      return GridView.builder(
        gridDelegate: gridDelegate,
        itemCount: visible.length,
        itemBuilder: (context, index) => _buildTriggerCard(visible[index]),
      );
    });
  }

  Widget _buildTriggerCard(TriggerModel trigger) {
    final mode = trigger.triggerMode;
    final modeLabel = _modeLabels[mode] ?? mode;
    final modeIcon = _modeIcons[mode] ?? Icons.bolt;
    final modeColor = _modeColors[mode] ?? Colors.grey;

    final isPplOrSearch = mode == 'ppl_match' || mode == 'search';
    final isSearchMode = mode == 'search' || mode == 'search_demographic';

    final groupId = trigger.pplMatchGroupId;
    final groupName = groupId == null ? null : _groupNameById[groupId];

    final conditionsLabel = isPplOrSearch
        ? 'Group: ${groupName ?? groupId ?? 'Not set'}'
        : trigger.conditionsDisplay;

    final cameraLabel = isSearchMode
        ? '${trigger.searchCameraDeviceIds?.length ?? 0} camera(s)'
        : (trigger.cameraName ?? trigger.cameraDeviceId ?? '—');

    final latestMatchSummary = _latestMatchSummary(trigger);
    final latestMatchTime = _latestMatchTime(trigger);
    final hasMatch = latestMatchSummary != '—' && latestMatchSummary != 'No match yet';

    return Card(
      color: Colors.grey.shade900,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: trigger.isActive
              ? modeColor.withOpacity(0.45)
              : Colors.grey.shade700,
          width: 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () {
          if (isWide(context)) {
            setState(() {
              _selectedTrigger = trigger;
              _editingTrigger = false;
              _inlineTriggerEditor = null;
            });
          } else {
            _showCreateEditDialog(trigger: trigger);
          }
        },
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header row ──────────────────────────
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: modeColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Icon(modeIcon, color: modeColor, size: 16),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      trigger.name ?? 'Unnamed',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: Colors.white,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (!isWide(context)) ...[
                    const SizedBox(width: 4),
                    IconButton(
                      onPressed: () => _showCreateEditDialog(trigger: trigger),
                      icon: const Icon(Icons.settings_outlined, size: 20),
                      iconSize: 20,
                      padding: const EdgeInsets.all(4),
                      constraints: const BoxConstraints(),
                      tooltip: 'Trigger settings',
                    ),
                  ],
                  const SizedBox(width: 6),
                  // Informational status chip — editing/toggle lives in the
                  // right-hand detail pane (or pending editor on mobile).
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: trigger.isActive
                          ? AppColors.success.withValues(alpha: 0.14)
                          : AppColors.error.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      trigger.isActive ? 'Active' : 'Inactive',
                      style: TextStyle(
                        color: trigger.isActive
                            ? AppColors.success
                            : AppColors.error,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),

              // Mode pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: modeColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  modeLabel,
                  style: TextStyle(color: modeColor, fontSize: 10, fontWeight: FontWeight.w600),
                ),
              ),

              const SizedBox(height: 8),
              const Divider(height: 1, thickness: 1),
              const SizedBox(height: 8),

              // ── Info grid ───────────────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _cardInfoRow(
                      icon: isSearchMode ? Icons.videocam_outlined : Icons.camera_alt_outlined,
                      text: cameraLabel,
                    ),
                    const SizedBox(height: 4),
                    _cardInfoRow(
                      icon: Icons.rule_outlined,
                      text: conditionsLabel,
                    ),
                    if (trigger.timeSpan.isNotEmpty && trigger.timeSpan != 'any') ...[
                      const SizedBox(height: 4),
                      _cardInfoRow(
                        icon: Icons.schedule_outlined,
                        text: trigger.timeSpan,
                      ),
                    ],
                    if (hasMatch) ...[
                      const SizedBox(height: 4),
                      _cardInfoRow(
                        icon: Icons.person_search_outlined,
                        text: latestMatchTime.isEmpty
                            ? latestMatchSummary
                            : '$latestMatchSummary  ·  $latestMatchTime',
                        color: AppColors.warning,
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 6),

              // ── Footer: informational action chips ──
              // Editing (edit/delete/toggle) lives in the detail pane.
              _buildActionChips(trigger),
            ],
          ),
        ),
      ),
    );
  }

  Widget _cardInfoRow({
    required IconData icon,
    required String text,
    Color? color,
  }) {
    final textColor = color ?? Colors.white60;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 13, color: textColor),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 11.5, color: textColor),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Future<Widget?> _showCreateEditDialog({
    TriggerModel? trigger,
    bool embedded = false,
    VoidCallback? onCancel,
    VoidCallback? onSaved,
  }) async {
    final isEditing = trigger != null;
    
    // Fetch all registered cameras from database using the SAME method as cameras screen
    debugPrint('🔄 Loading cameras from database (same as cameras screen)...');
    List<Camera> availableCameras = await _fetchCameras();
    
    // Deduplicate cameras by deviceId
    final Map<String, Camera> cameraMap = {};
    for (var camera in availableCameras) {
      cameraMap[camera.deviceId] = camera;
    }
    availableCameras = cameraMap.values.toList();
    debugPrint('📦 Loaded ${availableCameras.length} cameras');

    final groupsApiClient = IndividualGroupsApiClient(ref.read(apiClientProvider));
    List<IndividualGroup> availableGroups = [];
    try {
      final groupsResponse = await groupsApiClient.listGroups(limit: 200);
      if (groupsResponse.success && groupsResponse.data != null) {
        availableGroups = groupsResponse.data!.groups;
        for (final group in availableGroups) {
          _groupNameById[group.id] = group.name;
        }
      }
    } catch (e) {
      debugPrint('⚠️ Failed to load individual groups: $e');
    }
    if (!mounted) return null;
    
    String? selectedCameraDeviceId = trigger?.cameraDeviceId;
    List<String> selectedActionUuids = List<String>.from(
      trigger?.actionUuids ?? (trigger?.actionUuid != null ? [trigger!.actionUuid!] : []),
    );
    
    // Validate that all selected action UUIDs exist in available actions
    selectedActionUuids.removeWhere((uuid) => !_availableActions.any((a) => a['uuid'] == uuid));
    
    // Form controllers
    final nameController = TextEditingController(text: trigger?.name);
    final descriptionController = TextEditingController(text: trigger?.description);
    final timeSpanController = TextEditingController(text: trigger?.timeSpan ?? 'any');
    final cooldownController = TextEditingController(text: trigger?.cooldownSeconds.toString() ?? '60');
    final similarityThresholdController = TextEditingController(
      text: trigger?.pplMatchSimilarityThreshold.toString() ?? '0.75',
    );
    final topKController = TextEditingController(
      text: trigger?.pplMatchTopK.toString() ?? '1',
    );
    String triggerMode = trigger?.triggerMode ?? 'demographic';
    String? selectedPplMatchGroupId = trigger?.pplMatchGroupId;
    List<String> selectedSearchCameraIds = trigger?.searchCameraDeviceIds ?? [];
    int searchIntervalSeconds = trigger?.searchIntervalSeconds ?? 300;
    bool pplMatchNegate = trigger?.pplMatchNegate ?? false;
    List<String> selectedVProfileGroupIds = trigger?.pplMatchGroupIds ?? [];
    List<String> selectedVProfileCameraIds = trigger?.cameraDeviceIds ?? [];
    final searchIntervalController = TextEditingController(
      text: (trigger?.searchIntervalSeconds ?? 300).toString(),
    );

    if (selectedPplMatchGroupId != null &&
        availableGroups.every((group) => group.id != selectedPplMatchGroupId)) {
      final fallbackName = _groupNameById[selectedPplMatchGroupId] ??
          'Current Group ($selectedPplMatchGroupId)';
      availableGroups = [
        IndividualGroup(
          id: selectedPplMatchGroupId,
          name: fallbackName,
          description: null,
          createdBy: '',
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
          memberCount: 0,
          memberIds: const [],
          visibility: GroupVisibility.private,
          tags: const [],
          coverIndividualId: null,
          metadata: const {},
        ),
        ...availableGroups,
      ];
    }
    
    // Demographic conditions — migrate legacy age bracket fields to age_threshold
    List<DemographicCondition> demographicConditions = (trigger?.demographicConditions ?? [
      DemographicCondition(field: 'people_count', operator: 'gte', value: 1),
    ]).map(_normalizeConditionForEdit).toList();
    
    // Parse tracking duration
    int trackingNumber = 10;
    String trackingUnit = 'minutes';
    if (trigger?.trackingDuration != null) {
      final parts = trigger!.trackingDuration.split(' ');
      if (parts.length >= 2) {
        trackingNumber = int.tryParse(parts[0]) ?? 10;
        trackingUnit = parts[1];
        if (!trackingUnit.endsWith('s')) trackingUnit += 's';
      }
    }
    
    bool isActive = trigger?.isActive ?? true;

    // Shared save routine used by both the modal and embedded (inline) editors.
    Future<void> doSave() async {
      try {
        final apiClient = ref.read(apiClientProvider);

        final cameraName = (triggerMode == 'search' || triggerMode == 'search_demographic')
            ? null
            : availableCameras.firstWhere(
                (c) => c.deviceId == selectedCameraDeviceId,
                orElse: () => Camera(
                  id: '',
                  deviceId: selectedCameraDeviceId ?? '',
                  name: selectedCameraDeviceId ?? '',
                  status: 'unknown',
                  resolution: '0x0',
                  type: CameraType.usb,
                  supportsRecording: false,
                ),
              ).name;

        final requestBody = TriggerCreateRequest(
          name: nameController.text.trim(),
          description: descriptionController.text.trim().isEmpty ? null : descriptionController.text.trim(),
          demographicConditions: (triggerMode == 'demographic' || triggerMode == 'search_demographic') ? demographicConditions : const [],
          timeSpan: timeSpanController.text.trim(),
          cameraDeviceId: (triggerMode == 'search' || triggerMode == 'search_demographic' || triggerMode == 'vprofile_match') ? null : selectedCameraDeviceId,
          cameraName: cameraName,
          actionUuid: selectedActionUuids.isNotEmpty ? selectedActionUuids.first : null,
          actionUuids: selectedActionUuids.isNotEmpty ? selectedActionUuids : null,
          trackingDuration: '$trackingNumber $trackingUnit',
          cooldownSeconds: int.tryParse(cooldownController.text) ?? 60,
          isActive: isActive,
          triggerMode: triggerMode,
          pplMatchGroupId: (triggerMode == 'ppl_match' || triggerMode == 'search')
            ? selectedPplMatchGroupId : null,
          pplMatchGroupIds: triggerMode == 'vprofile_match' ? selectedVProfileGroupIds : null,
          cameraDeviceIds: triggerMode == 'vprofile_match' ? selectedVProfileCameraIds : null,
          pplMatchSimilarityThreshold: (triggerMode == 'ppl_match' || triggerMode == 'search' || triggerMode == 'vprofile_match')
            ? (double.tryParse(similarityThresholdController.text) ?? 0.75)
            : null,
          pplMatchTopK: (triggerMode == 'ppl_match' || triggerMode == 'vprofile_match')
            ? (int.tryParse(topKController.text) ?? 1)
            : null,
          pplMatchNegate: (triggerMode == 'ppl_match' || triggerMode == 'search' || triggerMode == 'vprofile_match')
            ? pplMatchNegate : null,
          searchCameraDeviceIds: (triggerMode == 'search' || triggerMode == 'search_demographic') ? selectedSearchCameraIds : null,
          searchIntervalSeconds: (triggerMode == 'search' || triggerMode == 'search_demographic')
            ? (int.tryParse(searchIntervalController.text) ?? 300)
            : null,
        );

        final endpoint = isEditing
            ? '/api/v1/triggers/${trigger!.uuid}'
            : '/api/v1/triggers/';

        final response = isEditing
            ? await apiClient.put(endpoint, data: requestBody.toJson())
            : await apiClient.post(endpoint, data: requestBody.toJson());

        if (response.statusCode == 200 || response.statusCode == 201) {
          _loadTriggers();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Trigger ${isEditing ? 'updated' : 'created'} successfully')),
            );
          }
        } else {
          throw Exception('Failed to ${isEditing ? 'update' : 'create'} trigger: ${response.data}');
        }
      } catch (e) {
        debugPrint('❌ Error ${isEditing ? 'updating' : 'creating'} trigger: $e');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: $e')),
          );
        }
      }
    }

    final Widget editor = StatefulBuilder(
      builder: (context, setDialogState) {
        return AlertDialog(
          insetPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          title: Text(isEditing ? 'Edit Trigger' : 'Create Trigger'),
          content: SingleChildScrollView(
            child: SizedBox(
              width: 600,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                    // Basic info
                    TextField(
                      controller: nameController,
                      decoration: const InputDecoration(labelText: 'Name *'),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: descriptionController,
                      decoration: const InputDecoration(labelText: 'Description'),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 24),
                    
                    DropdownButtonFormField<String>(
                      value: triggerMode,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Trigger Mode',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'demographic',
                          child: Text('Instant Demographic'),
                        ),
                        DropdownMenuItem(
                          value: 'ppl_match',
                          child: Text('Instant People Match'),
                        ),
                        DropdownMenuItem(
                          value: 'search',
                          child: Text('Search People Match'),
                        ),
                        DropdownMenuItem(
                          value: 'search_demographic',
                          child: Text('Search Demographic'),
                        ),
                        DropdownMenuItem(
                          value: 'vprofile_match',
                          child: Text('VProfile Match (Multi-Group, Multi-Camera)'),
                        ),
                      ],
                      selectedItemBuilder: (context) => const [
                        Text('Instant Demographic', overflow: TextOverflow.ellipsis),
                        Text('Instant People Match', overflow: TextOverflow.ellipsis),
                        Text('Search People Match', overflow: TextOverflow.ellipsis),
                        Text('Search Demographic', overflow: TextOverflow.ellipsis),
                        Text('VProfile Match (Multi-Group, Multi-Camera)', overflow: TextOverflow.ellipsis),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        setDialogState(() {
                          triggerMode = value;
                        });
                      },
                    ),
                    const SizedBox(height: 16),

                    if (triggerMode == 'demographic')
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: LayoutBuilder(
                            builder: (context, constraints) {
                              final isCompact = constraints.maxWidth < 360;

                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (isCompact)
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Row(
                                          children: [
                                            Icon(Icons.tune, color: AppColors.primary, size: 20),
                                            SizedBox(width: 8),
                                            Expanded(
                                              child: Text(
                                                'Demographic Conditions (All must match)',
                                                style: TextStyle(fontWeight: FontWeight.bold),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 8),
                                        IconButton(
                                          icon: const Icon(Icons.add_circle, color: AppColors.primary),
                                          onPressed: () {
                                            setDialogState(() {
                                              demographicConditions.add(
                                                DemographicCondition(
                                                  field: 'people_count',
                                                  operator: 'gte',
                                                  value: 1,
                                                ),
                                              );
                                            });
                                          },
                                          tooltip: 'Add condition',
                                        ),
                                      ],
                                    )
                                  else
                                    Row(
                                      children: [
                                        const Icon(Icons.tune, color: AppColors.primary, size: 20),
                                        const SizedBox(width: 8),
                                        const Expanded(
                                          child: Text(
                                            'Demographic Conditions (All must match)',
                                            style: TextStyle(fontWeight: FontWeight.bold),
                                          ),
                                        ),
                                        IconButton(
                                          icon: const Icon(Icons.add_circle, color: AppColors.primary),
                                          onPressed: () {
                                            setDialogState(() {
                                              demographicConditions.add(
                                                DemographicCondition(
                                                  field: 'people_count',
                                                  operator: 'gte',
                                                  value: 1,
                                                ),
                                              );
                                            });
                                          },
                                          tooltip: 'Add condition',
                                        ),
                                      ],
                                    ),
                                  const SizedBox(height: 12),
                                  ...List.generate(demographicConditions.length, (index) {
                                    final condition = demographicConditions[index];
                                    final canonicalField = _canonicalConditionField(condition.field);

                                    final fieldDropdown = DropdownButtonFormField<String>(
                                      value: canonicalField,
                                      decoration: const InputDecoration(
                                        labelText: 'Field',
                                        border: OutlineInputBorder(),
                                        isDense: true,
                                      ),
                                      items: const [
                                        DropdownMenuItem(value: 'people_count', child: Text('People Count')),
                                        DropdownMenuItem(value: 'percent_male', child: Text('Male %')),
                                        DropdownMenuItem(value: 'percent_female', child: Text('Female %')),
                                        DropdownMenuItem(value: 'age_threshold', child: Text('Age')),
                                      ],
                                      onChanged: (value) {
                                        setDialogState(() {
                                          final nextField = value!;
                                          demographicConditions[index] = DemographicCondition(
                                            field: nextField,
                                            operator: condition.operator,
                                            value: _normalizedConditionValueForField(
                                              previousField: canonicalField,
                                              nextField: nextField,
                                              currentValue: condition.value,
                                            ),
                                          );
                                        });
                                      },
                                    );

                                    final operatorDropdown = DropdownButtonFormField<String>(
                                      value: condition.operator,
                                      decoration: const InputDecoration(
                                        labelText: 'Op',
                                        border: OutlineInputBorder(),
                                        isDense: true,
                                      ),
                                      items: const [
                                        DropdownMenuItem(value: 'gt', child: Text('>')),
                                        DropdownMenuItem(value: 'gte', child: Text('≥')),
                                        DropdownMenuItem(value: 'lt', child: Text('<')),
                                        DropdownMenuItem(value: 'lte', child: Text('≤')),
                                        DropdownMenuItem(value: 'eq', child: Text('=')),
                                      ],
                                      onChanged: (value) {
                                        setDialogState(() {
                                          demographicConditions[index] = DemographicCondition(
                                            field: canonicalField,
                                            operator: value!,
                                            value: condition.value,
                                          );
                                        });
                                      },
                                    );

                                    final valueField = TextFormField(
                                      key: ValueKey('demographic-condition-$index-${condition.field}'),
                                      initialValue: _formatConditionInputValue(condition.value),
                                      decoration: InputDecoration(
                                        labelText: _conditionValueLabel(canonicalField),
                                        suffixText: _conditionValueSuffix(canonicalField),
                                        border: const OutlineInputBorder(),
                                        isDense: true,
                                      ),
                                      keyboardType: TextInputType.number,
                                      inputFormatters: _isAgeThresholdField(canonicalField)
                                          ? [FilteringTextInputFormatter.digitsOnly]
                                          : _isPercentageConditionField(canonicalField)
                                              ? [FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*$'))]
                                              : [FilteringTextInputFormatter.digitsOnly],
                                      onChanged: (value) {
                                        var numValue = double.tryParse(value);
                                        if (numValue != null) {
                                          if (_isAgeThresholdField(canonicalField)) {
                                            numValue = numValue.clamp(1, 100);
                                          }
                                          setDialogState(() {
                                            demographicConditions[index] = DemographicCondition(
                                              field: canonicalField,
                                              operator: condition.operator,
                                              value: numValue!,
                                            );
                                          });
                                        }
                                      },
                                    );

                                    final removeButton = IconButton(
                                      icon: const Icon(Icons.remove_circle, color: AppColors.error),
                                      onPressed: demographicConditions.length > 1
                                          ? () {
                                              setDialogState(() {
                                                demographicConditions.removeAt(index);
                                              });
                                            }
                                          : null,
                                      tooltip: 'Remove condition',
                                    );

                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 8),
                                      child: isCompact
                                          ? Column(
                                              crossAxisAlignment: CrossAxisAlignment.stretch,
                                              children: [
                                                fieldDropdown,
                                                const SizedBox(height: 8),
                                                Row(
                                                  children: [
                                                    Expanded(child: operatorDropdown),
                                                    const SizedBox(width: 8),
                                                    Expanded(child: valueField),
                                                    const SizedBox(width: 8),
                                                    removeButton,
                                                  ],
                                                ),
                                              ],
                                            )
                                          : Row(
                                              children: [
                                                Expanded(flex: 3, child: fieldDropdown),
                                                const SizedBox(width: 8),
                                                Expanded(flex: 2, child: operatorDropdown),
                                                const SizedBox(width: 8),
                                                Expanded(flex: 2, child: valueField),
                                                const SizedBox(width: 8),
                                                removeButton,
                                              ],
                                            ),
                                    );
                                  }),
                                ],
                              );
                            },
                          ),
                        ),
                      )
                    else if (triggerMode == 'ppl_match')
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.psychology, color: AppColors.secondary, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    'PPL Match Configuration',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              DropdownButtonFormField<String>(
                                value: selectedPplMatchGroupId,
                                decoration: const InputDecoration(
                                  labelText: 'Individual Group *',
                                  border: OutlineInputBorder(),
                                ),
                                items: availableGroups.map((group) {
                                  return DropdownMenuItem<String>(
                                    value: group.id,
                                    child: Text(group.name),
                                  );
                                }).toList(),
                                onChanged: (value) =>
                                    setDialogState(() => selectedPplMatchGroupId = value),
                              ),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: similarityThresholdController,
                                      decoration: const InputDecoration(
                                        labelText: 'Similarity Threshold (0..1)',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextField(
                                      controller: topKController,
                                      decoration: const InputDecoration(
                                        labelText: 'Top K',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: TextInputType.number,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              SwitchListTile(
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                title: const Text('NOT mode'),
                                subtitle: const Text(
                                  'Fire when NO group members are matched',
                                  style: TextStyle(fontSize: 12),
                                ),
                                value: pplMatchNegate,
                                onChanged: (v) => setDialogState(() => pplMatchNegate = v),
                              ),
                            ],
                          ),
                        ),
                      )
                    else if (triggerMode == 'search')
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.search, color: AppColors.secondary, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    'Search Configuration',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              // Individual Group selector (required for search)
                              DropdownButtonFormField<String>(
                                value: selectedPplMatchGroupId,
                                decoration: const InputDecoration(
                                  labelText: 'Individual Group *',
                                  helperText: 'Group whose members will be searched against camera recordings',
                                  border: OutlineInputBorder(),
                                ),
                                items: availableGroups.map((group) {
                                  return DropdownMenuItem<String>(
                                    value: group.id,
                                    child: Text(group.name),
                                  );
                                }).toList(),
                                onChanged: (value) =>
                                    setDialogState(() => selectedPplMatchGroupId = value),
                              ),
                              const SizedBox(height: 12),
                              // Multi-camera selector
                              const Text('Cameras to Search *',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 180),
                                decoration: BoxDecoration(
                                  border: Border.all(color: Colors.grey.shade400),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: availableCameras.isEmpty
                                    ? const Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Text('No cameras available',
                                            style: TextStyle(color: AppColors.warning)),
                                      )
                                    : ListView.builder(
                                        shrinkWrap: true,
                                        itemCount: availableCameras.length,
                                        itemBuilder: (context, index) {
                                          final camera = availableCameras[index];
                                          final isSelected =
                                              selectedSearchCameraIds.contains(camera.deviceId);
                                          return CheckboxListTile(
                                            dense: true,
                                            title: Text(camera.name, style: const TextStyle(fontSize: 13)),
                                            subtitle: Text(camera.deviceId,
                                                style: const TextStyle(fontSize: 11, color: Colors.grey)),
                                            value: isSelected,
                                            onChanged: (checked) {
                                              setDialogState(() {
                                                if (checked == true) {
                                                  selectedSearchCameraIds.add(camera.deviceId);
                                                } else {
                                                  selectedSearchCameraIds.remove(camera.deviceId);
                                                }
                                              });
                                            },
                                          );
                                        },
                                      ),
                              ),
                              if (selectedSearchCameraIds.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    '${selectedSearchCameraIds.length} camera(s) selected',
                                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                                  ),
                                ),
                              const SizedBox(height: 12),
                              // Search interval and similarity threshold
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: searchIntervalController,
                                      decoration: const InputDecoration(
                                        labelText: 'Search Interval (seconds)',
                                        helperText: 'Min 30s',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: TextInputType.number,
                                      onChanged: (value) {
                                        searchIntervalSeconds = int.tryParse(value) ?? 300;
                                      },
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextField(
                                      controller: similarityThresholdController,
                                      decoration: const InputDecoration(
                                        labelText: 'Similarity Threshold',
                                        helperText: '0.0 – 1.0',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              SwitchListTile(
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                title: const Text('NOT mode'),
                                subtitle: const Text(
                                  'Fire when NO group members are found in camera recordings',
                                  style: TextStyle(fontSize: 12),
                                ),
                                value: pplMatchNegate,
                                onChanged: (v) => setDialogState(() => pplMatchNegate = v),
                              ),
                            ],
                          ),
                        ),
                      )
                    else if (triggerMode == 'search_demographic')
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.analytics, color: AppColors.error, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    'Search Demographic Configuration',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              // Multi-camera selector
                              const Text('Cameras to Search *',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 180),
                                decoration: BoxDecoration(
                                  border: Border.all(color: Colors.grey.shade400),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: availableCameras.isEmpty
                                    ? const Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Text('No cameras available',
                                            style: TextStyle(color: AppColors.warning)),
                                      )
                                    : ListView.builder(
                                        shrinkWrap: true,
                                        itemCount: availableCameras.length,
                                        itemBuilder: (context, index) {
                                          final camera = availableCameras[index];
                                          final isSelected =
                                              selectedSearchCameraIds.contains(camera.deviceId);
                                          return CheckboxListTile(
                                            dense: true,
                                            title: Text(camera.name, style: const TextStyle(fontSize: 13)),
                                            subtitle: Text(camera.deviceId,
                                                style: const TextStyle(fontSize: 11, color: Colors.grey)),
                                            value: isSelected,
                                            onChanged: (checked) {
                                              setDialogState(() {
                                                if (checked == true) {
                                                  selectedSearchCameraIds.add(camera.deviceId);
                                                } else {
                                                  selectedSearchCameraIds.remove(camera.deviceId);
                                                }
                                              });
                                            },
                                          );
                                        },
                                      ),
                              ),
                              if (selectedSearchCameraIds.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    '${selectedSearchCameraIds.length} camera(s) selected',
                                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                                  ),
                                ),
                              const SizedBox(height: 12),
                              // Search interval
                              TextField(
                                controller: searchIntervalController,
                                decoration: const InputDecoration(
                                  labelText: 'Search Interval (seconds)',
                                  helperText: 'Min 30s. How often cameras are queried for demographics.',
                                  border: OutlineInputBorder(),
                                ),
                                keyboardType: TextInputType.number,
                                onChanged: (value) {
                                  searchIntervalSeconds = int.tryParse(value) ?? 300;
                                },
                              ),
                              const SizedBox(height: 16),
                              // Demographic conditions (reuse same builder)
                              Row(
                                children: [
                                  const Icon(Icons.tune, color: AppColors.primary, size: 20),
                                  const SizedBox(width: 8),
                                  const Text(
                                    'Demographic Conditions (All must match)',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  const Spacer(),
                                  IconButton(
                                    icon: const Icon(Icons.add_circle, color: AppColors.primary),
                                    onPressed: () {
                                      setDialogState(() {
                                        demographicConditions.add(
                                          DemographicCondition(
                                            field: 'people_count',
                                            operator: 'gte',
                                            value: 1,
                                          ),
                                        );
                                      });
                                    },
                                    tooltip: 'Add condition',
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              ...List.generate(demographicConditions.length, (index) {
                                final condition = demographicConditions[index];
                                final canonicalField = _canonicalConditionField(condition.field);
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        flex: 3,
                                        child: DropdownButtonFormField<String>(
                                          value: canonicalField,
                                          decoration: const InputDecoration(
                                            labelText: 'Field',
                                            border: OutlineInputBorder(),
                                            isDense: true,
                                          ),
                                          items: const [
                                            DropdownMenuItem(value: 'people_count', child: Text('People Count')),
                                            DropdownMenuItem(value: 'percent_male', child: Text('Male %')),
                                            DropdownMenuItem(value: 'percent_female', child: Text('Female %')),
                                            DropdownMenuItem(value: 'age_threshold', child: Text('Age')),
                                          ],
                                          onChanged: (value) {
                                            setDialogState(() {
                                              final nextField = value!;
                                              demographicConditions[index] = DemographicCondition(
                                                field: nextField,
                                                operator: condition.operator,
                                                value: _normalizedConditionValueForField(
                                                  previousField: canonicalField,
                                                  nextField: nextField,
                                                  currentValue: condition.value,
                                                ),
                                              );
                                            });
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        flex: 2,
                                        child: DropdownButtonFormField<String>(
                                          value: condition.operator,
                                          decoration: const InputDecoration(
                                            labelText: 'Op',
                                            border: OutlineInputBorder(),
                                            isDense: true,
                                          ),
                                          items: const [
                                            DropdownMenuItem(value: 'gt', child: Text('>')),
                                            DropdownMenuItem(value: 'gte', child: Text('≥')),
                                            DropdownMenuItem(value: 'lt', child: Text('<')),
                                            DropdownMenuItem(value: 'lte', child: Text('≤')),
                                            DropdownMenuItem(value: 'eq', child: Text('=')),
                                          ],
                                          onChanged: (value) {
                                            setDialogState(() {
                                              demographicConditions[index] = DemographicCondition(
                                                field: canonicalField,
                                                operator: value!,
                                                value: condition.value,
                                              );
                                            });
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        flex: 2,
                                        child: TextFormField(
                                          key: ValueKey('search-demographic-condition-$index-${condition.field}'),
                                          initialValue: _formatConditionInputValue(condition.value),
                                          decoration: InputDecoration(
                                            labelText: _conditionValueLabel(canonicalField),
                                            suffixText: _conditionValueSuffix(canonicalField),
                                            border: const OutlineInputBorder(),
                                            isDense: true,
                                          ),
                                          keyboardType: TextInputType.number,
                                          inputFormatters: _isAgeThresholdField(canonicalField)
                                              ? [FilteringTextInputFormatter.digitsOnly]
                                              : _isPercentageConditionField(canonicalField)
                                                  ? [FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*$'))]
                                                  : [FilteringTextInputFormatter.digitsOnly],
                                          onChanged: (value) {
                                            var numValue = double.tryParse(value);
                                            if (numValue != null) {
                                              if (_isAgeThresholdField(canonicalField)) {
                                                numValue = numValue.clamp(1, 100);
                                              }
                                              setDialogState(() {
                                                demographicConditions[index] = DemographicCondition(
                                                  field: canonicalField,
                                                  operator: condition.operator,
                                                  value: numValue!,
                                                );
                                              });
                                            }
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      IconButton(
                                        icon: const Icon(Icons.remove_circle, color: AppColors.error),
                                        onPressed: demographicConditions.length > 1
                                            ? () {
                                                setDialogState(() {
                                                  demographicConditions.removeAt(index);
                                                });
                                              }
                                            : null,
                                        tooltip: 'Remove condition',
                                      ),
                                    ],
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                      ),
                    // VProfile Match configuration card
                    if (triggerMode == 'vprofile_match')
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.people_outline, color: AppColors.info, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    'VProfile Match Configuration',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              // Multi-camera selector
                              const Text('Cameras *', style: TextStyle(fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 140),
                                decoration: BoxDecoration(
                                  border: Border.all(color: Colors.grey.shade400),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: availableCameras.isEmpty
                                    ? const Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Text('No cameras available', style: TextStyle(color: AppColors.warning)),
                                      )
                                    : ListView.builder(
                                        shrinkWrap: true,
                                        itemCount: availableCameras.length,
                                        itemBuilder: (context, index) {
                                          final camera = availableCameras[index];
                                          final isSelected = selectedVProfileCameraIds.contains(camera.deviceId);
                                          return CheckboxListTile(
                                            dense: true,
                                            title: Text(camera.name, style: const TextStyle(fontSize: 13)),
                                            subtitle: Text(camera.deviceId, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                                            value: isSelected,
                                            onChanged: (checked) {
                                              setDialogState(() {
                                                if (checked == true) {
                                                  selectedVProfileCameraIds.add(camera.deviceId);
                                                } else {
                                                  selectedVProfileCameraIds.remove(camera.deviceId);
                                                }
                                              });
                                            },
                                          );
                                        },
                                      ),
                              ),
                              if (selectedVProfileCameraIds.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text('${selectedVProfileCameraIds.length} camera(s) selected',
                                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                                ),
                              const SizedBox(height: 12),
                              // Multi-group selector
                              const Text('Individual Groups *', style: TextStyle(fontWeight: FontWeight.w500)),
                              const SizedBox(height: 4),
                              Container(
                                constraints: const BoxConstraints(maxHeight: 140),
                                decoration: BoxDecoration(
                                  border: Border.all(color: Colors.grey.shade400),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: availableGroups.isEmpty
                                    ? const Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Text('No groups available', style: TextStyle(color: AppColors.warning)),
                                      )
                                    : ListView.builder(
                                        shrinkWrap: true,
                                        itemCount: availableGroups.length,
                                        itemBuilder: (context, index) {
                                          final group = availableGroups[index];
                                          final isSelected = selectedVProfileGroupIds.contains(group.id);
                                          return CheckboxListTile(
                                            dense: true,
                                            title: Text(group.name, style: const TextStyle(fontSize: 13)),
                                            value: isSelected,
                                            onChanged: (checked) {
                                              setDialogState(() {
                                                if (checked == true) {
                                                  selectedVProfileGroupIds.add(group.id);
                                                } else {
                                                  selectedVProfileGroupIds.remove(group.id);
                                                }
                                              });
                                            },
                                          );
                                        },
                                      ),
                              ),
                              if (selectedVProfileGroupIds.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text('${selectedVProfileGroupIds.length} group(s) selected',
                                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                                ),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: similarityThresholdController,
                                      decoration: const InputDecoration(
                                        labelText: 'Similarity Threshold (0..1)',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextField(
                                      controller: topKController,
                                      decoration: const InputDecoration(
                                        labelText: 'Top K',
                                        border: OutlineInputBorder(),
                                      ),
                                      keyboardType: TextInputType.number,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              SwitchListTile(
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                title: const Text('NOT mode'),
                                subtitle: const Text('Fire when NO group members are matched', style: TextStyle(fontSize: 12)),
                                value: pplMatchNegate,
                                onChanged: (v) => setDialogState(() => pplMatchNegate = v),
                              ),
                            ],
                          ),
                        ),
                      ),
                    const SizedBox(height: 16),
                    
                    // Camera selector (hidden for search & vprofile modes — cameras selected in their panels)
                    if (triggerMode != 'search' && triggerMode != 'search_demographic' && triggerMode != 'vprofile_match') ...[
                    const Text('Camera *', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    availableCameras.isEmpty
                        ? const Text(
                            'No cameras registered in database.',
                            style: TextStyle(color: AppColors.warning),
                          )
                        : DropdownButtonFormField<String>(
                            value: selectedCameraDeviceId,
                            isExpanded: true,
                            decoration: const InputDecoration(
                              labelText: 'Select Camera',
                              helperText: 'All registered cameras (connected or disconnected)',
                              border: OutlineInputBorder(),
                            ),
                            items: availableCameras.map((camera) {
                              return DropdownMenuItem<String>(
                                value: camera.deviceId,
                                child: Text(
                                  camera.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              );
                            }).toList(),
                            selectedItemBuilder: (context) => availableCameras
                                .map(
                                  (camera) => Text(
                                    camera.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                )
                                .toList(),
                            onChanged: (value) => setDialogState(() => selectedCameraDeviceId = value),
                          ),
                    const SizedBox(height: 16),
                    ],
                    
                    // Time span
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: TextField(
                            controller: timeSpanController,
                            decoration: const InputDecoration(
                              labelText: 'Time Span *',
                              hintText: 'e.g., Mon-Fri 09:00-17:00 or "any"',
                              helperText: 'Define when this trigger is active',
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.help_outline, color: Colors.grey),
                          onPressed: () {
                            showDialog(
                              context: context,
                              builder: (context) => AlertDialog(
                                title: const Text('Time Span Format'),
                                content: const SingleChildScrollView(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text('Examples:\n'),
                                      Text('• "any" - Always active'),
                                      Text('• "Mon-Fri 09:00-17:00" - Weekdays, 9am-5pm'),
                                      Text('• "Mon,Wed,Fri 08:00-12:00" - Specific days'),
                                      Text('• "Sat-Sun 00:00-23:59" - Weekends only'),
                                    ],
                                  ),
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.pop(context),
                                    child: const Text('Got it'),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Multi-action selector
                    InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'User Actions (Optional)',
                        helperText: 'Select one or more actions to execute',
                        border: OutlineInputBorder(),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (selectedActionUuids.isEmpty)
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Text('None selected', style: TextStyle(color: Colors.grey.shade500)),
                            ),
                          if (selectedActionUuids.isNotEmpty)
                            Wrap(
                              spacing: 6,
                              runSpacing: 4,
                              children: selectedActionUuids.map((uuid) {
                                final action = _availableActions.firstWhere(
                                  (a) => a['uuid'] == uuid,
                                  orElse: () => {'uuid': uuid, 'name': uuid.substring(0, 8)},
                                );
                                return Chip(
                                  label: Text(action['name']!, style: const TextStyle(fontSize: 12)),
                                  onDeleted: () => setDialogState(() => selectedActionUuids.remove(uuid)),
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  visualDensity: VisualDensity.compact,
                                );
                              }).toList(),
                            ),
                          const SizedBox(height: 8),
                          ..._availableActions
                              .where((a) => !selectedActionUuids.contains(a['uuid']))
                              .map((action) {
                            return InkWell(
                              onTap: () => setDialogState(() => selectedActionUuids.add(action['uuid']!)),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 4),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Icon(Icons.add_circle_outline, size: 18, color: AppColors.primary),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            action['name']!,
                                            style: const TextStyle(fontSize: 13),
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                          if ((action['type'] ?? '').isNotEmpty) ...[
                                            const SizedBox(height: 2),
                                            Text(
                                              action['type'] ?? '',
                                              style: TextStyle(
                                                color: Colors.grey.shade500,
                                                fontSize: 11,
                                              ),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Tracking duration
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: TextEditingController(text: trackingNumber.toString()),
                            decoration: const InputDecoration(labelText: 'Tracking Duration'),
                            keyboardType: TextInputType.number,
                            onChanged: (value) {
                              trackingNumber = int.tryParse(value) ?? trackingNumber;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: trackingUnit,
                            decoration: const InputDecoration(labelText: 'Unit'),
                            items: const [
                              DropdownMenuItem(value: 'seconds', child: Text('Seconds')),
                              DropdownMenuItem(value: 'minutes', child: Text('Minutes')),
                              DropdownMenuItem(value: 'hours', child: Text('Hours')),
                              DropdownMenuItem(value: 'days', child: Text('Days')),
                            ],
                            onChanged: (value) => setDialogState(() => trackingUnit = value!),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Cooldown
                    TextField(
                      controller: cooldownController,
                      decoration: const InputDecoration(
                        labelText: 'Cooldown (seconds)',
                        helperText: 'Minimum seconds between trigger firings',
                      ),
                      keyboardType: TextInputType.number,
                    ),
                    const SizedBox(height: 16),
                    
                    // Active toggle
                    SwitchListTile(
                      title: const Text('Active'),
                      value: isActive,
                      onChanged: (value) => setDialogState(() => isActive = value),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  if (embedded) {
                    onCancel?.call();
                    return;
                  }
                  Navigator.pop(context, false);
                },
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: () async {
                  // Validate
                  if (nameController.text.trim().isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Name is required')),
                    );
                    return;
                  }
                  
                  if (triggerMode != 'search' && triggerMode != 'search_demographic' && triggerMode != 'vprofile_match' && selectedCameraDeviceId == null) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Camera is required')),
                    );
                    return;
                  }
                  
                  if (triggerMode == 'demographic' && demographicConditions.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('At least one condition is required')),
                    );
                    return;
                  }

                  if (triggerMode == 'ppl_match' && selectedPplMatchGroupId == null) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Individual Group is required for PPL Match mode')),
                    );
                    return;
                  }

                  if (triggerMode == 'ppl_match') {
                    final threshold = double.tryParse(similarityThresholdController.text);
                    if (threshold == null || threshold < 0.0 || threshold > 1.0) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Similarity threshold must be between 0 and 1')),
                      );
                      return;
                    }
                    final topK = int.tryParse(topKController.text);
                    if (topK == null || topK < 1) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Top K must be at least 1')),
                      );
                      return;
                    }
                  }

                  if (triggerMode == 'search') {
                    if (selectedSearchCameraIds.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Select at least one camera for Search mode')),
                      );
                      return;
                    }
                    if (selectedPplMatchGroupId == null) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Individual Group is required for Search mode')),
                      );
                      return;
                    }
                    final interval = int.tryParse(searchIntervalController.text) ?? 0;
                    if (interval < 30) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Search interval must be at least 30 seconds')),
                      );
                      return;
                    }
                    final threshold = double.tryParse(similarityThresholdController.text);
                    if (threshold == null || threshold < 0.0 || threshold > 1.0) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Similarity threshold must be between 0 and 1')),
                      );
                      return;
                    }
                  }

                  if (triggerMode == 'search_demographic') {
                    if (selectedSearchCameraIds.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Select at least one camera for Search Demographic mode')),
                      );
                      return;
                    }
                    if (demographicConditions.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('At least one demographic condition is required')),
                      );
                      return;
                    }
                    final interval = int.tryParse(searchIntervalController.text) ?? 0;
                    if (interval < 30) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Search interval must be at least 30 seconds')),
                      );
                      return;
                    }
                  }

                  if (triggerMode == 'vprofile_match') {
                    if (selectedVProfileCameraIds.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Select at least one camera for VProfile mode')),
                      );
                      return;
                    }
                    if (selectedVProfileGroupIds.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Select at least one individual group for VProfile mode')),
                      );
                      return;
                    }
                    final threshold = double.tryParse(similarityThresholdController.text);
                    if (threshold == null || threshold < 0.0 || threshold > 1.0) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Similarity threshold must be between 0 and 1')),
                      );
                      return;
                    }
                    final topK = int.tryParse(topKController.text);
                    if (topK == null || topK < 1) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Top K must be at least 1')),
                      );
                      return;
                    }
                  }
                  
                  if (embedded) {
                    await doSave();
                    onSaved?.call();
                    return;
                  }
                  Navigator.pop(context, true);
                },
                child: Text(isEditing ? 'Update' : 'Create'),
              ),
            ],
          );
        },
    );

    if (embedded) {
      return editor;
    }

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => editor,
    );

    if (result != true) return null;

    await doSave();

    // Dispose controllers
    nameController.dispose();
    descriptionController.dispose();
    timeSpanController.dispose();
    cooldownController.dispose();
    similarityThresholdController.dispose();
    topKController.dispose();
    searchIntervalController.dispose();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }
}
