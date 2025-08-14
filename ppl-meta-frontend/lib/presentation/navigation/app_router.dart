import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/provider_bridge.dart';
import '../screens/auth/new_login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/users/users_screen.dart';
import '../screens/cameras/cameras_screen.dart';
import '../screens/cameras/camera_detail_screen.dart';
import '../screens/camera/snapshot_gallery_screen.dart';
import '../../screens/upload_screen.dart';
import '../../screens/gallery_screen.dart';
import '../../screens/analytics_screen.dart';
import '../../screens/collections_screen.dart';
import '../../screens/profile_screen.dart';
import '../../screens/features_screen.dart';
import '../../screens/media_preview_screen.dart';
import '../../screens/camera_media_sync_screen.dart';
import '../../models/media_models.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);
  
  return GoRouter(
    initialLocation: '/home', // Set a default, let redirect handle authentication
    redirect: (context, state) {
      final isAuthenticated = authState.isAuthenticated;
      final isLoginRoute = state.fullPath == '/login';
      final isRegisterRoute = state.fullPath == '/register';
      
      print('Router redirect - path: ${state.fullPath}, isAuthenticated: $isAuthenticated');
      
      // If not authenticated and trying to access protected routes, redirect to login
      if (!isAuthenticated && !isLoginRoute && !isRegisterRoute) {
        print('Redirecting to login - not authenticated');
        return '/login';
      }
      
      // If authenticated and trying to access auth routes, redirect to home
      if (isAuthenticated && (isLoginRoute || isRegisterRoute)) {
        print('Redirecting to home - already authenticated');
        return '/home';
      }
      
      print('No redirect needed - staying on: ${state.fullPath}');
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
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/features',
        name: 'features',
        builder: (context, state) => const FeaturesScreen(),
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
          child: CamerasScreen(),
        ),
      ),
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
        path: '/snapshots',
        name: 'snapshots',
        builder: (context, state) => const ProviderScreenWrapper(
          child: SnapshotGalleryScreen(),
        ),
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
        path: '/media-preview',
        name: 'media-preview',
        builder: (context, state) {
          final mediaItem = state.extra as MediaItem?;
          if (mediaItem == null) {
            return const Scaffold(
              body: Center(
                child: Text('Media item not found'),
              ),
            );
          }
          return ProviderScreenWrapper(
            child: MediaPreviewScreen(mediaItem: mediaItem),
          );
        },
      ),
      GoRoute(
        path: '/camera-media-sync',
        name: 'camera-media-sync',
        builder: (context, state) => ProviderScreenWrapper(
          child: CameraMediaSyncScreen(),
        ),
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
