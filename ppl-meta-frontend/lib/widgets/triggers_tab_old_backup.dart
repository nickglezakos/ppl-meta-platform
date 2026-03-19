import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../models/trigger_model.dart';
import '../models/signage_models.dart';
import '../services/trigger_service.dart';
import '../core/providers/auth_provider.dart';
import '../core/services/auth_service.dart';
import 'demographic_trigger_config.dart';

// Simple camera info model for dropdown
class SimpleCameraInfo {
  final String deviceId;
  final String name;

  SimpleCameraInfo({required this.deviceId, required this.name});

  factory SimpleCameraInfo.fromJson(Map<String, dynamic> json) {
    return SimpleCameraInfo(
      deviceId: json['device_id'] as String,
      name: json['name'] as String? ?? json['device_id'] as String,
    );
  }
}

class TriggersTab extends ConsumerStatefulWidget {
  const TriggersTab({Key? key}) : super(key: key);

  @override
  ConsumerState<TriggersTab> createState() => _TriggersTabState();
}

class _TriggersTabState extends ConsumerState<TriggersTab> {
  final TriggerService _triggerService = TriggerService();
  
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
    // Load triggers and actions after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTriggers();
      _loadAvailableActions();
    });
  }
  
  Future<void> _loadAvailableActions() async {
    try {
      final authToken = await _getAuthToken();
      if (authToken == null) return;
      
      final response = await http.get(
        Uri.parse('http://localhost:8000/api/v1/user-actions/?page=1&page_size=100'),
        headers: {'Authorization': 'Bearer $authToken'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _availableActions = (data['actions'] as List)
              .map((action) => {
                    'uuid': action['uuid'] as String,
                    'name': action['name'] as String,
                  })
              .toList();
        });
        print('✅ Loaded ${_availableActions.length} available actions');
      }
    } catch (e) {
      print('❌ Error loading available actions: $e');
    }
  }
  
  /// Fetch cameras from Camera service API
  /// Uses authServiceProvider to get token, same as MultiCameraPage
  Future<List<SimpleCameraInfo>> _fetchCameras() async {
    try {
      print('🔐 Fetching cameras with authentication...');
      
      // Get auth token using the same method as MultiCameraPage
      final authToken = await _getAuthToken();
      
      if (authToken == null || authToken.isEmpty) {
        print('⚠️ No auth token available - cannot fetch cameras');
        return [];
      }
      
      final headers = <String, String>{
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer $authToken',
      };

      print('🔍 Fetching cameras from camera service (port 8005)...');

      // Use camera service directly (port 8005)
      final response = await http.get(
        Uri.parse('http://localhost:8005/api/v1/cameras'),
        headers: headers,
      );

      print('📡 Camera API response: ${response.statusCode}');

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        print('✅ Fetched ${data.length} cameras');
        return data.map((json) => SimpleCameraInfo.fromJson(json)).toList();
      } else if (response.statusCode == 403) {
        // If 403, return empty list with a warning - user can manually enter camera ID
        print('⚠️ Camera API requires authentication - returning empty list');
        print('   User can manually enter camera_device_id if needed');
        return [];
      } else {
        print('❌ Camera API error: ${response.statusCode} - ${response.body}');
        throw Exception('Failed to load cameras: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error fetching cameras: $e');
      return [];
    }
  }

  Future<void> _loadTriggers() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Get auth token from secure storage
      final authToken = await _getAuthToken();
      if (authToken != null) {
        _triggerService.setAuthToken(authToken);
      }

      final response = await _triggerService.fetchTriggers(
        page: _currentPage,
        pageSize: 50,
        isActive: _filterIsActive,
      );
      
      print('✅ Triggers loaded: ${response.triggers.length} triggers, total pages: ${response.totalPages}');
      
      setState(() {
        _triggers = response.triggers;
        _totalPages = response.totalPages;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading triggers: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  /// Get auth token using the same method as other camera screens
  Future<String?> _getAuthToken() async {
    try {
      print('   _getAuthToken: Using authServiceProvider like MultiCameraPage...');
      final authService = ref.read(authServiceProvider);
      final token = await authService.getToken();
      print('   _getAuthToken: Token = ${token != null ? "${token.substring(0, token.length < 20 ? token.length : 20)}..." : "NULL"}');
      return token;
    } catch (e) {
      print('   _getAuthToken: Error getting auth token: $e');
      return null;
    }
  }

  Future<void> _updateTriggerAction(TriggerModel trigger, String? actionUuid) async {
    try {
      final authToken = await _getAuthToken();
      if (authToken == null) {
        throw Exception('Not authenticated');
      }
      
      final response = await http.put(
        Uri.parse('http://localhost:8000/api/v1/triggers/${trigger.uuid}'),
        headers: {
          'Authorization': 'Bearer $authToken',
          'Content-Type': 'application/json',
        },
        body: json.encode({'action_uuid': actionUuid}),
      );
      
      if (response.statusCode == 200) {
        _loadTriggers(); // Reload to get updated state
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                actionUuid == null 
                    ? 'Action unlinked from trigger' 
                    : 'Action linked to trigger',
              ),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        throw Exception('Failed to update trigger: ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error updating trigger action: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _toggleTrigger(TriggerModel trigger) async {
    try {
      await _triggerService.toggleTrigger(trigger.uuid);
      _loadTriggers(); // Reload to get updated state
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Trigger ${trigger.isActive ? "deactivated" : "activated"}',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error toggling trigger: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _deleteTrigger(TriggerModel trigger) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Trigger'),
        content: Text(
          'Are you sure you want to delete this trigger?\n${trigger.name ?? trigger.uuid}',
        ),
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

    if (confirmed == true) {
      try {
        await _triggerService.deleteTrigger(trigger.uuid);
        _loadTriggers();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Trigger deleted successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error deleting trigger: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with filter
          Row(
            children: [
              const Icon(Icons.notifications_active, color: Colors.orange),
              const SizedBox(width: 8),
              Text(
                'Triggers',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              // Filter dropdown
              DropdownButton<bool?>(
                value: _filterIsActive,
                dropdownColor: Colors.grey.shade900,
                items: const [
                  DropdownMenuItem(value: null, child: Text('All')),
                  DropdownMenuItem(value: true, child: Text('Active')),
                  DropdownMenuItem(value: false, child: Text('Inactive')),
                ],
                onChanged: (value) {
                  setState(() {
                    _filterIsActive = value;
                    _currentPage = 1;
                  });
                  _loadTriggers();
                },
              ),
              const SizedBox(width: 16),
              // Add button
              ElevatedButton.icon(
                onPressed: () => _showCreateEditDialog(),
                icon: const Icon(Icons.add),
                label: const Text('Create Trigger'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Loading state
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            ),
          
          // Error state
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.red.shade900.withOpacity(0.3),
                border: Border.all(color: Colors.red),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                  TextButton(
                    onPressed: _loadTriggers,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          
          // Empty state
          if (!_isLoading && _errorMessage == null && _triggers.isEmpty)
            Container(
              padding: const EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Column(
                children: [
                  Icon(
                    Icons.notifications_off,
                    size: 64,
                    color: Colors.grey.shade600,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No triggers found',
                    style: TextStyle(
                      fontSize: 18,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Create your first trigger to get started',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),
          
          // Data table (responsive)
          if (!_isLoading && _errorMessage == null && _triggers.isNotEmpty)
            LayoutBuilder(
              builder: (context, constraints) {
                final isWideScreen = constraints.maxWidth > 900;
                
                if (isWideScreen) {
                  return _buildDataTable();
                } else {
                  return _buildCardList();
                }
              },
            ),
          
          // Pagination
          if (!_isLoading && _errorMessage == null && _totalPages > 1)
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
  }

  Future<void> _showCreateEditDialog({TriggerModel? trigger}) async {
    final isEditing = trigger != null;
    
    // Load cameras BEFORE showing the dialog
    print('🔄 Pre-loading cameras before dialog opens...');
    List<SimpleCameraInfo> availableCameras = await _fetchCameras();
    
    // Deduplicate cameras by deviceId
    final Map<String, SimpleCameraInfo> cameraMap = {};
    for (var camera in availableCameras) {
      cameraMap[camera.deviceId] = camera;
    }
    availableCameras = cameraMap.values.toList();
    print('📦 Pre-loaded ${availableCameras.length} cameras');
    
    // Check if editing trigger has a camera that no longer exists
    String? missingCameraInfo;
    if (isEditing && trigger.cameraDeviceId != null && !cameraMap.containsKey(trigger.cameraDeviceId)) {
      missingCameraInfo = '⚠️ Camera "${trigger.cameraName ?? trigger.cameraDeviceId}" is no longer available in the system. Please select a new camera.';
      print(missingCameraInfo);
    }
    
    // Load signage devices and playlists for demographic triggers
    print('🔄 Pre-loading signage devices and playlists...');
    List<DatabaseSignageDevice> availableDevices = [];
    List<VideoList> availablePlaylists = [];
    try {
      final authToken = await _getAuthToken();
      if (authToken != null) {
        _triggerService.setAuthToken(authToken);
        availableDevices = await _triggerService.fetchSignageDevices();
        availablePlaylists = await _triggerService.fetchSignagePlaylists();
        print('✅ Loaded ${availableDevices.length} devices and ${availablePlaylists.length} playlists');
      }
    } catch (e) {
      print('❌ Error loading signage data: $e');
    }
    
    // Load available user actions
    print('🔄 Pre-loading user actions...');
    List<Map<String, String>> availableActions = [];
    try {
      final authToken = await _getAuthToken();
      if (authToken != null) {
        final response = await http.get(
          Uri.parse('http://localhost:8000/api/v1/user-actions/?page=1&page_size=100'),
          headers: {'Authorization': 'Bearer $authToken'},
        );
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          availableActions = (data['actions'] as List)
              .map((action) => {
                    'uuid': action['uuid'] as String,
                    'name': action['name'] as String,
                  })
              .toList();
          print('✅ Loaded ${availableActions.length} user actions');
        }
      }
    } catch (e) {
      print('❌ Error loading user actions: $e');
    }
    
    String? selectedCameraDeviceId = trigger?.cameraDeviceId;
    
    // Validate that selectedCameraDeviceId exists in availableCameras
    // If not, set to null so user must select a new camera
    if (selectedCameraDeviceId != null && !availableCameras.any((c) => c.deviceId == selectedCameraDeviceId)) {
      print('⚠️ Selected camera $selectedCameraDeviceId not found in available cameras, setting to null');
      selectedCameraDeviceId = null;
    }
    
    String? selectedActionUuid = trigger?.actionUuid;
    
    // Validate that selectedActionUuid exists in availableActions
    if (selectedActionUuid != null && !availableActions.any((a) => a['uuid'] == selectedActionUuid)) {
      print('⚠️ Selected action $selectedActionUuid not found in available actions, setting to null');
      selectedActionUuid = null;
    }
    
    // Form controllers
    final nameController = TextEditingController(text: trigger?.name);
    final descriptionController = TextEditingController(text: trigger?.description);
    final personCountValueController = TextEditingController(text: trigger?.personCountValue);
    final ageRangeValueController = TextEditingController(text: trigger?.ageRangeValue);
    final timeSpanController = TextEditingController(text: trigger?.timeSpan ?? 'any');
    
    // Form state
    String personCountOperator = trigger?.personCountOperator ?? 'more_than';
    String? ageRangeOperator = trigger?.ageRangeOperator;
    String genderFilter = trigger?.genderFilter ?? 'any';
    
    // Demographic trigger state
    bool enableDemographicConditions = trigger?.enableDemographicConditions ?? false;
    List<Map<String, dynamic>> demographicConditions = 
        trigger?.demographicConditions != null 
            ? List<Map<String, dynamic>>.from(trigger!.demographicConditions!)
            : [];
    List<String> signageDeviceIds = trigger?.signageDeviceIds ?? [];
    String? signagePlaylistId = trigger?.signagePlaylistId;
    String signageTransitionMode = trigger?.signageTransitionMode ?? 'immediate';
    int signageFadeDurationMs = trigger?.signageFadeDurationMs ?? 2000;
    int cooldownSeconds = trigger?.cooldownSeconds ?? 60;
    
    // Parse tracking duration into number and unit
    int trackingNumber = 10;
    String trackingUnit = 'minutes';
    if (trigger?.trackingDuration != null) {
      final parts = trigger!.trackingDuration.split(' ');
      if (parts.length >= 2) {
        trackingNumber = int.tryParse(parts[0]) ?? 10;
        trackingUnit = parts[1]; // 'second', 'seconds', 'minute', 'minutes', etc.
        // Normalize to plural form
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
              width: 500,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Show warning if camera no longer exists
                  if (missingCameraInfo != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.orange.shade900.withOpacity(0.3),
                        border: Border.all(color: Colors.orange.shade700),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning, color: Colors.orange, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              missingCameraInfo,
                              style: const TextStyle(color: Colors.orange, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
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
                  const SizedBox(height: 16),
                  const Text('Person Count Condition', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: personCountOperator,
                          decoration: const InputDecoration(labelText: 'Operator'),
                          items: const [
                            DropdownMenuItem(value: 'less_than', child: Text('Less than')),
                            DropdownMenuItem(value: 'more_than', child: Text('More than')),
                            DropdownMenuItem(value: 'equals', child: Text('Equals')),
                            DropdownMenuItem(value: 'between', child: Text('Between')),
                          ],
                          onChanged: (value) => setDialogState(() => personCountOperator = value!),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: TextField(
                          controller: personCountValueController,
                          decoration: InputDecoration(
                            labelText: personCountOperator == 'between' ? 'Range (e.g., 5-15)' : 'Value',
                          ),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Age Range Filter (Optional)', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String?>(
                          value: ageRangeOperator,
                          decoration: const InputDecoration(labelText: 'Operator'),
                          items: const [
                            DropdownMenuItem(value: null, child: Text('None')),
                            DropdownMenuItem(value: 'less_than', child: Text('Less than')),
                            DropdownMenuItem(value: 'more_than', child: Text('More than')),
                            DropdownMenuItem(value: 'between', child: Text('Between')),
                            DropdownMenuItem(value: 'any', child: Text('Any')),
                          ],
                          onChanged: (value) => setDialogState(() => ageRangeOperator = value),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: TextField(
                          controller: ageRangeValueController,
                          decoration: InputDecoration(
                            labelText: ageRangeOperator == 'between' ? 'Range (e.g., 18-65)' : 'Age',
                            enabled: ageRangeOperator != null && ageRangeOperator != 'any',
                          ),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: genderFilter,
                    decoration: const InputDecoration(labelText: 'Gender Filter'),
                    items: const [
                      DropdownMenuItem(value: 'any', child: Text('Any')),
                      DropdownMenuItem(value: 'male', child: Text('Male')),
                      DropdownMenuItem(value: 'female', child: Text('Female')),
                    ],
                    onChanged: (value) => setDialogState(() => genderFilter = value!),
                  ),
                  const SizedBox(height: 16),
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
                            helperMaxLines: 2,
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
                                    Text(
                                      'The time span defines when this trigger is active.\n',
                                      style: TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    Text('Examples:\n'),
                                    Text('• "any" - Always active'),
                                    Text('• "Mon-Fri 09:00-17:00" - Weekdays, 9am-5pm'),
                                    Text('• "Mon,Wed,Fri 08:00-12:00" - Specific days'),
                                    Text('• "Sat-Sun 00:00-23:59" - Weekends only'),
                                    Text('• "Mon-Sun 18:00-06:00" - Every night'),
                                    SizedBox(height: 12),
                                    Text(
                                      'Format:\n',
                                      style: TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    Text('• Days: Mon, Tue, Wed, Thu, Fri, Sat, Sun'),
                                    Text('• Use dash (-) for ranges: Mon-Fri'),
                                    Text('• Use comma (,) for multiple: Mon,Wed,Fri'),
                                    Text('• Time: 24-hour format HH:MM'),
                                    Text('• Separate days and time with space'),
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
                        tooltip: 'Time span format help',
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('Camera *', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  availableCameras.isEmpty
                          ? const Text(
                              'No cameras available. Please connect cameras first.',
                              style: TextStyle(color: Colors.red),
                            )
                          : DropdownButtonFormField<String>(
                              value: selectedCameraDeviceId,
                              decoration: const InputDecoration(
                                labelText: 'Select Camera',
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
                  DropdownButtonFormField<String?>(
                    value: selectedActionUuid,
                    decoration: const InputDecoration(
                      labelText: 'User Action (Optional)',
                      helperText: 'Link to a user-defined action',
                    ),
                    items: [
                      const DropdownMenuItem(value: null, child: Text('None (use default action)')),
                      ...availableActions.map((action) {
                        return DropdownMenuItem(
                          value: action['uuid'],
                          child: Text(action['name']!),
                        );
                      }).toList(),
                    ],
                    onChanged: (value) => setDialogState(() => selectedActionUuid = value),
                  ),
                  const SizedBox(height: 16),
                  const Text('Tracking Duration *', style: TextStyle(fontWeight: FontWeight.bold)),
                  const Text('Time window for MVR search results', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextField(
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Number',
                            border: OutlineInputBorder(),
                          ),
                          controller: TextEditingController(text: trackingNumber.toString())
                            ..selection = TextSelection.fromPosition(
                              TextPosition(offset: trackingNumber.toString().length),
                            ),
                          onChanged: (value) => setDialogState(() {
                            trackingNumber = int.tryParse(value) ?? 10;
                          }),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        flex: 3,
                        child: DropdownButtonFormField<String>(
                          value: trackingUnit,
                          decoration: const InputDecoration(
                            labelText: 'Unit',
                            border: OutlineInputBorder(),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'seconds', child: Text('Seconds')),
                            DropdownMenuItem(value: 'minutes', child: Text('Minutes')),
                            DropdownMenuItem(value: 'hours', child: Text('Hours')),
                            DropdownMenuItem(value: 'days', child: Text('Days')),
                            DropdownMenuItem(value: 'months', child: Text('Months')),
                          ],
                          onChanged: (value) => setDialogState(() => trackingUnit = value!),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SwitchListTile(
                    title: const Text('Active'),
                    value: isActive,
                    onChanged: (value) => setDialogState(() => isActive = value),
                  ),
                  const SizedBox(height: 24),
                  const Divider(),
                  const SizedBox(height: 16),
                  
                  // Demographic trigger configuration
                  DemographicTriggerConfig(
                    enableDemographic: enableDemographicConditions,
                    demographicConditions: demographicConditions,
                    selectedDeviceIds: signageDeviceIds,
                    selectedPlaylistId: signagePlaylistId,
                    transitionMode: signageTransitionMode,
                    fadeDurationMs: signageFadeDurationMs,
                    cooldownSeconds: cooldownSeconds,
                    availableDevices: availableDevices,
                    availablePlaylists: availablePlaylists,
                    onEnableChanged: (value) => setDialogState(() => enableDemographicConditions = value),
                    onConditionsChanged: (value) => setDialogState(() => demographicConditions = value),
                    onDevicesChanged: (value) => setDialogState(() => signageDeviceIds = value),
                    onPlaylistChanged: (value) => setDialogState(() => signagePlaylistId = value),
                    onTransitionModeChanged: (value) => setDialogState(() => signageTransitionMode = value),
                    onFadeDurationChanged: (value) => setDialogState(() => signageFadeDurationMs = value),
                    onCooldownChanged: (value) => setDialogState(() => cooldownSeconds = value),
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
              onPressed: () => Navigator.pop(context, true),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange,
                foregroundColor: Colors.white,
              ),
              child: Text(isEditing ? 'Update' : 'Create'),
            ),
          ],
        );
        },
      ),
    );

    if (result == true) {
      // Validate required fields
      if (nameController.text.isEmpty || 
          personCountValueController.text.isEmpty ||
          selectedCameraDeviceId == null || selectedCameraDeviceId!.isEmpty ||
          timeSpanController.text.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Please fill in all required fields'),
              backgroundColor: Colors.red,
            ),
          );
        }
        return;
      }
      
      // Find selected camera to get its name
      final selectedCamera = availableCameras.firstWhere(
        (cam) => cam.deviceId == selectedCameraDeviceId,
        orElse: () => SimpleCameraInfo(deviceId: selectedCameraDeviceId!, name: selectedCameraDeviceId!),
      );

      try {
        // Combine tracking number and unit into duration string
        final trackingDuration = trackingNumber == 1 
            ? '$trackingNumber ${trackingUnit.replaceAll('s', '')}' // '1 minute', '1 hour', etc.
            : '$trackingNumber $trackingUnit'; // '10 minutes', '2 hours', etc.
        
        final request = TriggerCreateRequest(
          name: nameController.text,
          description: descriptionController.text.isEmpty ? null : descriptionController.text,
          personCountOperator: personCountOperator,
          personCountValue: personCountValueController.text,
          ageRangeOperator: ageRangeOperator,
          ageRangeValue: ageRangeValueController.text.isEmpty ? null : ageRangeValueController.text,
          genderFilter: genderFilter,
          timeSpan: timeSpanController.text,
          cameraDeviceId: selectedCameraDeviceId!,
          cameraName: selectedCamera.name,
          action: 'alert', // Default action
          actionUuid: selectedActionUuid,
          trackingDuration: trackingDuration,
          isActive: isActive,
          // Demographic trigger fields
          enableDemographicConditions: enableDemographicConditions,
          demographicConditions: enableDemographicConditions && demographicConditions.isNotEmpty 
              ? demographicConditions 
              : null,
          signageDeviceIds: enableDemographicConditions && signageDeviceIds.isNotEmpty 
              ? signageDeviceIds 
              : null,
          signagePlaylistId: enableDemographicConditions ? signagePlaylistId : null,
          signageTransitionMode: signageTransitionMode,
          signageFadeDurationMs: signageFadeDurationMs,
          cooldownSeconds: cooldownSeconds,
        );

        if (isEditing) {
          await _triggerService.updateTrigger(trigger.uuid, request);
        } else {
          await _triggerService.createTrigger(request);
        }

        await _loadTriggers();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Trigger ${isEditing ? "updated" : "created"} successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error ${isEditing ? "updating" : "creating"} trigger: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }

    // Dispose controllers
    nameController.dispose();
    descriptionController.dispose();
    personCountValueController.dispose();
    ageRangeValueController.dispose();
    timeSpanController.dispose();
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
                headingRowColor: MaterialStateProperty.all(Colors.grey.shade800),
                dataRowColor: MaterialStateProperty.all(Colors.grey.shade900),
                columns: const [
            DataColumn(label: Text('Name', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Type', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Persons', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Age Range', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Gender', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Time Span', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Camera', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Tracking', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Action', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Actions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
          ],
          rows: _triggers.map((trigger) {
            final isDemographic = trigger.enableDemographicConditions == true;
            return DataRow(cells: [
              DataCell(Text(trigger.name ?? 'Unnamed', style: const TextStyle(color: Colors.white70))),
              DataCell(
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (isDemographic) ...[
                      const Tooltip(
                        message: 'Intelligent Signage (Demographic)',
                        child: Icon(Icons.psychology, color: Colors.blue, size: 18),
                      ),
                      const SizedBox(width: 4),
                    ],
                    Icon(
                      isDemographic ? Icons.smart_display : Icons.notifications,
                      color: isDemographic ? Colors.blue : Colors.orange,
                      size: 16,
                    ),
                  ],
                ),
              ),
              DataCell(Text(trigger.personCountDisplay, style: const TextStyle(color: Colors.white70))),
              DataCell(Text(trigger.ageRangeDisplay, style: const TextStyle(color: Colors.white70))),
              DataCell(Text(trigger.genderFilter ?? 'Any', style: const TextStyle(color: Colors.white70))),
              DataCell(Text(trigger.timeSpan, style: const TextStyle(color: Colors.white70))),
              DataCell(Text(trigger.cameraName ?? trigger.cameraDeviceId, style: const TextStyle(color: Colors.white70))),
              DataCell(Text(trigger.trackingDuration, style: const TextStyle(color: Colors.white70))),
              DataCell(
                Container(
                  constraints: const BoxConstraints(minWidth: 150),
                  child: DropdownButtonFormField<String?>(
                    value: trigger.actionUuid,
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
                      ..._availableActions.map((action) {
                        return DropdownMenuItem(
                          value: action['uuid'],
                          child: Text(
                            action['name']!,
                            style: const TextStyle(color: Colors.white70),
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      }).toList(),
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

  Widget _buildCardList() {
    return Column(
      children: _triggers.map((trigger) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.grey.shade900,
            border: Border.all(color: Colors.grey.shade700),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header with status badge
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        trigger.name ?? 'Unnamed Trigger',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () => _toggleTrigger(trigger),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
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
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                
                // Details
                _buildDetailRow('Persons', trigger.personCountDisplay),
                _buildDetailRow('Age Range', trigger.ageRangeDisplay),
                _buildDetailRow('Gender', trigger.genderFilter ?? 'Any'),
                _buildDetailRow('Time Span', trigger.timeSpan),
                _buildDetailRow('Camera', trigger.cameraName ?? trigger.cameraDeviceId),
                _buildDetailRow('Tracking', trigger.trackingDuration),
                
                // Action selector
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 120,
                        child: Text(
                          'Action:',
                          style: TextStyle(
                            color: Colors.grey.shade400,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      Expanded(
                        child: DropdownButtonFormField<String?>(
                          value: trigger.actionUuid,
                          decoration: InputDecoration(
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                            border: const OutlineInputBorder(),
                            fillColor: Colors.grey.shade800,
                            filled: true,
                          ),
                          style: const TextStyle(color: Colors.white, fontSize: 14),
                          dropdownColor: Colors.grey.shade800,
                          items: [
                            const DropdownMenuItem(
                              value: null,
                              child: Text('None'),
                            ),
                            ..._availableActions.map((action) {
                              return DropdownMenuItem(
                                value: action['uuid'],
                                child: Text(action['name']!),
                              );
                            }).toList(),
                          ],
                          onChanged: (newValue) => _updateTriggerAction(trigger, newValue),
                        ),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _showCreateEditDialog(trigger: trigger),
                      icon: const Icon(Icons.edit, size: 16),
                      label: const Text('Edit'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.blue,
                        side: const BorderSide(color: Colors.blue),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton.icon(
                      onPressed: () => _deleteTrigger(trigger),
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red,
                        side: const BorderSide(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: TextStyle(
                color: Colors.grey.shade400,
                fontSize: 14,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
