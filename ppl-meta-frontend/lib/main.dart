import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/config/app_config.dart';
import 'core/theme/app_theme.dart';
import 'presentation/navigation/app_router.dart';
import 'services/dynamic_service_provider.dart';
import 'widgets/global_screenshot_overlay.dart';
import 'widgets/alert_overlay.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize SharedPreferences for web platform
  if (kIsWeb) {
    SharedPreferences.setMockInitialValues({});
  }
  
  // Initialize app configuration
  await AppConfig.initialize();
  
  runApp(
    const ProviderScope(
      child: PPLMetaApp(),
    ),
  );
}

class PPLMetaApp extends ConsumerWidget {
  const PPLMetaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    
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
          child: GlobalScreenshotOverlay(
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
    );
  }
}
