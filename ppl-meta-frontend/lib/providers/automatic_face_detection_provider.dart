import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers/features_provider.dart';

/// Provider for automatic face detection global setting status
final automaticFaceDetectionProvider = StateNotifierProvider<AutomaticFaceDetectionNotifier, AutomaticFaceDetectionState>(
  (ref) => AutomaticFaceDetectionNotifier(ref),
);

/// State for automatic face detection system
class AutomaticFaceDetectionState {
  final bool isGloballyEnabled;
  final DateTime? lastUpdated;
  final String? error;

  const AutomaticFaceDetectionState({
    this.isGloballyEnabled = false,
    this.lastUpdated,
    this.error,
  });

  AutomaticFaceDetectionState copyWith({
    bool? isGloballyEnabled,
    DateTime? lastUpdated,
    String? error,
  }) {
    return AutomaticFaceDetectionState(
      isGloballyEnabled: isGloballyEnabled ?? this.isGloballyEnabled,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      error: error ?? this.error,
    );
  }
}

/// Notifier for automatic face detection system
/// This tracks the global setting state and provides status information
class AutomaticFaceDetectionNotifier extends StateNotifier<AutomaticFaceDetectionState> {
  final Ref ref;

  AutomaticFaceDetectionNotifier(this.ref) : super(const AutomaticFaceDetectionState()) {
    // Listen to features provider changes to sync global setting state
    ref.listen(featuresNotifierProvider, (previous, next) {
      next.whenData((featuresState) {
        if (state.isGloballyEnabled != featuresState.faceDetectionOnSaveEnabled) {
          state = state.copyWith(
            isGloballyEnabled: featuresState.faceDetectionOnSaveEnabled,
            lastUpdated: DateTime.now(),
            error: null,
          );
        }
      });
    });
  }

  /// Get the current global setting status
  bool get isEnabled => state.isGloballyEnabled;

  /// Get status information for display
  Map<String, dynamic> getStatusInfo() {
    return {
      'enabled': state.isGloballyEnabled,
      'lastUpdated': state.lastUpdated?.toIso8601String(),
      'status': state.isGloballyEnabled 
        ? 'Camera recordings will automatically trigger face detection'
        : 'Automatic face detection on save is disabled',
    };
  }

  /// Manually refresh the setting state from features provider
  void refreshStatus() {
    final featuresState = ref.read(featuresNotifierProvider).value;
    if (featuresState != null) {
      state = state.copyWith(
        isGloballyEnabled: featuresState.faceDetectionOnSaveEnabled,
        lastUpdated: DateTime.now(),
        error: null,
      );
    }
  }
}