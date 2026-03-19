import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/camera_auth_service.dart';
import '../services/camera_service.dart';

/// Service Providers Setup for Camera Authentication
/// 
/// Configures Provider pattern for dependency injection and state management
/// Ensures proper service lifecycle and dependency resolution
class CameraServiceProviders extends StatelessWidget {
  final Widget child;

  const CameraServiceProviders({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Camera Authentication Service (primary dependency)
        ChangeNotifierProvider<CameraAuthService>(
          create: (context) => CameraAuthService(),
          lazy: false, // Initialize immediately for token restoration
        ),
        
        // Camera Service (depends on CameraAuthService)
        ChangeNotifierProxyProvider<CameraAuthService, CameraService>(
          create: (context) => CameraService(
            Provider.of<CameraAuthService>(context, listen: false),
          ),
          update: (context, authService, previousCameraService) {
            // Return existing service if auth service hasn't changed
            return previousCameraService ?? CameraService(authService);
          },
        ),
      ],
      child: child,
    );
  }
}
