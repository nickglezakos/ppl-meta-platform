import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/core.dart';
import 'features/authentication/authentication.dart';
import 'features/camera/camera.dart';
import 'services/app_logger.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize logging system
  await AppLogger.instance.initialize();
  AppLogger.instance.info('🚀 PPL Meta Mobile Camera starting...');
  
  runApp(const PPLMetaCameraApp());
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
    // Initialize authentication on app start
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AuthenticationProvider>().initializeAuth();
    });
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
          return const AuthenticationScreen();
        }
      },
    );
  }
}
