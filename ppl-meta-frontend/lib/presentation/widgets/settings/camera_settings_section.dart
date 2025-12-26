import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';

/// Camera Settings Section for instant detection configuration
class CameraSettingsSection extends ConsumerStatefulWidget {
  const CameraSettingsSection({super.key});

  @override
  ConsumerState<CameraSettingsSection> createState() => _CameraSettingsSectionState();
}

class _CameraSettingsSectionState extends ConsumerState<CameraSettingsSection> {
  bool _enableInstantDetection = true;
  int _instantDetectionInterval = 5; // seconds
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      setState(() {
        _enableInstantDetection = prefs.getBool('enable_instant_detection_on_recording') ?? true;
        _instantDetectionInterval = prefs.getInt('instant_detection_interval') ?? 5;
        _isLoading = false;
      });
    } catch (e) {
      print('Error loading camera settings: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _saveInstantDetectionToggle(bool value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('enable_instant_detection_on_recording', value);
      setState(() {
        _enableInstantDetection = value;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              value 
                ? 'Instant detection will start automatically with recording'
                : 'Instant detection will not start automatically',
            ),
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      print('Error saving camera settings: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to save settings'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _saveInstantDetectionInterval(int seconds) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt('instant_detection_interval', seconds);
      setState(() {
        _instantDetectionInterval = seconds;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Instant detection interval set to $seconds seconds'),
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      print('Error saving instant detection interval: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to save interval setting'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section Header
            Row(
              children: [
                Icon(
                  Icons.camera_alt,
                  color: AppColors.primary,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Text(
                  'Camera Settings',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Instant Detection Setting
            if (_isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: CircularProgressIndicator(),
                ),
              )
            else ...[
              SwitchListTile(
                title: const Text(
                  'Auto-start Instant Detection',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Automatically start real-time face detection when recording starts',
                        style: TextStyle(fontSize: 14),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.blue.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: Colors.blue.withOpacity(0.3),
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.info_outline,
                              size: 18,
                              color: Colors.blue.shade700,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'When enabled, instant detection provides live person count and demographics while recording. Updates every $_instantDetectionInterval seconds in the camera widget.',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.blue.shade900,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                value: _enableInstantDetection,
                onChanged: _saveInstantDetectionToggle,
                activeColor: AppColors.primary,
                contentPadding: EdgeInsets.zero,
              ),
              
              const SizedBox(height: 24),
              
              // Instant Detection Time Slot Setting
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Instant Detection Time Slot',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'How often to process frames for instant detection',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: Slider(
                          value: _instantDetectionInterval.toDouble(),
                          min: 3,
                          max: 15,
                          divisions: 12,
                          label: '$_instantDetectionInterval seconds',
                          activeColor: AppColors.primary,
                          onChanged: (value) {
                            setState(() {
                              _instantDetectionInterval = value.round();
                            });
                          },
                          onChangeEnd: (value) {
                            _saveInstantDetectionInterval(value.round());
                          },
                        ),
                      ),
                      const SizedBox(width: 16),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: AppColors.primary.withOpacity(0.3),
                          ),
                        ),
                        child: Text(
                          '$_instantDetectionInterval s',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: AppColors.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.orange.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Colors.orange.withOpacity(0.3),
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.tips_and_updates_outlined,
                          size: 18,
                          color: Colors.orange.shade700,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Performance Tip',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.orange.shade900,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Lower values (3-5s) provide more frequent updates but use more processing power. Higher values (10-15s) are more efficient but update less often.',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.orange.shade900,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
            
            const SizedBox(height: 16),
            
            // Feature Description
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: Colors.green.withOpacity(0.2),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.check_circle_outline,
                        size: 18,
                        color: Colors.green.shade700,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Instant Detection Features',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.green.shade900,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _buildFeatureItem('Real-time person detection (updates every 5s)'),
                  _buildFeatureItem('Live age and gender demographics'),
                  _buildFeatureItem('No impact on recording quality'),
                  _buildFeatureItem('Memory-only storage (no database)'),
                  _buildFeatureItem('Automatically stops when recording stops'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFeatureItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(left: 26, top: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '• ',
            style: TextStyle(
              fontSize: 13,
              color: Colors.green.shade700,
            ),
          ),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 13,
                color: Colors.green.shade900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
