import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Camera settings model for instant detection configuration
class CameraSettings {
  final bool enableInstantDetectionOnRecording;

  const CameraSettings({
    this.enableInstantDetectionOnRecording = true,
  });

  CameraSettings copyWith({
    bool? enableInstantDetectionOnRecording,
  }) {
    return CameraSettings(
      enableInstantDetectionOnRecording: enableInstantDetectionOnRecording ?? 
          this.enableInstantDetectionOnRecording,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enable_instant_detection_on_recording': enableInstantDetectionOnRecording,
    };
  }

  factory CameraSettings.fromJson(Map<String, dynamic> json) {
    return CameraSettings(
      enableInstantDetectionOnRecording: json['enable_instant_detection_on_recording'] as bool? ?? true,
    );
  }
}

/// Camera settings notifier with persistence
class CameraSettingsNotifier extends StateNotifier<CameraSettings> {
  static const String _storageKey = 'camera_settings';
  final SharedPreferences _prefs;

  CameraSettingsNotifier(this._prefs) : super(const CameraSettings()) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final json = _prefs.getString(_storageKey);
    if (json != null) {
      try {
        // In a real app, you'd use json.decode here
        // For now, just load the boolean directly
        final enabled = _prefs.getBool('enable_instant_detection_on_recording') ?? true;
        state = CameraSettings(enableInstantDetectionOnRecording: enabled);
      } catch (e) {
        print('Error loading camera settings: $e');
      }
    }
  }

  Future<void> setEnableInstantDetectionOnRecording(bool enabled) async {
    state = state.copyWith(enableInstantDetectionOnRecording: enabled);
    await _prefs.setBool('enable_instant_detection_on_recording', enabled);
  }
}

/// Provider for camera settings
final cameraSettingsProvider = StateNotifierProvider<CameraSettingsNotifier, CameraSettings>((ref) {
  throw UnimplementedError('cameraSettingsProvider must be overridden');
});

/// Provider for SharedPreferences
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

/// Initialize camera settings provider
Future<Override> initializeCameraSettingsProvider() async {
  final prefs = await SharedPreferences.getInstance();
  return cameraSettingsProvider.overrideWith((ref) => CameraSettingsNotifier(prefs));
}
