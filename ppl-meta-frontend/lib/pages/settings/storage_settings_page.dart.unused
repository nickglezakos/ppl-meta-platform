// Storage Settings Page
// Allows users to configure default collection sizes, live/archive ratios,
// and notification preferences for their camera collections.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/user_storage_preferences.dart';
import '../services/api_service.dart';
import '../providers/user_preferences_provider.dart';
import '../widgets/common/loading_overlay.dart';
import '../widgets/common/error_dialog.dart';
import '../widgets/storage/storage_usage_chart.dart';
import '../widgets/storage/storage_recommendation_card.dart';

class StorageSettingsPage extends StatefulWidget {
  const StorageSettingsPage({super.key});

  @override
  State<StorageSettingsPage> createState() => _StorageSettingsPageState();
}

class _StorageSettingsPageState extends State<StorageSettingsPage> {
  late UserStoragePreferences _preferences;
  bool _isLoading = true;
  bool _isSaving = false;
  
  // Form controllers
  late TextEditingController _defaultSizeController;
  late double _livePortionPercentage;
  late bool _notificationsEnabled;
  late bool _autoArchiveEnabled;
  late int _archiveAfterDays;
  late double _notificationThreshold;
  late bool _emailNotificationsEnabled;
  late bool _pushNotificationsEnabled;
  late bool _autoDeleteEnabled;
  late int _autoDeleteAfterDays;
  late String _videoQuality;
  late bool _compressionEnabled;
  
  final List<int> _archiveAfterDaysOptions = [7, 14, 30, 60, 90];
  final List<int> _autoDeleteAfterDaysOptions = [90, 180, 365, 730, 1095];
  final List<String> _videoQualityOptions = ['low', 'medium', 'high', 'ultra'];

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  @override
  void dispose() {
    _defaultSizeController.dispose();
    super.dispose();
  }

  Future<void> _loadPreferences() async {
    try {
      final provider = Provider.of<UserPreferencesProvider>(context, listen: false);
      _preferences = await provider.getStoragePreferences();
      
      _initializeFormFields();
      
      setState(() {
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showErrorDialog('Failed to load storage preferences: $e');
    }
  }

  void _initializeFormFields() {
    _defaultSizeController = TextEditingController(
      text: _preferences.defaultCollectionSizeGb.toString()
    );
    _livePortionPercentage = _preferences.defaultLivePortionPercentage;
    _notificationsEnabled = _preferences.enableStorageNotifications;
    _autoArchiveEnabled = _preferences.defaultAutoArchiveEnabled;
    _archiveAfterDays = _preferences.defaultMinAgeForArchiveDays;
    _notificationThreshold = _preferences.notificationThresholdPercentage;
    _emailNotificationsEnabled = _preferences.emailNotificationsEnabled;
    _pushNotificationsEnabled = _preferences.pushNotificationsEnabled;
    _autoDeleteEnabled = _preferences.autoDeleteOldArchivesEnabled;
    _autoDeleteAfterDays = _preferences.autoDeleteAfterDays;
    _videoQuality = _preferences.preferredVideoQuality;
    _compressionEnabled = _preferences.preferredCompressionEnabled;
  }

  Future<void> _savePreferences() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final updatedPreferences = UserStoragePreferences(
        userUuid: _preferences.userUuid,
        defaultCollectionSizeGb: double.parse(_defaultSizeController.text),
        defaultLivePortionPercentage: _livePortionPercentage,
        enableStorageNotifications: _notificationsEnabled,
        defaultAutoArchiveEnabled: _autoArchiveEnabled,
        defaultMinAgeForArchiveDays: _archiveAfterDays,
        notificationThresholdPercentage: _notificationThreshold,
        emailNotificationsEnabled: _emailNotificationsEnabled,
        pushNotificationsEnabled: _pushNotificationsEnabled,
        autoDeleteOldArchivesEnabled: _autoDeleteEnabled,
        autoDeleteAfterDays: _autoDeleteAfterDays,
        preferredVideoQuality: _videoQuality,
        preferredCompressionEnabled: _compressionEnabled,
      );

      final provider = Provider.of<UserPreferencesProvider>(context, listen: false);
      await provider.updateStoragePreferences(updatedPreferences);

      _preferences = updatedPreferences;

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Storage preferences saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      _showErrorDialog('Failed to save preferences: $e');
    } finally {
      setState(() {
        _isSaving = false;
      });
    }
  }

