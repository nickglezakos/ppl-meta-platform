import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/role.dart';
import '../models/capability.dart';
import '../models/user.dart';
import '../services/roles_service.dart';
import '../api/api_client.dart';

/// State for roles management
class RolesState {
  final List<Role> roles;
  final Role? selectedRole;
  final List<Capability> selectedRoleCapabilities;
  final List<User> selectedRoleUsers;
  final bool isLoading;
  final String? error;

  const RolesState({
    this.roles = const [],
    this.selectedRole,
    this.selectedRoleCapabilities = const [],
    this.selectedRoleUsers = const [],
    this.isLoading = false,
    this.error,
  });

  RolesState copyWith({
    List<Role>? roles,
    Role? selectedRole,
    List<Capability>? selectedRoleCapabilities,
    List<User>? selectedRoleUsers,
    bool? isLoading,
    String? error,
  }) {
    return RolesState(
      roles: roles ?? this.roles,
      selectedRole: selectedRole ?? this.selectedRole,
      selectedRoleCapabilities:
          selectedRoleCapabilities ?? this.selectedRoleCapabilities,
      selectedRoleUsers: selectedRoleUsers ?? this.selectedRoleUsers,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// StateNotifier for managing roles state
class RolesNotifier extends StateNotifier<RolesState> {
  final RolesService _rolesService;

  RolesNotifier(this._rolesService) : super(const RolesState());

  /// Load all roles
  Future<void> loadRoles() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final roles = await _rolesService.getRoles();
      state = state.copyWith(roles: roles, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Select a role and load its details
  Future<void> selectRole(int roleId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final role = await _rolesService.getRoleById(roleId);
      state = state.copyWith(
        selectedRole: role,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Create a new role
  Future<void> createRole(String name) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _rolesService.createRole(name);
      await loadRoles(); // Refresh list
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Update a role's name
  Future<void> updateRole(int roleId, String newName) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final updated = await _rolesService.updateRole(roleId, newName);
      state = state.copyWith(
        selectedRole: updated,
        isLoading: false,
      );
      await loadRoles();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Delete a role
  Future<void> deleteRole(int roleId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _rolesService.deleteRole(roleId);
      state = state.copyWith(selectedRole: null, isLoading: false);
      await loadRoles();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Assign role to user
  Future<void> assignRoleToUser(int userId, int roleId) async {
    try {
      await _rolesService.assignRoleToUser(userId, roleId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Unassign role from user
  Future<void> unassignRoleFromUser(int userId, int roleId) async {
    try {
      await _rolesService.unassignRoleFromUser(userId, roleId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Add capability to role
  Future<void> addCapabilityToRole(int roleId, int capabilityId) async {
    try {
      await _rolesService.addCapabilityToRole(roleId, capabilityId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Remove capability from role
  Future<void> removeCapabilityFromRole(int roleId, int capabilityId) async {
    try {
      await _rolesService.removeCapabilityFromRole(roleId, capabilityId);
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

final rolesServiceProvider = Provider<RolesService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return RolesService(apiClient);
});

final rolesNotifierProvider =
    StateNotifierProvider<RolesNotifier, RolesState>((ref) {
  final rolesService = ref.watch(rolesServiceProvider);
  return RolesNotifier(rolesService);
});

final rolesListProvider = Provider<List<Role>>((ref) {
  return ref.watch(rolesNotifierProvider).roles;
});
