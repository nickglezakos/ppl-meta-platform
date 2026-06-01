import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/provider_bridge.dart';
import '../../core/services/secure_storage_service.dart';
import '../screens/auth/new_login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/auth/forgot_password_screen.dart';
import '../screens/auth/reset_password_screen.dart';
import '../screens/auth/verify_email_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/users/users_screen.dart';
import '../screens/cameras/cameras_screen.dart';
import '../screens/cameras/camera_detail_screen.dart';
import '../screens/cameras/edge_camera_management_screen.dart';
import '../screens/camera/snapshot_gallery_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../../screens/upload_screen.dart';
import '../../screens/gallery_screen.dart';
import '../../screens/analytics_screen.dart';
import '../../screens/collections_screen.dart';
import '../../screens/profile_screen.dart';
import '../../screens/features_screen.dart';
import '../../screens/media_preview_screen.dart';
// ARCHIVED: import '../../screens/camera_media_sync_screen.dart';
import '../../screens/workflow_dashboard_screen.dart';
import '../../screens/automation_screen.dart';
import '../../screens/signage_management_screen.dart';
import '../../screens/triggers_screen.dart';
import '../../screens/individual_groups_screen.dart';
import '../../screens/individual_group_detail_screen.dart';
import '../../screens/presence_screen.dart';
import '../../screens/storage_screen.dart';
import '../../screens/network_screen.dart';
// ARCHIVED: import '../../features/cameras/pages/multi_camera_page.dart';
import '../../models/media_models.dart';
import '../../pages/workflow_widget_test_page.dart';
// ARCHIVED: import '../../pages/enhanced_multi_camera_page.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);
  
  return GoRouter(
    initialLocation: '/home', // Set a default, let redirect handle authentication
    redirect: (context, state) async {
      final storedToken = await SecureStorageService.getString('auth_token');
      final isAuthenticated = authState.isAuthenticated &&
          storedToken != null &&
          storedToken.isNotEmpty;
      final isLoginRoute = state.fullPath == '/login';
      final isRegisterRoute = state.fullPath == '/register';
      final isPublicRoute = state.fullPath == '/forgot-password' ||
          (state.fullPath?.startsWith('/reset-password') ?? false) ||
          (state.fullPath?.startsWith('/verify-email') ?? false);
      
      // If not authenticated and trying to access protected routes, redirect to login
      if (!isAuthenticated && !isLoginRoute && !isRegisterRoute && !isPublicRoute) {
        return '/login';
      }
      
      // If authenticated and trying to access auth routes, redirect to home
      if (isAuthenticated && (isLoginRoute || isRegisterRoute)) {
        return '/home';
      }

      return null; // No redirect needed
    },
    routes: [
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const NewLoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/forgot-password',
        name: 'forgot-password',
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: '/reset-password',
        name: 'reset-password',
        builder: (context, state) {
          final token = state.uri.queryParameters['token'] ?? '';
          return ResetPasswordScreen(token: token);
        },
      ),
      GoRoute(
        path: '/verify-email',
        name: 'verify-email',
        builder: (context, state) {
          final token = state.uri.queryParameters['token'] ?? '';
          return VerifyEmailScreen(token: token);
        },
      ),
      GoRoute(
        path: '/home',
        name: 'home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/upload',
        name: 'upload',
        builder: (context, state) => const ProviderScreenWrapper(
          child: UploadScreen(),
        ),
      ),
      GoRoute(
        path: '/gallery',
        name: 'gallery',
        builder: (context, state) => const ProviderScreenWrapper(
          child: GalleryScreen(),
        ),
      ),
      GoRoute(
        path: '/analytics',
        name: 'analytics',
        builder: (context, state) => const ProviderScreenWrapper(
          child: AnalyticsScreen(),
        ),
      ),
      GoRoute(
        path: '/collections',
        name: 'collections',
        builder: (context, state) {
          final initialCollectionId = state.uri.queryParameters['initialCollectionId'];
          return ProviderScreenWrapper(
            child: CollectionsScreen(initialCollectionId: initialCollectionId),
          );
        },
      ),
      GoRoute(
        path: '/profile',
        name: 'profile',
        builder: (context, state) {
          final userIdParam = state.uri.queryParameters['userId'];
          final targetUserId = userIdParam != null ? int.tryParse(userIdParam) : null;
          return ProfileScreen(targetUserId: targetUserId);
        },
      ),
      GoRoute(
        path: '/features',
        name: 'features',
        builder: (context, state) => const FeaturesScreen(),
      ),
      GoRoute(
        path: '/workflows',
        name: 'workflows',
        builder: (context, state) => const ProviderScreenWrapper(
          child: WorkflowDashboardScreen(),
        ),
      ),
      GoRoute(
        path: '/workflow-test',
        name: 'workflow-test',
        builder: (context, state) => const ProviderScreenWrapper(
          child: WorkflowWidgetTestPage(),
        ),
      ),
      GoRoute(
        path: '/automation',
        name: 'automation',
        builder: (context, state) => const ProviderScreenWrapper(
          child: AutomationScreen(),
        ),
      ),
      GoRoute(
        path: '/users',
        name: 'users',
        builder: (context, state) => const ProviderScreenWrapper(
          child: UsersScreen(),
        ),
      ),
      GoRoute(
        path: '/cameras',
        name: 'cameras',
        builder: (context, state) => const ProviderScreenWrapper(
          child: CamerasScreen(), // Using new cameras screen
        ),
      ),
      /* ARCHIVED: Enhanced multi camera page
      GoRoute(
        path: '/cameras-enhanced',
        name: 'cameras-enhanced',
        builder: (context, state) => const ProviderScreenWrapper(
          child: EnhancedMultiCameraPage(),
        ),
      ), */
      GoRoute(
        path: '/cameras/:cameraId',
        name: 'camera-detail',
        builder: (context, state) {
          final cameraId = state.pathParameters['cameraId']!;
          return ProviderScreenWrapper(
            child: CameraDetailScreen(cameraId: cameraId),
          );
        },
      ),
      GoRoute(
        path: '/cameras/:cameraId/snapshots',
        name: 'camera-snapshots',
        builder: (context, state) {
          final cameraId = state.pathParameters['cameraId']!;
          return ProviderScreenWrapper(
            child: SnapshotGalleryScreen(
              cameraId: cameraId,
              title: 'Camera Snapshots',
            ),
          );
        },
      ),
      GoRoute(
        path: '/edge-cameras/:deviceId',
        name: 'edge-camera-management',
        builder: (context, state) {
          final deviceId = state.pathParameters['deviceId']!;
          final cameraName = state.uri.queryParameters['name'] ?? 'Edge Camera';
          return ProviderScreenWrapper(
            child: EdgeCameraManagementScreen(
              deviceId: deviceId,
              cameraName: cameraName,
            ),
          );
        },
      ),
      GoRoute(
        path: '/media-preview',
        name: 'media-preview',
        builder: (context, state) {
          final mediaItem = state.extra as MediaItem?;
          final collectionId = state.uri.queryParameters['collectionId'];
          if (mediaItem == null) {
            return const Scaffold(
              body: Center(
                child: Text('Media item not found'),
              ),
            );
          }
          return ProviderScreenWrapper(
            child: EnhancedMediaPreviewScreen(
              mediaItem: mediaItem,
              collectionId: collectionId,
            ),
          );
        },
      ),
      GoRoute(
        path: '/media-preview/:videoUuid',
        name: 'media-preview-by-uuid',
        builder: (context, state) {
          final videoUuid = state.pathParameters['videoUuid']!;
          // Create a minimal MediaItem with just the UUID
          // The screen will fetch the full details from the API
          final mediaItem = MediaItem(
            mediaId: '0', // Placeholder - will be loaded from API
            uuid: videoUuid,
            originalFilename: 'Loading...',
            mediaType: MediaType.video,
            fileSize: 0,
            filePath: '',
            uploadedAt: DateTime.now(),
            isPublic: false,
          );
          return ProviderScreenWrapper(
            child: EnhancedMediaPreviewScreen(mediaItem: mediaItem),
          );
        },
      ),
      /* ARCHIVED: Camera media sync screen
      GoRoute(
        path: '/camera-media-sync',
        name: 'camera-media-sync',
        builder: (context, state) => ProviderScreenWrapper(
          child: CameraMediaSyncScreen(),
        ),
      ), */
      GoRoute(
        path: '/signage',
        name: 'signage',
        builder: (context, state) => const ProviderScreenWrapper(
          child: SignageManagementScreen(),
        ),
      ),
      GoRoute(
        path: '/triggers',
        name: 'triggers',
        builder: (context, state) => const ProviderScreenWrapper(
          child: TriggersScreen(),
        ),
      ),
      GoRoute(
        path: '/presence',
        name: 'presence',
        builder: (context, state) => const ProviderScreenWrapper(
          child: PresenceScreen(),
        ),
      ),
      GoRoute(
        path: '/presence-station',
        name: 'presence-station',
        builder: (context, state) => const ProviderScreenWrapper(
          child: PresenceScreen(stationMode: true),
        ),
      ),
      GoRoute(
        path: '/individual-groups',
        name: 'individual-groups',
        builder: (context, state) => const ProviderScreenWrapper(
          child: IndividualGroupsScreen(),
        ),
      ),
      GoRoute(
        path: '/individual-groups/:groupId',
        name: 'individual-group-detail',
        builder: (context, state) {
          final groupId = state.pathParameters['groupId']!;
          return ProviderScreenWrapper(
            child: IndividualGroupDetailScreen(groupId: groupId),
          );
        },
      ),
      GoRoute(
        path: '/storage',
        name: 'storage',
        builder: (context, state) => const StorageScreen(),
      ),
      GoRoute(
        path: '/network',
        name: 'network',
        builder: (context, state) => const NetworkScreen(),
      ),
      GoRoute(
        path: '/settings',
        name: 'settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      // Root route redirects based on auth status
      GoRoute(
        path: '/',
        name: 'root',
        redirect: (context, state) {
          return authState.isAuthenticated ? '/home' : '/login';
        },
        builder: (context, state) => const SizedBox.shrink(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('Error')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Page not found: ${state.uri.path}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => context.go('/'),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    ),
  );
});
