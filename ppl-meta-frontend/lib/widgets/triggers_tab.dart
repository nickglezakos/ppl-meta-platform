import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/trigger_model.dart';
import '../services/trigger_service.dart';
import '../core/models/camera.dart';
import '../core/providers/camera_providers.dart';
import '../core/api/api_client.dart';
import '../services/individual_groups_api_client.dart';
import '../models/individual_group_models.dart';

class TriggersTab extends ConsumerStatefulWidget {
  const TriggersTab({super.key});

  @override
  ConsumerState<TriggersTab> createState() => _TriggersTabState();
}

class _TriggersTabState extends ConsumerState<TriggersTab> {
  final TriggerService _triggerService = TriggerService();
  final Map<String, String> _groupNameById = {};
  
  bool _isLoading = true;
  String? _errorMessage;
  List<TriggerModel> _triggers = [];
  List<Map<String, String>> _availableActions = [];
  
  int _currentPage = 1;
  int _totalPages = 1;
  bool? _filterIsActive;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTriggers();
      _loadAvailableActions();
      _loadAvailableGroups();
    });
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
      debugPrint('🔍 [DEBUG] Request path: /api/v1/user-actions/');
      debugPrint('🔍 [DEBUG] Full URL will be: ${apiClient.dio.options.baseUrl}/api/v1/user-actions/');
      
      final response = await apiClient.get(
        '/api/v1/user-actions/',
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
        data: {'action_uuid': actionUuid},
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

  Future<void> _toggleTrigger(TriggerModel trigger) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      
      final response = await apiClient.put(
        '/api/v1/triggers/${trigger.uuid}',
        data: {'is_active': !trigger.isActive},
      );
      
      if (response.statusCode == 200) {
        if (!mounted) return;
        _loadTriggers();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Trigger ${trigger.isActive ? 'deactivated' : 'activated'}')),
        );
      } else {
        throw Exception('Failed to toggle trigger');
      }
    } catch (e) {
      debugPrint('❌ Error toggling trigger: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error toggling trigger: $e')),
      );
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
            style: TextButton.styleFrom(foregroundColor: Colors.red),
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
    if (trigger.triggerMode != 'ppl_match') {
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
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Text(
                  'Triggers',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(width: 16),
                ElevatedButton.icon(
                  onPressed: () => _showCreateEditDialog(),
                  icon: const Icon(Icons.add),
                  label: const Text('Create Trigger'),
                ),
                const Spacer(),
                // Filter dropdown
                DropdownButton<bool?>(
                  value: _filterIsActive,
                  hint: const Text('All Statuses'),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Statuses')),
                    DropdownMenuItem(value: true, child: Text('Active Only')),
                    DropdownMenuItem(value: false, child: Text('Inactive Only')),
                  ],
                  onChanged: (value) {
                    setState(() => _filterIsActive = value);
                    _loadTriggers();
                  },
                ),
                const SizedBox(width: 16),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () async {
                    await _loadTriggers();
                    await _loadAvailableGroups();
                  },
                  tooltip: 'Refresh',
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _errorMessage != null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text('Error: $_errorMessage', style: const TextStyle(color: Colors.red)),
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
                          : _buildDataTable(),
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
      ),
    );
  }

  Widget _buildDataTable() {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: Colors.grey.shade900,
            border: Border.all(color: Colors.grey.shade700),
            borderRadius: BorderRadius.circular(8),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: constraints.maxWidth),
              child: DataTable(
                columnSpacing: 16,
                horizontalMargin: 16,
                headingRowColor: WidgetStatePropertyAll(Colors.grey.shade800),
                dataRowColor: WidgetStatePropertyAll(Colors.grey.shade900),
                columns: const [
                  DataColumn(label: Text('Name', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Mode', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Conditions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Latest Match', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Camera', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Time Span', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Tracking', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Action', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Actions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                ],
                rows: _triggers.map((trigger) {
                  final isPplMatch = trigger.triggerMode == 'ppl_match';
                  final modeLabel = isPplMatch ? 'PPL Match' : 'Demographic';
                  final groupId = trigger.pplMatchGroupId;
                  final groupName = groupId == null ? null : _groupNameById[groupId];
                  final conditionsLabel = isPplMatch
                      ? 'Group: ${groupName ?? groupId ?? 'Not set'}'
                      : trigger.conditionsDisplay;
                  final latestMatchSummary = _latestMatchSummary(trigger);
                  final latestMatchTime = _latestMatchTime(trigger);
                  return DataRow(cells: [
                    DataCell(Text(trigger.name ?? 'Unnamed', style: const TextStyle(color: Colors.white70))),
                    DataCell(Text(modeLabel, style: const TextStyle(color: Colors.white70))),
                    DataCell(
                      Text(
                        conditionsLabel,
                        style: const TextStyle(color: Colors.white70),
                      ),
                    ),
                    DataCell(
                      Text(
                        latestMatchTime.isEmpty
                            ? latestMatchSummary
                            : '$latestMatchSummary\n$latestMatchTime',
                        style: const TextStyle(color: Colors.white70),
                      ),
                    ),
                    DataCell(Text(trigger.cameraName ?? trigger.cameraDeviceId, style: const TextStyle(color: Colors.white70))),
                    DataCell(Text(trigger.timeSpan, style: const TextStyle(color: Colors.white70))),
                    DataCell(Text(trigger.trackingDuration, style: const TextStyle(color: Colors.white70))),
                    DataCell(
                      Container(
                        constraints: const BoxConstraints(minWidth: 150),
                        child: DropdownButtonFormField<String?>(
                          value: _availableActions.any((a) => a['uuid'] == trigger.actionUuid) 
                              ? trigger.actionUuid 
                              : null, // If action doesn't exist, set to null
                          decoration: const InputDecoration(
                            isDense: true,
                            contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                            border: OutlineInputBorder(),
                          ),
                          style: const TextStyle(color: Colors.white70, fontSize: 14),
                          dropdownColor: Colors.grey.shade800,
                          items: [
                            const DropdownMenuItem(
                              value: null,
                              child: Text('None', style: TextStyle(color: Colors.white70)),
                            ),
                            // Deduplicate actions by UUID to prevent dropdown errors
                            ...{
                              for (var action in _availableActions)
                                action['uuid']!: action
                            }.values.map((action) {
                              return DropdownMenuItem(
                                value: action['uuid'],
                                child: Text(
                                  action['name']!,
                                  style: const TextStyle(color: Colors.white70),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              );
                            }),
                          ],
                          onChanged: (newValue) => _updateTriggerAction(trigger, newValue),
                        ),
                      ),
                    ),
                    DataCell(
                      InkWell(
                        onTap: () => _toggleTrigger(trigger),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: trigger.isActive
                                ? Colors.green.shade900
                                : Colors.red.shade900,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            trigger.isActive ? 'Active' : 'Inactive',
                            style: TextStyle(
                              color: trigger.isActive
                                  ? Colors.green.shade300
                                  : Colors.red.shade300,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ),
                    DataCell(
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit, color: Colors.blue, size: 20),
                            onPressed: () => _showCreateEditDialog(trigger: trigger),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete, color: Colors.red, size: 20),
                            onPressed: () => _deleteTrigger(trigger),
                          ),
                        ],
                      ),
                    ),
                  ]);
                }).toList(),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _showCreateEditDialog({TriggerModel? trigger}) async {
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
    if (!mounted) return;
    
    String? selectedCameraDeviceId = trigger?.cameraDeviceId;
    String? selectedActionUuid = trigger?.actionUuid;
    
    // Validate that selectedActionUuid exists in availableActions
    if (selectedActionUuid != null && !_availableActions.any((a) => a['uuid'] == selectedActionUuid)) {
      debugPrint('⚠️ Selected action $selectedActionUuid not found in available actions, setting to null');
      selectedActionUuid = null;
    }
    
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
    
    // Demographic conditions
    List<DemographicCondition> demographicConditions = trigger?.demographicConditions ?? [
      DemographicCondition(field: 'people_count', operator: 'gte', value: 1),
    ];
    
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

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
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
                      decoration: const InputDecoration(
                        labelText: 'Trigger Mode',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'demographic',
                          child: Text('Demographic'),
                        ),
                        DropdownMenuItem(
                          value: 'ppl_match',
                          child: Text('PPL Match'),
                        ),
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
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(Icons.tune, color: Colors.blue, size: 20),
                                  const SizedBox(width: 8),
                                  const Text(
                                    'Demographic Conditions (All must match)',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  const Spacer(),
                                  IconButton(
                                    icon: const Icon(Icons.add_circle, color: Colors.blue),
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
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        flex: 3,
                                        child: DropdownButtonFormField<String>(
                                          value: condition.field,
                                          decoration: const InputDecoration(
                                            labelText: 'Field',
                                            border: OutlineInputBorder(),
                                            isDense: true,
                                          ),
                                          items: const [
                                            DropdownMenuItem(value: 'people_count', child: Text('People Count')),
                                            DropdownMenuItem(value: 'percent_male', child: Text('Male %')),
                                            DropdownMenuItem(value: 'percent_female', child: Text('Female %')),
                                            DropdownMenuItem(value: 'percent_age_0_12', child: Text('Age 0-12 %')),
                                            DropdownMenuItem(value: 'percent_age_13_17', child: Text('Age 13-17 %')),
                                            DropdownMenuItem(value: 'percent_age_18_24', child: Text('Age 18-24 %')),
                                            DropdownMenuItem(value: 'percent_age_25_34', child: Text('Age 25-34 %')),
                                            DropdownMenuItem(value: 'percent_age_35_44', child: Text('Age 35-44 %')),
                                            DropdownMenuItem(value: 'percent_age_45_54', child: Text('Age 45-54 %')),
                                            DropdownMenuItem(value: 'percent_age_55_64', child: Text('Age 55-64 %')),
                                            DropdownMenuItem(value: 'percent_age_65_plus', child: Text('Age 65+ %')),
                                          ],
                                          onChanged: (value) {
                                            setDialogState(() {
                                              demographicConditions[index] = DemographicCondition(
                                                field: value!,
                                                operator: condition.operator,
                                                value: condition.value,
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
                                                field: condition.field,
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
                                        child: TextField(
                                          controller: TextEditingController(text: condition.value.toString()),
                                          decoration: const InputDecoration(
                                            labelText: 'Value',
                                            border: OutlineInputBorder(),
                                            isDense: true,
                                          ),
                                          keyboardType: TextInputType.number,
                                          onChanged: (value) {
                                            final numValue = double.tryParse(value);
                                            if (numValue != null) {
                                              setDialogState(() {
                                                demographicConditions[index] = DemographicCondition(
                                                  field: condition.field,
                                                  operator: condition.operator,
                                                  value: numValue,
                                                );
                                              });
                                            }
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      IconButton(
                                        icon: const Icon(Icons.remove_circle, color: Colors.red),
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
                      )
                    else
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.psychology, color: Colors.purple, size: 20),
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
                            ],
                          ),
                        ),
                      ),
                    const SizedBox(height: 16),
                    
                    // Camera selector
                    const Text('Camera *', style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    availableCameras.isEmpty
                        ? const Text(
                            'No cameras registered in database.',
                            style: TextStyle(color: Colors.orange),
                          )
                        : DropdownButtonFormField<String>(
                            value: selectedCameraDeviceId,
                            decoration: const InputDecoration(
                              labelText: 'Select Camera',
                              helperText: 'All registered cameras (connected or disconnected)',
                              border: OutlineInputBorder(),
                            ),
                            items: availableCameras.map((camera) {
                              return DropdownMenuItem<String>(
                                value: camera.deviceId,
                                child: Text(camera.name),
                              );
                            }).toList(),
                            onChanged: (value) => setDialogState(() => selectedCameraDeviceId = value),
                          ),
                    const SizedBox(height: 16),
                    
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
                    
                    // Action selector
                    DropdownButtonFormField<String?>(
                      value: selectedActionUuid,
                      decoration: const InputDecoration(
                        labelText: 'User Action (Optional)',
                        helperText: 'Link to a user-defined action',
                      ),
                      items: [
                        const DropdownMenuItem(value: null, child: Text('None')),
                        ..._availableActions.map((action) {
                          return DropdownMenuItem(
                            value: action['uuid'],
                            child: Text(action['name']!),
                          );
                        }),
                      ],
                      onChanged: (value) => setDialogState(() => selectedActionUuid = value),
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
                onPressed: () => Navigator.pop(context, false),
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
                  
                  if (selectedCameraDeviceId == null) {
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
                  
                  Navigator.pop(context, true);
                },
                child: Text(isEditing ? 'Update' : 'Create'),
              ),
            ],
          );
        },
      ),
    );

    if (result != true) return;

    // Create/update the trigger using authenticated ApiClient
    try {
      final apiClient = ref.read(apiClientProvider);

      final cameraName = availableCameras.firstWhere(
        (c) => c.deviceId == selectedCameraDeviceId,
        orElse: () => Camera(
          id: '',
          deviceId: selectedCameraDeviceId!,
          name: selectedCameraDeviceId!,
          status: 'unknown',
          resolution: '0x0',
          type: CameraType.usb,
          supportsRecording: false,
        ),
      ).name;

      final requestBody = TriggerCreateRequest(
        name: nameController.text.trim(),
        description: descriptionController.text.trim().isEmpty ? null : descriptionController.text.trim(),
        demographicConditions: triggerMode == 'demographic' ? demographicConditions : const [],
        timeSpan: timeSpanController.text.trim(),
        cameraDeviceId: selectedCameraDeviceId!,
        cameraName: cameraName,
        actionUuid: selectedActionUuid,
        trackingDuration: '$trackingNumber $trackingUnit',
        cooldownSeconds: int.tryParse(cooldownController.text) ?? 60,
        isActive: isActive,
        triggerMode: triggerMode,
        pplMatchGroupId: triggerMode == 'ppl_match' ? selectedPplMatchGroupId : null,
        pplMatchSimilarityThreshold: triggerMode == 'ppl_match'
          ? (double.tryParse(similarityThresholdController.text) ?? 0.75)
          : null,
        pplMatchTopK: triggerMode == 'ppl_match'
          ? (int.tryParse(topKController.text) ?? 1)
          : null,
      );

      final endpoint = isEditing
          ? '/api/v1/triggers/${trigger.uuid}'
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

    // Dispose controllers
    nameController.dispose();
    descriptionController.dispose();
    timeSpanController.dispose();
    cooldownController.dispose();
    similarityThresholdController.dispose();
    topKController.dispose();
  }

  @override
  void dispose() {
    super.dispose();
  }
}
