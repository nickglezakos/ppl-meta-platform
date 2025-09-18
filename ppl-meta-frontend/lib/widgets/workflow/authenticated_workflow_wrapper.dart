import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/services/auth_service.dart';
import '../../core/models/user.dart';
import '../../services/workflow_widget_api_client.dart';

/// Provider for WorkflowWidgetApiClient with authentication integration
final workflowWidgetApiClientProvider = Provider<WorkflowWidgetApiClient?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  if (authState.isAuthenticated && authState.user != null) {
    // Create auth manager wrapper using current auth service  
    final authService = ref.watch(authServiceProvider);
    final authManager = _WorkflowAuthManagerAdapter(authService, ref);
    return WorkflowWidgetApiClient(authManager: authManager);
  }
  return null;
});

/// Provider for authentication status watching
final authenticationStatusProvider = Provider<bool>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.isAuthenticated;
});

/// Provider for current user UUID - connects workflow widgets to auth system
final workflowCurrentUserProvider = Provider<String?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  final user = authState.user;
  return user?.id.toString(); // Use user ID as UUID
});

/// Provider for current auth token - connects workflow widgets to auth system
final workflowAuthTokenProvider = FutureProvider<String?>((ref) async {
  final authService = ref.watch(authServiceProvider);
  return await authService.getToken();
});

/// Adapter class that provides AuthManager-like interface using AuthService
class _WorkflowAuthManagerAdapter {
  final AuthService _authService;
  final Ref _ref;

  _WorkflowAuthManagerAdapter(this._authService, this._ref);

  /// Check if user is authenticated
  bool get isAuthenticated {
    final authState = _ref.read(authNotifierProvider);
    return authState.isAuthenticated;
  }

  /// Current authentication token (sync getter - cached)
  String? get token {
    // For workflow widget compatibility, return null here as we handle async token fetching
    return null;
  }

  /// Get current user UUID
  String? get currentUserUuid {
    final authState = _ref.read(authNotifierProvider);
    return authState.user?.id.toString();
  }

  /// Get authentication token (async method)
  Future<String?> getToken() async {
    try {
      return await _authService.getToken();
    } catch (e) {
      debugPrint('🔓 WorkflowAuthAdapter: Error getting token: $e');
      return null;
    }
  }

  /// Get current user
  User? get currentUser {
    final authState = _ref.read(authNotifierProvider);
    return authState.user;
  }

  /// Get user data as Map (for compatibility)
  Map<String, dynamic>? get userData {
    final user = currentUser;
    if (user == null) return null;
    return {
      'id': user.id,
      'username': user.username,
      'email': user.email,
      'email_verified': user.emailVerified,
      'created_at': user.createdAt?.toIso8601String(),
      'updated_at': user.updatedAt?.toIso8601String(),
    };
  }

  /// Login method
  Future<bool> login(String email, String password) async {
    final authNotifier = _ref.read(authNotifierProvider.notifier);
    return await authNotifier.login(email, password);
  }

  /// Logout method
  Future<void> logout() async {
    final authNotifier = _ref.read(authNotifierProvider.notifier);
    await authNotifier.logout();
  }

  /// For duck typing compatibility - some AuthManager methods
  String? get userEmail => currentUser?.email;
  String? get username => currentUser?.username;
  DateTime? get lastLoginTime => currentUser?.updatedAt;
  bool get hasValidToken => isAuthenticated;
}

/// Wrapper widget that handles authentication state for workflow widgets
class AuthenticatedWorkflowWrapper extends ConsumerWidget {
  final Widget child;
  final Widget? loadingWidget;
  final Widget? unauthenticatedWidget;
  final bool requiresAuth;

  const AuthenticatedWorkflowWrapper({
    super.key,
    required this.child,
    this.loadingWidget,
    this.unauthenticatedWidget,
    this.requiresAuth = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    
    // If authentication is not required, always show child
    if (!requiresAuth) {
      return child;
    }

    // Show loading state while checking authentication
    if (authState.isLoading) {
      return loadingWidget ?? const _DefaultLoadingWidget();
    }

    // Show unauthenticated state if not logged in
    if (!authState.isAuthenticated) {
      return unauthenticatedWidget ?? const _DefaultUnauthenticatedWidget();
    }

    // User is authenticated, show the child widget
    return child;
  }
}

/// Mixin for widgets that need authentication handling
mixin AuthenticatedWorkflowMixin<T extends ConsumerStatefulWidget> on ConsumerState<T> {
  WorkflowWidgetApiClient? _apiClient;

  /// Initialize API client with authentication
  void initializeApiClient() {
    _apiClient = ref.read(workflowWidgetApiClientProvider);
  }

  /// Get the current API client
  WorkflowWidgetApiClient? get apiClient => _apiClient;

  /// Check if user is authenticated
  bool get isAuthenticated => ref.read(authenticationStatusProvider);

  /// Get current user UUID
  String? get currentUserUuid => ref.read(workflowCurrentUserProvider);

  /// Listen to authentication changes
  void listenToAuthChanges() {
    ref.listen<bool>(authenticationStatusProvider, (previous, current) {
      if (current != previous) {
        onAuthenticationChanged(current);
      }
    });
  }

  /// Override this method to handle authentication changes
  void onAuthenticationChanged(bool isAuthenticated) {
    if (isAuthenticated) {
      initializeApiClient();
    } else {
      _apiClient?.dispose();
      _apiClient = null;
    }
  }

  @override
  void initState() {
    super.initState();
    initializeApiClient();
    listenToAuthChanges();
  }

  @override
  void dispose() {
    _apiClient?.dispose();
    super.dispose();
  }
}

/// Builder widget for authentication-aware workflow widgets
class AuthenticatedWorkflowBuilder extends ConsumerWidget {
  final Widget Function(BuildContext context, WorkflowWidgetApiClient apiClient, String userUuid) builder;
  final Widget Function(BuildContext context)? loadingBuilder;
  final Widget Function(BuildContext context)? unauthenticatedBuilder;
  final Widget Function(BuildContext context, String error)? errorBuilder;