  void _resetToDefaults() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reset to Defaults'),
        content: const Text(
          'This will reset all storage settings to their default values. '
          'Are you sure you want to continue?'
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _setDefaultValues();
            },
            child: const Text('Reset'),
          ),
        ],
      ),
    );
  }

  void _setDefaultValues() {
    setState(() {
      _defaultSizeController.text = '50.0';
      _livePortionPercentage = 70.0;
      _notificationsEnabled = true;
      _autoArchiveEnabled = true;
      _archiveAfterDays = 7;
      _notificationThreshold = 80.0;
      _emailNotificationsEnabled = true;
      _pushNotificationsEnabled = true;
      _autoDeleteEnabled = false;
      _autoDeleteAfterDays = 365;
      _videoQuality = 'medium';
      _compressionEnabled = true;
    });
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (context) => ErrorDialog(
        title: 'Storage Settings Error',
        message: message,
      ),
    );
  }

  double get _archivePortionPercentage => 100.0 - _livePortionPercentage;

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Storage Settings'),
        actions: [
          TextButton.icon(
            onPressed: _resetToDefaults,
            icon: const Icon(Icons.refresh, color: Colors.white),
            label: const Text('Reset', style: TextStyle(color: Colors.white)),
          ),
          IconButton(
            onPressed: _isSaving ? null : _savePreferences,
            icon: _isSaving 
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Icon(Icons.save),
          ),
        ],
      ),
      body: LoadingOverlay(
        isLoading: _isSaving,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildCollectionSizeSection(),
            const SizedBox(height: 24),
            _buildStorageDistributionSection(),
            const SizedBox(height: 24),
            _buildArchivalSection(),
            const SizedBox(height: 24),
            _buildNotificationSection(),
            const SizedBox(height: 24),
            _buildAdvancedSection(),
            const SizedBox(height: 24),
            _buildUsageOverview(),
          ],
        ),
      ),
    );
  }

  Widget _buildCollectionSizeSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Default Collection Size',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Set the default storage quota for new camera collections.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _defaultSizeController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Size (GB)',
                      border: OutlineInputBorder(),
                      suffixText: 'GB',
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter a size';
                      }
                      final size = double.tryParse(value);
                      if (size == null || size < 1.0 || size > 1000.0) {
                        return 'Size must be between 1 and 1000 GB';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  children: [
                    IconButton(
                      onPressed: () {
                        final currentSize = double.tryParse(_defaultSizeController.text) ?? 50.0;
                        _defaultSizeController.text = (currentSize + 10).toString();
                      },
                      icon: const Icon(Icons.add),
                    ),
                    IconButton(
                      onPressed: () {
                        final currentSize = double.tryParse(_defaultSizeController.text) ?? 50.0;
                        if (currentSize > 10) {
                          _defaultSizeController.text = (currentSize - 10).toString();
                        }
                      },
                      icon: const Icon(Icons.remove),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            StorageRecommendationCard(
              currentSize: double.tryParse(_defaultSizeController.text) ?? 50.0,
              onSizeRecommendation: (size) {
                setState(() {
                  _defaultSizeController.text = size.toString();
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStorageDistributionSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Storage Distribution',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Configure how storage is split between live and archived recordings.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        'Live Streaming: ${_livePortionPercentage.round()}%',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        'Immediate access for streaming',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        'Archive: ${_archivePortionPercentage.round()}%',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        'Older recordings storage',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Slider(
              value: _livePortionPercentage,
              min: 10.0,
              max: 95.0,
              divisions: 17,
              label: '${_livePortionPercentage.round()}% Live',
              onChanged: (value) {
                setState(() {
                  _livePortionPercentage = value;
                });
              },
            ),
            const SizedBox(height: 16),
            StorageUsageChart(
              livePercentage: _livePortionPercentage,
              archivePercentage: _archivePortionPercentage,
              totalSizeGb: double.tryParse(_defaultSizeController.text) ?? 50.0,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildArchivalSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Automatic Archival',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Configure when recordings are automatically moved to archive storage.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Enable Auto-Archival'),
              subtitle: const Text('Move old recordings to archive automatically'),
              value: _autoArchiveEnabled,
              onChanged: (value) {
                setState(() {
                  _autoArchiveEnabled = value;
                });
              },
            ),
            if (_autoArchiveEnabled) ...[
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                value: _archiveAfterDays,
                decoration: const InputDecoration(
                  labelText: 'Archive recordings after',
                  border: OutlineInputBorder(),
                ),
                items: _archiveAfterDaysOptions.map((days) => 
                  DropdownMenuItem(
                    value: days,
                    child: Text('$days days'),
                  )
                ).toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() {
                      _archiveAfterDays = value;
                    });
                  }
                },
              ),
            ],
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Auto-Delete Old Archives'),
              subtitle: Text(
                _autoDeleteEnabled 
                  ? 'Delete archives after $_autoDeleteAfterDays days'
                  : 'Keep all archived recordings'
              ),
              value: _autoDeleteEnabled,
              onChanged: (value) {
                setState(() {
                  _autoDeleteEnabled = value;
                });
              },
            ),
            if (_autoDeleteEnabled) ...[
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                value: _autoDeleteAfterDays,
                decoration: const InputDecoration(
                  labelText: 'Delete archives after',
                  border: OutlineInputBorder(),
                ),
                items: _autoDeleteAfterDaysOptions.map((days) => 
                  DropdownMenuItem(
                    value: days,
                    child: Text('${days ~/ 365 > 0 ? "${days ~/ 365} year${days ~/ 365 > 1 ? 's' : ''}" : "$days days"}'),
                  )
                ).toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() {
                      _autoDeleteAfterDays = value;
                    });
                  }
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildNotificationSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Storage Notifications',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Get alerted when collections are approaching capacity limits.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Enable Storage Notifications'),
              subtitle: const Text('Alert when collections reach capacity'),
              value: _notificationsEnabled,
              onChanged: (value) {
                setState(() {
                  _notificationsEnabled = value;
                });
              },
            ),
            if (_notificationsEnabled) ...[
              const SizedBox(height: 16),
              Text(
                'Notification Threshold: ${_notificationThreshold.round()}%',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Slider(
                value: _notificationThreshold,
                min: 50.0,
                max: 95.0,
                divisions: 9,
                label: '${_notificationThreshold.round()}%',
                onChanged: (value) {
                  setState(() {
                    _notificationThreshold = value;
                  });
                },
              ),
              const SizedBox(height: 16),
              SwitchListTile(
                title: const Text('Email Notifications'),
                subtitle: const Text('Send notifications via email'),
                value: _emailNotificationsEnabled,
                onChanged: (value) {
                  setState(() {
                    _emailNotificationsEnabled = value;
                  });
                },
              ),
              SwitchListTile(
                title: const Text('Push Notifications'),
                subtitle: const Text('Send notifications to mobile app'),
                value: _pushNotificationsEnabled,
                onChanged: (value) {
                  setState(() {
                    _pushNotificationsEnabled = value;
                  });
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAdvancedSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Advanced Settings',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Configure video quality and compression preferences.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _videoQuality,
              decoration: const InputDecoration(
                labelText: 'Default Video Quality',
                border: OutlineInputBorder(),
              ),
              items: _videoQualityOptions.map((quality) => 
                DropdownMenuItem(
                  value: quality,
                  child: Text(quality.substring(0, 1).toUpperCase() + quality.substring(1)),
                )
              ).toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _videoQuality = value;
                  });
                }
              },
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Enable Compression'),
              subtitle: const Text('Compress archived recordings to save space'),
              value: _compressionEnabled,
              onChanged: (value) {
                setState(() {
                  _compressionEnabled = value;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUsageOverview() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Storage Overview',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                TextButton.icon(
                  onPressed: () {
                    // Navigate to detailed storage analytics
                    Navigator.pushNamed(context, '/storage-analytics');
                  },
                  icon: const Icon(Icons.analytics),
                  label: const Text('View Details'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            FutureBuilder<Map<String, dynamic>>(
              future: ApiService.get('/api/v1/users/storage-summary'),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                
                if (snapshot.hasError) {
                  return Text('Error loading storage summary: ${snapshot.error}');
                }
                
                final data = snapshot.data ?? {};
                return Column(
                  children: [
                    _buildOverviewTile(
                      'Total Collections',
                      '${data['total_collections'] ?? 0}',
                      Icons.folder_outlined,
                    ),
                    _buildOverviewTile(
                      'Total Storage Used',
                      '${(data['total_used_gb'] ?? 0.0).toStringAsFixed(1)} GB',
                      Icons.storage,
                    ),
                    _buildOverviewTile(
                      'Overall Usage',
                      '${(data['usage_percentage'] ?? 0.0).toStringAsFixed(1)}%',
                      Icons.pie_chart,
                    ),
                    if ((data['collections_near_capacity'] ?? 0) > 0)
                      _buildOverviewTile(
                        'Collections Near Capacity',
                        '${data['collections_near_capacity']}',
                        Icons.warning,
                        isWarning: true,
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverviewTile(String title, String value, IconData icon, {bool isWarning = false}) {
    return ListTile(
      leading: Icon(
        icon,
        color: isWarning ? Colors.orange : Theme.of(context).primaryColor,
      ),
      title: Text(title),
      trailing: Text(
        value,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: isWarning ? Colors.orange : null,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}