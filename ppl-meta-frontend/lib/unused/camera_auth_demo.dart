import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/camera_service_providers.dart';
import 'screens/camera_auth_demo_screen.dart';

/// Camera Authentication Demo App
/// 
/// Demonstrates CAM-FLUTTER-001 implementation
/// Tests cross-service JWT authentication flow
void main() {
  runApp(const CameraAuthDemoApp());
}

class CameraAuthDemoApp extends StatelessWidget {
  const CameraAuthDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return CameraServiceProviders(
      child: MaterialApp(
        title: 'PPL Meta Camera Auth Demo',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
          useMaterial3: true,
        ),
        home: const CameraAuthDemoScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
