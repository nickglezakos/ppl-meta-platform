import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_provider.dart';

/// Basic features configuration
class AppFeatures {
  final bool visionCapability;
  final bool faceDetectionEnabled;
  final bool workflowsEnabled;
  final bool cameraIntegrationEnabled;

  const AppFeatures({
    this.visionCapability = true,
    this.faceDetectionEnabled = true,
    this.workflowsEnabled = true,
    this.cameraIntegrationEnabled = true,
  });
}

/// Provider for app features configuration
final featuresProvider = Provider<AppFeatures>((ref) {
  return const AppFeatures(
    visionCapability: true,
    faceDetectionEnabled: true,
    workflowsEnabled: true,
    cameraIntegrationEnabled: true,
  );
});

/// Provider that checks if the current user has media viewing capability
final mediaViewingEnabledProvider = Provider<bool>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.user?.canViewMedia ?? false;
});