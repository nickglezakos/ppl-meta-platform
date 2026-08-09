import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/capability.dart';
import '../services/capabilities_service.dart';
import '../api/api_client.dart';

/// State for capabilities management
class CapabilitiesState {
  final List<Capability> allCapabilities;
  final List<String> myCapabilities;
  final bool isLoading;
  final String? error;

  const CapabilitiesState({
    this.allCapabilities = const [],
    this.myCapabilities = const [],
    this.isLoading = false,
    this.error,
  });

  CapabilitiesState copyWith({
    List<Capability>? allCapabilities,
    List<String>? myCapabilities,
    bool? isLoading,
    String? error,
  }) {
    return CapabilitiesState(
      allCapabilities: allCapabilities ?? this.allCapabilities,
      myCapabilities: myCapabilities ?? this.myCapabilities,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// StateNotifier for managing capabilities state
class CapabilitiesNotifier extends StateNotifier<CapabilitiesState> {
  final CapabilitiesService _capabilitiesService;

  CapabilitiesNotifier(this._capabilitiesService) : super(const CapabilitiesState());

  /// Load the current user's own capabilities
  Future<void> loadMyCapabilities() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final data = await _capabilitiesService.getMyCapabilities();
      final caps = (data['capabilities'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [];
      state = state.copyWith(myCapabilities: caps, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Load capabilities for a specific role
  Future<List<Capability>> getCapabilitiesByRole(int roleId) async {
    try {
      return await _capabilitiesService.getCapabilitiesByRole(roleId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// ── Providers ──────────────────────────────────────────────────

final capabilitiesServiceProvider = Provider<CapabilitiesService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CapabilitiesService(apiClient);
});

final capabilitiesNotifierProvider =
    StateNotifierProvider<CapabilitiesNotifier, CapabilitiesState>((ref) {
  final svc = ref.watch(capabilitiesServiceProvider);
  return CapabilitiesNotifier(svc);
});
