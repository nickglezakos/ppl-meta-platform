import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

/// Authentication state
class AuthState {
  final User? user;
  final bool isLoading;
  final String? error;
  final bool isAuthenticated;

  const AuthState({
    this.user,
    this.isLoading = false,
    this.error,
    this.isAuthenticated = false,
  });

  const AuthState.unauthenticated()
      : user = null,
        isLoading = false,
        error = null,
        isAuthenticated = false;

  const AuthState.authenticated(this.user)
      : isLoading = false,
        error = null,
        isAuthenticated = true;

  AuthState copyWith({
    User? user,
    bool? isLoading,
    String? error,
    bool? isAuthenticated,
  }) {
    return AuthState(
      user: user ?? this.user,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AuthState &&
        other.user == user &&
        other.isLoading == isLoading &&
        other.error == error &&
        other.isAuthenticated == isAuthenticated;
  }

  @override
  int get hashCode {
    return Object.hash(user, isLoading, error, isAuthenticated);
  }

  @override
  String toString() {
    return 'AuthState(user: $user, isLoading: $isLoading, error: $error, isAuthenticated: $isAuthenticated)';
  }
}

/// Authentication state notifier
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final Logger _logger = Logger();

  AuthNotifier(this._authService) : super(const AuthState.unauthenticated()) {
    _logger.i('AuthNotifier: Constructor called, initial state: unauthenticated');
    // Initialize authentication automatically
    _initializeAuth();
  }

  /// Initialize authentication service and check current status
  Future<void> _initializeAuth() async {
    _logger.i('AuthNotifier: _initializeAuth() started');
    try {
      await _authService.initialize();
      _logger.i('AuthNotifier: AuthService initialized successfully');
      await checkAuth();
      _logger.i('AuthNotifier: Initial auth check completed');
    } catch (e) {
      _logger.e('AuthNotifier: _initializeAuth() failed: $e');
    }
  }

  /// Check current authentication status
  Future<void> checkAuth() async {
    _logger.i('AuthNotifier: checkAuth() called, current state: ${state.toString()}');
    
    try {
      final token = await _authService.getToken();
      _logger.i('AuthNotifier: Retrieved token from storage: ${token != null ? 'EXISTS (${token.length} chars)' : 'NULL'}');
      
      if (token == null) {
        _logger.w('AuthNotifier: No token found, setting unauthenticated');
        state = const AuthState.unauthenticated();
        return;
      }

      final user = await _authService.getCurrentUser();
      _logger.i('AuthNotifier: Current user: ${user != null ? 'FOUND (${user.username})' : 'NULL'}');
      
      if (user != null) {
        _logger.i('AuthNotifier: Authentication valid, setting authenticated state');
        state = AuthState.authenticated(user);
      } else {
        _logger.w('AuthNotifier: User is null despite having token, setting unauthenticated');
        state = const AuthState.unauthenticated();
      }
    } catch (e) {
      _logger.e('AuthNotifier: checkAuth error: $e');
      state = const AuthState.unauthenticated();
    }
  }

  /// Login with email and password
  Future<bool> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      await _authService.login(email, password);
      
      // After successful login, fetch the user profile
      final user = await _authService.getCurrentUser();
      _logger.i('AuthNotifier: User fetched after login: ${user != null ? 'FOUND (${user.username})' : 'NULL'}');
      
      if (user != null) {
        state = AuthState.authenticated(user);
        _logger.i('AuthNotifier: Login successful, user authenticated');
      } else {
        _logger.w('AuthNotifier: Login successful but failed to fetch user profile');
        state = state.copyWith(
          isAuthenticated: true,
          isLoading: false,
        );
      }
      return true;
    } catch (e) {
      _logger.e('AuthNotifier: Login error: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Register new user
  Future<bool> register(String username, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final user = await _authService.register(username, email, password);
      // After registration, user needs to verify email, so don't auto-login
      state = state.copyWith(
        isLoading: false,
        error: null,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Logout user
  Future<void> logout() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      await _authService.logout();
      state = const AuthState(
        user: null,
        isAuthenticated: false,
        isLoading: false,
      );
    } catch (e) {
      // Even if logout fails on backend, clear local state
      state = const AuthState(
        user: null,
        isAuthenticated: false,
        isLoading: false,
      );
    }
  }

  /// Clear error state
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Change user password
  Future<bool> changePassword(String currentPassword, String newPassword) async {
    try {
      await _authService.changePassword(currentPassword, newPassword);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Refresh user data
  Future<void> refreshUser() async {
    if (!state.isAuthenticated) return;

    try {
      final user = await _authService.getCurrentUser();
      if (user != null) {
        state = state.copyWith(user: user);
      } else {
        // User not found, logout
        await logout();
      }
    } catch (e) {
      // If refresh fails, logout user
      await logout();
    }
  }
}

/// Provider for authentication state
final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final authService = ref.watch(authServiceProvider);
  ref.keepAlive(); // Prevent this provider from being disposed
  return AuthNotifier(authService);
}, name: 'authNotifier');

/// Convenience provider for current user
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.user;
});

/// Convenience provider for authentication status
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.isAuthenticated;
});
