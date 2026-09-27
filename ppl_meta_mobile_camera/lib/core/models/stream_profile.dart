import 'package:camera/camera.dart';

/// Named stream profiles for mobile → platform upload.
///
/// Users pick these in Camera Settings. They control capture resolution,
/// JPEG encode quality, and send pacing — not just a cosmetic FPS label.
enum StreamProfileId {
  lowBandwidth,
  balanced,
  highQuality,
}

class StreamProfile {
  final StreamProfileId id;
  final String label;
  final String description;
  /// Stored settings resolution string (WxH).
  final String resolution;
  /// Target upload pacing (frames the app tries to send per second).
  final int targetFps;
  /// JPEG encode quality 1–100.
  final int jpegQuality;
  /// camera plugin resolution preset.
  final ResolutionPreset cameraPreset;

  const StreamProfile({
    required this.id,
    required this.label,
    required this.description,
    required this.resolution,
    required this.targetFps,
    required this.jpegQuality,
    required this.cameraPreset,
  });

  String get settingsKey => id.name;

  static const StreamProfile lowBandwidth = StreamProfile(
    id: StreamProfileId.lowBandwidth,
    label: 'Low bandwidth / older device',
    description: 'Smaller frames, lighter JPEG, ~8 fps upload. Best for older phones or weak Wi‑Fi.',
    resolution: '640x480',
    targetFps: 8,
    jpegQuality: 55,
    cameraPreset: ResolutionPreset.low,
  );

  static const StreamProfile balanced = StreamProfile(
    id: StreamProfileId.balanced,
    label: 'Balanced',
    description: 'Default for most devices. ~12 fps upload at 720p-class capture.',
    resolution: '1280x720',
    targetFps: 12,
    jpegQuality: 70,
    cameraPreset: ResolutionPreset.medium,
  );

  static const StreamProfile highQuality = StreamProfile(
    id: StreamProfileId.highQuality,
    label: 'High quality',
    description: 'Newer phones / strong LAN. ~20 fps upload at higher capture size.',
    resolution: '1920x1080',
    targetFps: 20,
    jpegQuality: 80,
    cameraPreset: ResolutionPreset.high,
  );

  static const List<StreamProfile> all = [
    lowBandwidth,
    balanced,
    highQuality,
  ];

  static const StreamProfile defaultProfile = balanced;

  static StreamProfile fromSettingsKey(String? key) {
    if (key == null || key.isEmpty) return defaultProfile;
    for (final profile in all) {
      if (profile.settingsKey == key || profile.id.name == key) {
        return profile;
      }
    }
    // Legacy quality labels from older UI
    switch (key.toLowerCase()) {
      case 'low':
        return lowBandwidth;
      case 'high':
      case 'ultra':
        return highQuality;
      default:
        return defaultProfile;
    }
  }
}
