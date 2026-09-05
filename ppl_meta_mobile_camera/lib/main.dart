import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/core.dart';
import 'features/authentication/authentication.dart';
import 'features/camera/camera.dart';
import 'services/app_logger.dart';
import 'services/discovery_config_service.dart';
import 'services/platform_config_service.dart';
import 'services/tailscale_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize logging system
  await AppLogger.instance.initialize();
  AppLogger.instance.info('🚀 Eyenet Vision starting...');

  // Initialize discovery service - user configuration required
  await DiscoveryConfigService.instance.initialize();
  AppLogger.instance.info('🔧 Discovery service ready - user configuration required');

  // VPN mesh boot (WP5): once enrolled, bring up the camera's own embedded
  // Tailscale node and resolve the platform endpoints (LAN first, VPN on
  // demand). Best-effort — never blocks onboarding.
  await _prepareVpnMesh();

  runApp(const PPLMetaCameraApp());
}

/// Best-effort VPN mesh startup: bring up the embedded node and ensure the
/// platform is reachable over LAN (or fall back to the mesh). No-ops when the
/// camera is not yet enrolled, and never throws on failure.
Future<void> _prepareVpnMesh() async {
  try {
    final config = await PlatformConfigService.getInstance();
    if (!config.vpnEnrolled && config.vpnAuthKey == null) {
      AppLogger.instance.info('No VPN enrollment yet — skipping mesh bring-up');
      return;
    }

    // Bring up the camera's own mesh node (routing discovery/register/heartbeat
    // over the tailnet when remote).
    final tailscale = TailscaleService(config: config);
    await tailscale.initialize();

    // Resolve the platform (LAN-first) and self-heal stale LAN IPs.
    await config.ensurePlatformReachable();
    AppLogger.instance.info(
      'Platform host resolved: ${config.platformHost} '
      '(preferVpn=${config.preferVpnHost})',
    );
  } catch (e, stack) {
    AppLogger.instance.warning('VPN mesh prepare failed (non-fatal): $e');
    AppLogger.instance.debug('VPN mesh prepare stack: $stack');
  }
}

class PPLMetaCameraApp extends StatelessWidget {
  const PPLMetaCameraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Authentication Service (singleton)
        Provider<AuthenticationService>.value(
          value: AuthenticationService.instance,
        ),
        ChangeNotifierProvider(create: (_) => AuthenticationProvider()),
        ChangeNotifierProvider(
          create: (_) {
            final cameraProvider = CameraProvider();
            // Register camera provider with interface to break circular dependencies
            CameraInterface.setInstance(cameraProvider);
            return cameraProvider;
          },
        ),
        ChangeNotifierProvider(create: (_) => GalleryProvider()),
        ChangeNotifierProvider(create: (_) => PlatformStreamingProvider()),
      ],
      child: MaterialApp(
        title: 'PPL Meta Camera',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF2196F3), // PPL Meta Blue
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 0,
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            filled: true,
          ),
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF2196F3), // PPL Meta Blue
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 0,
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            filled: true,
          ),
        ),
        themeMode: ThemeMode.system,
        home: const MainNavigator(),
      ),
    );
  }
}

/// Main navigation widget that handles authentication and app flow
class MainNavigator extends StatefulWidget {
  const MainNavigator({Key? key}) : super(key: key);

  @override
  State<MainNavigator> createState() => _MainNavigatorState();
}

class _MainNavigatorState extends State<MainNavigator> {
  @override
  void initState() {
    super.initState();
    // Skip auto-initialization - using Simple Setup approach instead
    // WidgetsBinding.instance.addPostFrameCallback((_) {
    //   context.read<AuthenticationProvider>().initializeAuth();
    // });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthenticationProvider>(
      builder: (context, authProvider, child) {
        if (authProvider.isAuthenticated) {
          // Check if camera registration is required
          if (authProvider.requiresCameraRegistration) {
            return const CameraRegistrationScreen();
          } else {
            return const CameraScreen();
          }
        } else {
          return const SimpleSetupScreen();
        }
      },
    );
  }
}
