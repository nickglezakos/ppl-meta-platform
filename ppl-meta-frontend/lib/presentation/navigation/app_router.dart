import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/providers/provider_bridge.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/home/home_screen.dart';
import '../../screens/upload_screen.dart';
import '../../screens/gallery_screen.dart';
import '../../screens/analytics_screen.dart';
import '../../screens/collections_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);
  
  return GoRouter(
    initialLocation: authState.isAuthenticated ? '/home' : '/login',
    redirect: (context, state) {
      final isAuthenticated = authState.isAuthenticated;
      final isLoginRoute = state.fullPath == '/login';
      final isRegisterRoute = state.fullPath == '/register';
      
      // If not authenticated and trying to access protected routes, redirect to login
      if (!isAuthenticated && !isLoginRoute && !isRegisterRoute) {
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
        builder: (context, state) => const LoginScreen(),
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
        builder: (context, state) => const ProviderScreenWrapper(
          child: CollectionsScreen(),
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