  const AuthenticatedWorkflowBuilder({
    super.key,
    required this.builder,
    this.loadingBuilder,
    this.unauthenticatedBuilder,
    this.errorBuilder,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final isAuthenticated = ref.watch(authenticationStatusProvider);
    final apiClient = ref.watch(workflowWidgetApiClientProvider);
    final userUuid = ref.watch(workflowCurrentUserProvider);

    // Show loading state
    if (authState.isLoading) {
      return loadingBuilder?.call(context) ?? const _DefaultLoadingWidget();
    }

    // Show unauthenticated state
    if (!isAuthenticated) {
      return unauthenticatedBuilder?.call(context) ?? const _DefaultUnauthenticatedWidget();
    }

    // Check for API client and user UUID
    if (apiClient == null || userUuid == null) {
      return errorBuilder?.call(context, 'Authentication configuration error') ??
          const _DefaultErrorWidget(error: 'Authentication configuration error');
    }

    // Build authenticated widget
    return builder(context, apiClient, userUuid);
  }
}

/// Simplified wrapper for workflow widgets with authentication
class WorkflowWidgetWrapper extends StatelessWidget {
  final Widget Function(WorkflowWidgetApiClient apiClient, String userUuid) builder;
  final String? title;
  final bool showAppBar;

  const WorkflowWidgetWrapper({
    super.key,
    required this.builder,
    this.title,
    this.showAppBar = false,
  });

  @override
  Widget build(BuildContext context) {
    return AuthenticatedWorkflowBuilder(
      builder: (context, apiClient, userUuid) {
        final widget = builder(apiClient, userUuid);
        
        if (showAppBar && title != null) {
          return Scaffold(
            appBar: AppBar(
              title: Text(title!),
              backgroundColor: Theme.of(context).colorScheme.inversePrimary,
            ),
            body: widget,
          );
        }
        
        return widget;
      },
      loadingBuilder: (context) => _buildScaffoldWrapper(
        context,
        const _DefaultLoadingWidget(),
      ),
      unauthenticatedBuilder: (context) => _buildScaffoldWrapper(
        context,
        const _DefaultUnauthenticatedWidget(),
      ),
      errorBuilder: (context, error) => _buildScaffoldWrapper(
        context,
        _DefaultErrorWidget(error: error),
      ),
    );
  }

  Widget _buildScaffoldWrapper(BuildContext context, Widget child) {
    if (showAppBar && title != null) {
      return Scaffold(
        appBar: AppBar(
          title: Text(title!),
          backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        ),
        body: child,
      );
    }
    return child;
  }
}

/// Token refresh handler for workflow widgets
class WorkflowTokenRefreshHandler extends ConsumerWidget {
  final Widget child;

  const WorkflowTokenRefreshHandler({
    Key? key,
    required this.child,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final authTokenAsync = ref.watch(workflowAuthTokenProvider);
    
    return authTokenAsync.when(
      data: (token) {
        if (token == null || authState.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        return child;
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error, color: Colors.red),
            Text('Authentication Error: $error'),
            ElevatedButton(
              onPressed: () => ref.refresh(workflowAuthTokenProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Default loading widget
class _DefaultLoadingWidget extends StatelessWidget {
  const _DefaultLoadingWidget();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Authenticating...'),
        ],
      ),
    );
  }
}

/// Default unauthenticated widget
class _DefaultUnauthenticatedWidget extends StatelessWidget {
  const _DefaultUnauthenticatedWidget();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.lock_outline,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'Authentication Required',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Please log in to access workflow features',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey[500],
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              // Navigate to login page
              Navigator.of(context).pushNamed('/login');
            },
            icon: const Icon(Icons.login),
            label: const Text('Log In'),
          ),
        ],
      ),
    );
  }
}

/// Default error widget
class _DefaultErrorWidget extends StatelessWidget {
  final String error;

  const _DefaultErrorWidget({
    required this.error,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red[400],
          ),
          const SizedBox(height: 16),
          Text(
            'Authentication Error',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.red[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () {
              // Retry authentication
              Navigator.of(context).pushReplacementNamed('/login');
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red[400],
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}