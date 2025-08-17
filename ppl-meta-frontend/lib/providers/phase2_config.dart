import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../core/services/camera_service.dart';
import '../providers/phase2_providers.dart' as phase2;

/// Provider overrides configuration for Phase 2 dependency injection
/// 
/// This class handles the initialization and configuration of all
/// Phase 2 providers with proper dependency injection.
class Phase2ProvidersConfig {
  
  /// Initialize all required dependencies and return provider overrides
  static Future<List<Override>> createOverrides() async {
    // Initialize SharedPreferences
    final sharedPreferences = await SharedPreferences.getInstance();
    
    // Initialize ApiClient first
    final apiClient = ApiClient(AppConfig.instance);
    
    // Initialize CameraService (from Phase 1)
    final cameraService = CameraService(apiClient);
    
    return [
      // Core dependency overrides
      phase2.sharedPreferencesProvider.overrideWithValue(sharedPreferences),
      phase2.cameraServiceProvider.overrideWithValue(cameraService),
    ];
  }
  
  /// Create a ProviderScope with Phase 2 configuration
  static Future<Widget> createProviderScope({
    required Widget child,
  }) async {
    final overrides = await createOverrides();
    
    return ProviderScope(
      overrides: overrides,
      child: child,
    );
  }
  
  /// Initialize Phase 2 services after provider scope is created
  static Future<void> initializeServices(WidgetRef ref) async {
    try {
      // Initialize sync service
      final syncService = ref.read(phase2.snapshotSyncServiceProvider);
      await syncService.initialize();
      
      // Start background sync if enabled
      final backgroundSyncEnabled = ref.read(phase2.backgroundSyncEnabledProvider);
      if (backgroundSyncEnabled) {
        await syncService.startBackgroundSync();
      }
      
      // Initialize gallery service cache
      final galleryService = ref.read(phase2.enhancedGalleryServiceProvider);
      await galleryService.initializeCache();
      
      print('✅ Phase 2 services initialized successfully');
    } catch (e) {
      print('❌ Failed to initialize Phase 2 services: $e');
      rethrow;
    }
  }
  
  /// Cleanup Phase 2 services on app shutdown
  static Future<void> cleanup(WidgetRef ref) async {
    try {
      // Stop background sync
      final syncService = ref.read(phase2.snapshotSyncServiceProvider);
      await syncService.stopBackgroundSync();
      
      // Clear caches
      final galleryService = ref.read(phase2.enhancedGalleryServiceProvider);
      await galleryService.clearCache();
      
      print('✅ Phase 2 services cleaned up successfully');
    } catch (e) {
      print('❌ Failed to cleanup Phase 2 services: $e');
    }
  }
}

/// Phase 2 initialization widget that sets up providers and services
class Phase2InitializationWidget extends ConsumerStatefulWidget {
  final Widget child;
  
  const Phase2InitializationWidget({
    super.key,
    required this.child,
  });
  
  @override
  ConsumerState<Phase2InitializationWidget> createState() => 
      _Phase2InitializationWidgetState();
}

class _Phase2InitializationWidgetState 
    extends ConsumerState<Phase2InitializationWidget> {
  
  bool _isInitialized = false;
  String? _initializationError;
  
  @override
  void initState() {
    super.initState();
    _initializePhase2();
  }
  
  Future<void> _initializePhase2() async {
    try {
      await Phase2ProvidersConfig.initializeServices(ref);
      
      if (mounted) {
        setState(() {
          _isInitialized = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _initializationError = e.toString();
        });
      }
    }
  }
  
  @override
  void dispose() {
    // Cleanup services on dispose
    Phase2ProvidersConfig.cleanup(ref);
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (_initializationError != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Initialization Error'),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 64,
                color: Colors.red,
              ),
              const SizedBox(height: 16),
              const Text(
                'Failed to initialize Phase 2 services',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                _initializationError!,
                style: const TextStyle(color: Colors.red),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    _initializationError = null;
                  });
                  _initializePhase2();
                },
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    
    if (!_isInitialized) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              const Text(
                'Initializing Phase 2 Services...',
                style: TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 8),
              Text(
                'Setting up cloud sync and enhanced gallery',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ),
      );
    }
    
    return widget.child;
  }
}

/// Provider scope wrapper for easy Phase 2 integration
class Phase2ProviderScope extends StatelessWidget {
  final Widget child;
  
  const Phase2ProviderScope({
    super.key,
    required this.child,
  });
  
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Widget>(
      future: Phase2ProvidersConfig.createProviderScope(
        child: Phase2InitializationWidget(
          child: child,
        ),
      ),
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return MaterialApp(
            home: Scaffold(
              appBar: AppBar(
                title: const Text('Provider Configuration Error'),
              ),
              body: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      size: 64,
                      color: Colors.red,
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Failed to configure providers',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      snapshot.error.toString(),
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        
        if (snapshot.hasData) {
          return snapshot.data!;
        }
        
        return const MaterialApp(
          home: Scaffold(
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text(
                    'Configuring providers...',
                    style: TextStyle(fontSize: 16),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
