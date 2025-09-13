import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../services/storage_service.dart';
import '../../../models/storage_preferences.dart';
import '../../../core/theme/app_theme.dart';

/// Provider for fetching storage preferences
final storagePreferencesProvider = FutureProvider<UserStoragePreferences>((ref) async {
  final storageService = ref.watch(storageServiceProvider);
  return await storageService.getUserPreferences();
});

class StorageSettingsSection extends ConsumerStatefulWidget {
  const StorageSettingsSection({super.key});

  @override
  ConsumerState<StorageSettingsSection> createState() => _StorageSettingsSectionState();
}

class _StorageSettingsSectionState extends ConsumerState<StorageSettingsSection> {
  bool _isLoading = false;
  
  // Local state for form fields
  double _defaultCollectionSizeGb = 50.0;
  double _defaultLivePortionPercentage = 70.0;
  double _notificationThresholdPercentage = 80.0;
  bool _enableStorageNotifications = true;
  bool _autoArchiveEnabled = true;
  int _minAgeForArchiveDays = 7;
  bool _autoDeleteEnabled = false;
  int _autoDeleteAfterDays = 365;
  String _preferredVideoQuality = 'medium';

  @override
  Widget build(BuildContext context) {
    final storageState = ref.watch(storagePreferencesProvider);
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader(),
          const SizedBox(height: 16),
          _buildStorageSettings(context, storageState),
        ],
      ),
    );
  }

  Widget _buildSectionHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(
            Icons.storage,
            color: AppColors.primary,
            size: 20,
          ),
          const SizedBox(width: 12),
          Text(
            'Storage Management',
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStorageSettings(BuildContext context, AsyncValue<UserStoragePreferences> storageState) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: storageState.when(
        data: (preferences) {
          // Update local state with fetched preferences
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              setState(() {
                _defaultCollectionSizeGb = preferences.defaultCollectionSizeGb;
                _defaultLivePortionPercentage = preferences.defaultLivePortionPercentage;
                _notificationThresholdPercentage = preferences.notificationThresholdPercentage;
                _enableStorageNotifications = preferences.enableStorageNotifications;
                _autoArchiveEnabled = preferences.defaultAutoArchiveEnabled;
                _minAgeForArchiveDays = preferences.defaultMinAgeForArchiveDays;
                _autoDeleteEnabled = preferences.autoDeleteOldArchivesEnabled;
                _autoDeleteAfterDays = preferences.autoDeleteAfterDays;
                _preferredVideoQuality = preferences.preferredVideoQuality;
              });
            }
          });
          
          return _buildSettingsForm();
        },
        loading: () => const Center(
          child: Padding(
            padding: EdgeInsets.all(32.0),
            child: CircularProgressIndicator(),
          ),
        ),
        error: (error, stack) => _buildErrorWidget(error),
      ),
    );
  }

  Widget _buildSettingsForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Default Collection Size
        _buildSettingTile(
          icon: Icons.folder_open,
          title: 'Default Collection Size',
          subtitle: '${_defaultCollectionSizeGb.toStringAsFixed(1)} GB per camera collection',
          child: Slider(
            value: _defaultCollectionSizeGb,
            min: 10.0,
            max: 1000.0,
            divisions: 99,
            label: '${_defaultCollectionSizeGb.toStringAsFixed(1)} GB',
            onChanged: (value) {
              setState(() {
                _defaultCollectionSizeGb = value;
              });
            },
            onChangeEnd: (value) => _savePreferences(),
          ),
        ),
        
        const Divider(),
        
        // Live/Archive Portion
        _buildSettingTile(
          icon: Icons.pie_chart,
          title: 'Live Streaming Portion',
          subtitle: '${_defaultLivePortionPercentage.toStringAsFixed(0)}% for immediate streaming',
          child: Slider(
            value: _defaultLivePortionPercentage,
            min: 50.0,
            max: 90.0,
            divisions: 8,
            label: '${_defaultLivePortionPercentage.toStringAsFixed(0)}%',
            onChanged: (value) {
              setState(() {
                _defaultLivePortionPercentage = value;
              });
            },
            onChangeEnd: (value) => _savePreferences(),
          ),
        ),
        
        const Divider(),
        
        // Notification Settings
        _buildSwitchTile(
          icon: Icons.notifications,
          title: 'Storage Notifications',
          subtitle: 'Alert when collections reach capacity',
          value: _enableStorageNotifications,
          onChanged: (value) {
            setState(() {
              _enableStorageNotifications = value;
            });
            _savePreferences();
          },
        ),
        
        if (_enableStorageNotifications) ...[
          _buildSettingTile(
            icon: Icons.warning,
            title: 'Notification Threshold',
            subtitle: 'Alert at ${_notificationThresholdPercentage.toStringAsFixed(0)}% capacity',
            child: Slider(
              value: _notificationThresholdPercentage,
              min: 50.0,
              max: 95.0,
              divisions: 9,
              label: '${_notificationThresholdPercentage.toStringAsFixed(0)}%',
              onChanged: (value) {
                setState(() {
                  _notificationThresholdPercentage = value;
                });
              },
              onChangeEnd: (value) => _savePreferences(),
            ),
          ),
        ],
        
        const Divider(),
        
        // Auto Archive Settings
        _buildSwitchTile(
          icon: Icons.archive,
          title: 'Automatic Archival',
          subtitle: 'Move old recordings to archive automatically',
          value: _autoArchiveEnabled,
          onChanged: (value) {
            setState(() {
              _autoArchiveEnabled = value;
            });
            _savePreferences();
          },
        ),
        
        if (_autoArchiveEnabled) ...[
          _buildDropdownTile(
            icon: Icons.schedule,
            title: 'Archive After',
            subtitle: '$_minAgeForArchiveDays days',
            value: _minAgeForArchiveDays,
            items: const [1, 3, 7, 14, 30, 60, 90],
            onChanged: (value) {
              setState(() {
                _minAgeForArchiveDays = value!;
              });
              _savePreferences();
            },
          ),
        ],
        
        const Divider(),
        
        // Video Quality Settings
        _buildDropdownTile(
          icon: Icons.high_quality,
          title: 'Video Quality',
          subtitle: _preferredVideoQuality.toUpperCase(),
          value: _preferredVideoQuality,
          items: const ['low', 'medium', 'high', 'ultra'],
          onChanged: (value) {
            setState(() {
              _preferredVideoQuality = value!;
            });
            _savePreferences();
          },
        ),
        
        const Divider(),
        
        // Auto Delete Settings
        _buildSwitchTile(
          icon: Icons.delete_forever,
          title: 'Auto-Delete Old Archives',
          subtitle: 'Automatically delete archived media after a period',
          value: _autoDeleteEnabled,
          onChanged: (value) {
            setState(() {
              _autoDeleteEnabled = value;
            });
            _savePreferences();
          },
        ),
        
        if (_autoDeleteEnabled) ...[
          _buildDropdownTile(
            icon: Icons.delete_forever,
            title: 'Delete After',
            subtitle: '$_autoDeleteAfterDays days',
            value: _autoDeleteAfterDays,
            items: const [30, 60, 90, 180, 365, 730, 1095],
            onChanged: (value) {
              setState(() {
                _autoDeleteAfterDays = value!;
              });
              _savePreferences();
            },
          ),
        ],
        
        const SizedBox(height: 16),
        
        // Reset to Defaults Button
        Center(
          child: ElevatedButton.icon(
            onPressed: _isLoading ? null : _resetToDefaults,
            icon: Icon(_isLoading ? Icons.hourglass_empty : Icons.restore),
            label: Text(_isLoading ? 'Resetting...' : 'Reset to Defaults'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.secondary,
              foregroundColor: Colors.white,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: AppColors.secondary),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }

  Widget _buildSwitchTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.secondary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: AppColors.primary,
          ),
        ],
      ),
    );
  }

  Widget _buildDropdownTile<T>({
    required IconData icon,
    required String title,
    required String subtitle,
    required T value,
    required List<T> items,
    required ValueChanged<T?> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.secondary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          DropdownButton<T>(
            value: value,
            items: items.map((item) => DropdownMenuItem<T>(
              value: item,
              child: Text(item is String ? item : '$item ${item is int && title.contains('After') ? 'days' : ''}'),
            )).toList(),
            onChanged: onChanged,
            underline: Container(),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorWidget(Object error) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Icon(
            Icons.error_outline,
            color: Colors.red,
            size: 48,
          ),
          const SizedBox(height: 16),
          Text(
            'Failed to load storage preferences',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: Colors.red,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error.toString(),
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: () => ref.refresh(storagePreferencesProvider),
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Future<void> _savePreferences() async {
    if (_isLoading) return;
    
    setState(() {
      _isLoading = true;
    });

    try {
      final storageService = ref.read(storageServiceProvider);
      final updates = UserStoragePreferencesUpdate(
        defaultCollectionSizeGb: _defaultCollectionSizeGb,
        defaultLivePortionPercentage: _defaultLivePortionPercentage,
        enableStorageNotifications: _enableStorageNotifications,
        notificationThresholdPercentage: _notificationThresholdPercentage,
        defaultAutoArchiveEnabled: _autoArchiveEnabled,
        defaultMinAgeForArchiveDays: _minAgeForArchiveDays,
        autoDeleteOldArchivesEnabled: _autoDeleteEnabled,
        autoDeleteAfterDays: _autoDeleteAfterDays,
        preferredVideoQuality: _preferredVideoQuality,
      );
      
      await storageService.updateUserPreferences(updates);
      
      // Refresh the provider to get updated data
      ref.invalidate(storagePreferencesProvider);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Storage preferences saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save preferences: $error'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _resetToDefaults() async {
    if (_isLoading) return;
    
    setState(() {
      _isLoading = true;
    });

    try {
      final storageService = ref.read(storageServiceProvider);
      await storageService.resetToDefaults();
      
      // Refresh the provider to get updated data
      ref.invalidate(storagePreferencesProvider);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Storage preferences reset to defaults'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to reset preferences: $error'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}