import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/config/app_config.dart';
import 'core/config/platform_config_service.dart';
import 'core/providers/bootstrap_provider.dart';
import 'core/theme/app_theme.dart';
import 'presentation/navigation/app_router.dart';
import 'presentation/screens/setup/platform_connection_setup_screen.dart';
import 'services/dynamic_service_provider.dart';
import 'services/platform_connectivity_service.dart';
import 'widgets/global_screenshot_overlay.dart';
import 'widgets/alert_overlay.dart';
import 'widgets/authority_lifecycle_banner.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize SharedPreferences for web platform
  if (kIsWeb) {
    SharedPreferences.setMockInitialValues({});
  }
  
  runApp(
    const ProviderScope(
      child: PPLMetaBootstrapApp(),
    ),
  );
}

class PPLMetaBootstrapApp extends StatefulWidget {
  const PPLMetaBootstrapApp({super.key});

  @override
  State<PPLMetaBootstrapApp> createState() => _PPLMetaBootstrapAppState();
}

class _PPLMetaBootstrapAppState extends State<PPLMetaBootstrapApp> {
  bool _isLoading = true;
  bool _needsSetup = false;

  bool get _requiresAndroidSetup => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    if (!_requiresAndroidSetup) {
      await AppConfig.initialize();
      if (mounted) {
        setState(() {
          _isLoading = false;
          _needsSetup = false;
        });
      }
      return;
    }

    final connectivityService = await PlatformConnectivityService.getInstance();

    // NEW: Check for VPN-mesh enrollment first (preferred path)
    try {
      final platformConfig = await PlatformConfigService.getInstance();
      if (platformConfig.vpnEnrolled ||
          (platformConfig.vpnPlatformTailscaleIp != null &&
              platformConfig.vpnPlatformTailscaleIp!.isNotEmpty)) {
        await platformConfig.ensurePlatformReachable();
        await AppConfig.initialize(); // Will pick up VPN-resolved host
        if (mounted) {
          setState(() {
            _isLoading = false;
            _needsSetup = false;
          });
        }
        return;
      }
    } catch (_) {
      // Continue with legacy path
    }

    if (connectivityService.isConfigured) {
      final isStoredConnectionValid = await connectivityService.testDiscoveryConnection(
        backendInput: connectivityService.backendHost,
        discoveryPort: connectivityService.discoveryPort,
      );

      if (!isStoredConnectionValid) {
        await AppConfig.initialize();
        if (mounted) {
          setState(() {
            _isLoading = false;
            _needsSetup = true;
          });
        }
        return;
      }

      await connectivityService.applyRuntimeConfiguration();
      await AppConfig.initialize(backendHostOverride: connectivityService.backendHost);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _needsSetup = false;
        });
      }
      return;
    }

    await AppConfig.initialize();
    if (mounted) {
      setState(() {
        _isLoading = false;
        _needsSetup = true;
      });
    }
  }

  Future<void> _handleSetupComplete() async {
    final connectivityService = await PlatformConnectivityService.getInstance();
    await connectivityService.applyRuntimeConfiguration();
    await AppConfig.initialize(backendHostOverride: connectivityService.backendHost);

    if (mounted) {
      setState(() {
        _needsSetup = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const MaterialApp(
        home: Scaffold(
          body: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    if (_needsSetup) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        home: PlatformConnectionSetupScreen(
          onSetupComplete: _handleSetupComplete,
        ),
      );
    }

    return const PPLMetaApp();
  }
}

class PPLMetaApp extends ConsumerWidget {
  const PPLMetaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    ref.watch(bootstrapStatusProvider);
    
    // Initialize service discovery if enabled
    ref.listen(serviceDiscoveryInitProvider, (previous, next) {
      next.when(
        data: (initialized) {
          if (initialized) {
            print('✅ Service Discovery initialized successfully');
          }
        },
        loading: () => print('🔄 Initializing Service Discovery...'),
        error: (error, stack) => print('❌ Service Discovery initialization failed: $error'),
      );
    });
    
    return MaterialApp.router(
      title: 'Eyenet Vision v2.23.1 with Dynamic Service Discovery',
      theme: AppTheme.darkTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.dark,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
      builder: (context, child) {
        // Wrap entire app with alert overlay, then screenshot overlay
        return AlertOverlay(
          child: AuthorityLifecycleBanner(
            child: GlobalScreenshotOverlay(
              child: child ?? const SizedBox.shrink(),
            ),
          ),
        );
      },
    );
  }
}
