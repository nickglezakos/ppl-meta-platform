import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user.dart';
import '../services/users_service.dart';
import '../api/api_client.dart';

// State class for users
class UsersState {
  final List<User> users;
  final bool isLoading;
  final String? error;

  const UsersState({
    this.users = const [],
    this.isLoading = false,
    this.error,
  });

  UsersState copyWith({
    List<User>? users,
    bool? isLoading,
    String? error,
  }) {
    return UsersState(
      users: users ?? this.users,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// StateNotifier for managing users state
class UsersNotifier extends StateNotifier<UsersState> {
  final UsersService _usersService;

  UsersNotifier(this._usersService) : super(const UsersState());

  /// Load users from the backend
  Future<void> loadUsers({int skip = 0, int limit = 100}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final users = await _usersService.getUsers(skip: skip, limit: limit);
      state = state.copyWith(
        users: users,
        isLoading: false,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Refresh users list
  Future<void> refreshUsers() async {
    await loadUsers();
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Provider for users service
final usersServiceProvider = Provider<UsersService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UsersService(apiClient);
});

// Provider for users notifier
final usersNotifierProvider = StateNotifierProvider<UsersNotifier, UsersState>((ref) {
  final usersService = ref.watch(usersServiceProvider);
  return UsersNotifier(usersService);
});

// Computed provider for users list
final usersListProvider = Provider<List<User>>((ref) {
  return ref.watch(usersNotifierProvider).users;
});

// Computed provider for loading state
final usersLoadingProvider = Provider<bool>((ref) {
  return ref.watch(usersNotifierProvider).isLoading;
});

// Computed provider for error state
final usersErrorProvider = Provider<String?>((ref) {
  return ref.watch(usersNotifierProvider).error;
});
