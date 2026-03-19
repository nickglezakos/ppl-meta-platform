import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';
import '../../../services/camera_settings_service.dart';
import '../../../services/offline_queue_service.dart';
import '../../../services/device_identifier_service.dart';
import 'dart:async';

/// Camera settings screen for mobile-first settings management
class CameraSettingsScreen extends StatefulWidget {
  const CameraSettingsScreen({Key? key}) : super(key: key);

  @override
  State<CameraSettingsScreen> createState() => _CameraSettingsScreenState();
}

class _CameraSettingsScreenState extends State<CameraSettingsScreen> {
  final CameraSettingsService _settingsService = CameraSettingsService();
  final OfflineQueueService _queueService = OfflineQueueService();
  final DeviceIdentifierService _deviceIdService = DeviceIdentifierService();

  Map<String, dynamic> _settings = {};
  bool _isLoading = true;
  bool _isSaving = false;
  bool _hasUnsavedChanges = false;
  int _queueSize = 0;
  DateTime? _lastSync;
  
  // Controllers for form fields
  late TextEditingController _nameController;
  late TextEditingController _maxDurationController;
  late TextEditingController _storageLimitController;
  
  String? _selectedResolution;
  int? _selectedFrameRate;
  String? _selectedOrientation;
  bool _recordingEnabled = true;
  bool _autoStartRecording = false;

  final List<String> _resolutions = [
    '640x480',
    '1280x720',
    '1920x1080',
    '2560x1440',
    '3840x2160',
  ];
  
  final List<int> _frameRates = [15, 24, 30, 60];
  final List<String> _orientations = ['portrait', 'landscape'];

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _maxDurationController = TextEditingController();
    _storageLimitController = TextEditingController();
    _loadSettings();
    _loadQueueSize();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _maxDurationController.dispose();
    _storageLimitController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);
    
    try {
      final settings = await _settingsService.getLocalSettings();
      final lastSync = await _settingsService.getLastSyncTime();
      
      setState(() {
        _settings = settings;
        _lastSync = lastSync;
        _updateFormFields();
        _isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading settings: $e');
      setState(() => _isLoading = false);
      _showError('Failed to load settings');
    }
  }

  Future<void> _loadQueueSize() async {
    final size = await _queueService.getQueueSize();
    setState(() => _queueSize = size);
  }

  void _updateFormFields() {
    _nameController.text = _settings['name'] ?? '';
    _selectedResolution = _settings['resolution'] ?? '1920x1080';
    _selectedFrameRate = _settings['frame_rate'] ?? 30;
    _selectedOrientation = _settings['orientation'] ?? 'portrait';
    _recordingEnabled = _settings['recording_enabled'] ?? true;
    _autoStartRecording = _settings['auto_start_recording'] ?? false;
    _maxDurationController.text = (_settings['max_recording_duration'] ?? 300).toString();
    _storageLimitController.text = (_settings['storage_limit_mb'] ?? 1000).toString();
  }

  Future<void> _saveSettings() async {
    setState(() => _isSaving = true);
    
    try {
      // Update settings map
      _settings['name'] = _nameController.text.trim();
      _settings['resolution'] = _selectedResolution;
      _settings['frame_rate'] = _selectedFrameRate;
      _settings['orientation'] = _selectedOrientation;
      _settings['recording_enabled'] = _recordingEnabled;
      _settings['auto_start_recording'] = _autoStartRecording;
      _settings['max_recording_duration'] = int.tryParse(_maxDurationController.text) ?? 300;
      _settings['storage_limit_mb'] = int.tryParse(_storageLimitController.text) ?? 1000;
      
      // Save locally first (instant feedback)
      final savedLocally = await _settingsService.saveLocalSettings(_settings);
      
      if (!savedLocally) {
        throw Exception('Failed to save settings locally');
      }
      
      // Try to sync to backend
      final authProvider = context.read<AuthenticationProvider>();
      final baseUrl = authProvider.baseUrl;
      final authToken = authProvider.token;
      
      if (baseUrl != null && authToken != null) {
        final syncSuccess = await _settingsService.syncToBackend(
          baseUrl: baseUrl,
          authToken: authToken,
          forceSync: true,
        );
        
        if (syncSuccess) {
          setState(() {
            _hasUnsavedChanges = false;
            _lastSync = DateTime.now();
          });
          _showSuccess('Settings saved and synced');
        } else {
          // Add to offline queue
          final uuid = await _deviceIdService.getStoredCameraUuid();
          await _queueService.enqueue(
            type: OfflineQueueService.typeSettingsUpdate,
            data: _settings,
            cameraUuid: uuid,
          );
          await _loadQueueSize();
          
          _showWarning('Settings saved locally, will sync when online');
        }
      } else {
        _showWarning('Settings saved locally, not connected to backend');
      }
      
      setState(() => _isSaving = false);
    } catch (e) {
      print('❌ Error saving settings: $e');
      setState(() => _isSaving = false);
      _showError('Failed to save settings: $e');
    }
  }

  Future<void> _syncNow() async {
    setState(() => _isSaving = true);
    
    try {
      final authProvider = context.read<AuthenticationProvider>();
      final baseUrl = authProvider.baseUrl;
      final authToken = authProvider.token;
      final uuid = await _deviceIdService.getStoredCameraUuid();
      
      if (baseUrl == null || authToken == null || uuid == null) {
        _showError('Not connected to backend');
        setState(() => _isSaving = false);
        return;
      }
      
      // Sync current settings
      final syncSuccess = await _settingsService.syncToBackend(
        baseUrl: baseUrl,
        authToken: authToken,
        forceSync: true,
      );
      
      // Sync offline queue
      final queueResult = await _queueService.syncAll(
        baseUrl: baseUrl,
        authToken: authToken,
        cameraUuid: uuid,
      );
      
      await _loadQueueSize();
      
      if (syncSuccess && queueResult['success']) {
        setState(() => _lastSync = DateTime.now());
        _showSuccess('All settings synced successfully');
      } else {
        _showWarning('Partial sync: ${queueResult['synced']} succeeded, ${queueResult['failed']} failed');
      }
      
      setState(() => _isSaving = false);
    } catch (e) {
      print('❌ Error syncing: $e');
      setState(() => _isSaving = false);
      _showError('Sync failed: $e');
    }
  }

  Future<void> _fetchBackendSettings() async {
    setState(() => _isLoading = true);
    
    try {
      final authProvider = context.read<AuthenticationProvider>();
      final baseUrl = authProvider.baseUrl;
      final authToken = authProvider.token;
      
      if (baseUrl == null || authToken == null) {
        _showError('Not connected to backend');
        setState(() => _isLoading = false);
        return;
      }
      
      final backendSettings = await _settingsService.fetchFromBackend(
        baseUrl: baseUrl,
        authToken: authToken,
      );
      
      if (backendSettings == null) {
        _showError('Failed to fetch backend settings');
        setState(() => _isLoading = false);
        return;
      }
      
      // Merge with local settings
      final mergeResult = await _settingsService.mergeSettings(
        localSettings: _settings,
        backendSettings: backendSettings,
      );
      
      final merged = mergeResult['merged'] as Map<String, dynamic>;
      final conflicts = mergeResult['conflicts'] as List<Map<String, dynamic>>;
      
      // Save merged settings
      await _settingsService.saveLocalSettings(merged);
      
      setState(() {
        _settings = merged;
        _updateFormFields();
        _isLoading = false;
      });
      
      if (conflicts.isNotEmpty) {
        _showConflictsDialog(conflicts);
      } else {
        _showSuccess('Settings updated from backend');
      }
    } catch (e) {
      print('❌ Error fetching backend settings: $e');
      setState(() => _isLoading = false);
      _showError('Failed to fetch backend settings');
    }
  }

  void _showConflictsDialog(List<Map<String, dynamic>> conflicts) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('⚠️ Settings Conflicts Resolved'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('The following settings had conflicts:'),
              const SizedBox(height: 12),
              ...conflicts.map((conflict) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '• ${conflict['setting']}: ${conflict['resolution']} (${conflict['reason']})',
                  style: const TextStyle(fontSize: 12),
                ),
              )),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }

  void _showWarning(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.orange),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Camera Settings'),
        actions: [
          if (_queueSize > 0)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Chip(
                  label: Text('$_queueSize queued'),
                  backgroundColor: Colors.orange,
                  labelStyle: const TextStyle(fontSize: 11, color: Colors.white),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.cloud_upload),
            onPressed: _isSaving ? null : _syncNow,
            tooltip: 'Sync Now',
          ),
          IconButton(
            icon: const Icon(Icons.cloud_download),
            onPressed: _isLoading ? null : _fetchBackendSettings,
            tooltip: 'Fetch from Backend',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Sync Status Card
                  _buildSyncStatusCard(),
                  const SizedBox(height: 24),
                  
                  // Basic Settings
                  _buildSectionHeader('Basic Settings'),
                  _buildTextField(
                    controller: _nameController,
                    label: 'Camera Name',
                    icon: Icons.label,
                  ),
                  const SizedBox(height: 16),
                  
                  // Recording Settings
                  _buildSectionHeader('Recording Settings'),
                  _buildSwitchTile(
                    title: 'Recording Enabled',
                    value: _recordingEnabled,
                    onChanged: (val) => setState(() => _recordingEnabled = val),
                  ),
                  _buildSwitchTile(
                    title: 'Auto-start Recording',
                    value: _autoStartRecording,
                    onChanged: (val) => setState(() => _autoStartRecording = val),
                  ),
                  const SizedBox(height: 16),
                  
                  // Video Settings
                  _buildSectionHeader('Video Settings'),
                  _buildDropdown<String>(
                    label: 'Resolution',
                    value: _selectedResolution,
                    items: _resolutions,
                    onChanged: (val) => setState(() => _selectedResolution = val),
                  ),
                  const SizedBox(height: 12),
                  _buildDropdown<int>(
                    label: 'Frame Rate',
                    value: _selectedFrameRate,
                    items: _frameRates,
                    onChanged: (val) => setState(() => _selectedFrameRate = val),
                  ),
                  const SizedBox(height: 12),
                  _buildDropdown<String>(
                    label: 'Orientation',
                    value: _selectedOrientation,
                    items: _orientations,
                    onChanged: (val) => setState(() => _selectedOrientation = val),
                  ),
                  const SizedBox(height: 16),
                  
                  // Storage Settings
                  _buildSectionHeader('Storage Settings'),
                  _buildTextField(
                    controller: _maxDurationController,
                    label: 'Max Recording Duration (seconds)',
                    icon: Icons.timer,
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 12),
                  _buildTextField(
                    controller: _storageLimitController,
                    label: 'Storage Limit (MB)',
                    icon: Icons.storage,
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 32),
                  
                  // Save Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isSaving ? null : _saveSettings,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Save Settings'),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildSyncStatusCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _lastSync != null ? Icons.cloud_done : Icons.cloud_off,
                  color: _lastSync != null ? Colors.green : Colors.grey,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Sync Status',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        _lastSync != null
                            ? 'Last synced: ${_formatDateTime(_lastSync!)}'
                            : 'Never synced',
                        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (_queueSize > 0) ...[
              const SizedBox(height: 8),
              Text(
                '$_queueSize pending change(s) in offline queue',
                style: const TextStyle(fontSize: 12, color: Colors.orange),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
      ),
      onChanged: (_) => setState(() => _hasUnsavedChanges = true),
    );
  }

  Widget _buildDropdown<T>({
    required String label,
    required T? value,
    required List<T> items,
    required void Function(T?) onChanged,
  }) {
    return DropdownButtonFormField<T>(
      value: value,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      items: items.map((item) {
        return DropdownMenuItem<T>(
          value: item,
          child: Text(item.toString()),
        );
      }).toList(),
      onChanged: (val) {
        onChanged(val);
        setState(() => _hasUnsavedChanges = true);
      },
    );
  }

  Widget _buildSwitchTile({
    required String title,
    required bool value,
    required void Function(bool) onChanged,
  }) {
    return SwitchListTile(
      title: Text(title),
      value: value,
      onChanged: (val) {
        onChanged(val);
        setState(() => _hasUnsavedChanges = true);
      },
      contentPadding: EdgeInsets.zero,
    );
  }

  String _formatDateTime(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    
    if (diff.inSeconds < 60) {
      return '${diff.inSeconds}s ago';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h ago';
    } else {
      return '${diff.inDays}d ago';
    }
  }
}
