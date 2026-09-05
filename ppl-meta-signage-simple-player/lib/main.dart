import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:logger/logger.dart';
import 'package:provider/provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'config/app_config.dart';
import 'services/discovery_service.dart';
import 'services/player_engine.dart';
import 'services/http_server.dart';
import 'services/history_tracking_service.dart';
import 'services/sync_service.dart';
import 'services/config_service.dart';
import 'services/tailscale_service.dart';
import 'database/playlist_database.dart';
import 'api/signage_api_client.dart';
import 'utils/device_info_helper.dart';
import 'screens/signage_player_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/simple_setup_screen.dart';

final logger = Logger(
  printer: PrettyPrinter(
    methodCount: 0,
    errorMethodCount: 5,
    lineLength: 80,
    colors: true,
    printEmojis: true,
  ),
);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Enable fullscreen mode for signage display
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive);
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.landscapeRight,
    DeviceOrientation.landscapeLeft,
  ]);

  if (Platform.isLinux) {
    // Linux needs explicit FFI init for sqflite.
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }
  
  logger.i('Starting PPL Meta Signage Simple Player v\${AppConfig.version}');
  logger.i('Platform: \${getPlatformName()}');
  logger.i('HTTP Server Port: \${AppConfig.httpServerPort}');
  
  runApp(const SignageSimplePlayerApp());
}

String getPlatformName() {
  if (const bool.fromEnvironment('dart.vm.product')) {
    return 'Production';
  }
  return 'Development';
}

class SignageSimplePlayerApp extends StatelessWidget {
  const SignageSimplePlayerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta Signage Simple Player',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const StartupScreen(),
    );
  }
}

class StartupScreen extends StatefulWidget {
  const StartupScreen({super.key});

  @override
  State<StartupScreen> createState() => _StartupScreenState();
}

class _StartupScreenState extends State<StartupScreen> {
  bool _isLoading = true;
  bool _needsSetup = false;

  @override
  void initState() {
    super.initState();
    _checkConfiguration();
  }

  Future<void> _checkConfiguration() async {
    try {
      final configService = await ConfigService.getInstance();
      final isConfigured = configService.skipOnboarding;
      
      setState(() {
        _needsSetup = !isConfigured;
        _isLoading = false;
      });

      if (isConfigured) {
        // Configuration exists, proceed to initialization
        _navigateToInitialization();
      }
    } catch (e) {
      logger.e('Error checking configuration: $e');
      setState(() {
        _needsSetup = true;
        _isLoading = false;
      });
    }
  }

  void _navigateToInitialization() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (context) => const InitializationScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_needsSetup) {
      return SimpleSetupScreen(
        onSetupComplete: _navigateToInitialization,
      );
    }

    return const Scaffold(
      body: Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}

class InitializationScreen extends StatefulWidget {
  const InitializationScreen({super.key});

  @override
  State<InitializationScreen> createState() => _InitializationScreenState();
}

class _InitializationScreenState extends State<InitializationScreen> {
  String _statusMessage = 'Initializing services...';
  bool _initialized = false;
  String? _errorMessage;
  
  // Service instances
  PlaylistDatabase? _database;
  SignageApiClient? _apiClient;
  SignagePlayerEngine? _playerEngine;
  SignageHttpServer? _httpServer;
  HistoryTrackingService? _historyTracker;
  SyncService? _syncService;
  SignageDiscoveryService? _discoveryService;
  ConfigService? _configService;
  TailscaleService? _tailscaleService;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  Future<void> _initializeServices() async {
    try {
      setState(() {
        _statusMessage = 'Loading configuration...';
      });
      
      _configService = await ConfigService.getInstance();
      logger.i('Configuration loaded');

      // Issue #9 / #7 / #12: refresh platform endpoints from Authority, probe
      // LAN reachability, and pull local IP over mesh (Variant A) if needed.
      setState(() {
        _statusMessage = 'Resolving platform endpoints...';
      });
      try {
        await _configService!.ensurePlatformReachable();
        logger.i(
          'Platform host resolved: ${_configService!.platformHost} '
          '(preferVpn=${_configService!.preferVpnHost})',
        );
      } catch (e) {
        logger.w('Platform reachability check failed (continuing): $e');
      }

      // Phase 4: bring up this player's own per-app Tailscale node (best-effort).
      // When VPN/auth metadata is configured the embedded runtime enrolls once and
      // persists its node key; otherwise this returns false without error. The API
      // and discovery clients below are then routed through the mesh node if it's up.
      _tailscaleService = TailscaleService(configService: _configService!, logger: logger);
      await _tailscaleService!.initialize();
      if (_tailscaleService!.isUp) {
        logger.i('Player own-node up — mesh IP ${_tailscaleService!.tailscaleIp}');
      }

      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Initializing database...';
      });
      
      _database = PlaylistDatabase();
      await _database!.database;
      logger.i('Database initialized successfully');
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Gathering device information...';
      });
      
      final deviceId = await DeviceInfoHelper.getDeviceId();
      logger.i('Device ID: $deviceId');
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Setting up API client...';
      });
      
      _apiClient = SignageApiClient(
        baseUrl: _configService!.gatewayUrl,
        deviceId: deviceId,
        logger: logger,
        tailscaleService: _tailscaleService,
        configService: _configService,
      );
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Initializing player engine...';
      });
      
      _playerEngine = SignagePlayerEngine(
        database: _database!,
        logger: logger,
        preloadCount: AppConfig.preloadCount,
        configService: _configService,
      );
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Starting HTTP server...';
      });
      
      _httpServer = SignageHttpServer(
        database: _database!,
        playerEngine: _playerEngine!,
        configService: _configService!,
        logger: logger,
        deviceId: deviceId,
        port: AppConfig.httpServerPort,
      );
      await _httpServer!.start();
      logger.i('HTTP server started on port ${AppConfig.httpServerPort}');
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Starting playback tracking...';
      });
      
      _historyTracker = HistoryTrackingService(
        database: _database!,
        playerEngine: _playerEngine!,
        logger: logger,
        deviceId: deviceId,
      );
      _historyTracker!.startTracking();
      logger.i('History tracking service started');
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Initializing sync service...';
      });
      
      _syncService = SyncService(
        apiClient: _apiClient!,
        database: _database!,
        logger: logger,
        configService: _configService,
      );
      _syncService!.startAutoPoll();
      
      await Future.delayed(const Duration(milliseconds: 300));
      
      setState(() {
        _statusMessage = 'Registering with Discovery Service...';
      });
      
      _discoveryService = SignageDiscoveryService(
        logger: logger,
        configService: _configService!,
        tailscaleService: _tailscaleService,
      );
      
      final registered = await _discoveryService!.initialize();
      
      if (registered) {
        setState(() {
          _statusMessage = 'Registration successful!';
        });
        await Future.delayed(const Duration(seconds: 1));
        
        setState(() {
          _initialized = true;
          _statusMessage = 'Ready';
        });
        
        // Navigate to player screen after successful initialization
        await Future.delayed(const Duration(milliseconds: 500));
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => _buildPlayerScreenWithProviders(),
            ),
          );
        }
      } else {
        setState(() {
          _statusMessage = 'Running in offline mode';
          _errorMessage = _discoveryService!.lastError ?? 'Could not connect to Discovery Service';
        });
        await Future.delayed(const Duration(seconds: 2));
        
        setState(() {
          _initialized = true;
        });
        
        // Navigate to player screen even in offline mode
        await Future.delayed(const Duration(milliseconds: 500));
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              builder: (context) => _buildPlayerScreenWithProviders(),
            ),
          );
        }
      }
    } catch (e, stackTrace) {
      logger.e('Initialization failed', error: e, stackTrace: stackTrace);
      setState(() {
        _errorMessage = e.toString();
        _statusMessage = 'Initialization failed';
      });
    }
  }

  Widget _buildPlayerScreenWithProviders() {
    return MultiProvider(
      providers: [
        Provider<PlaylistDatabase>.value(value: _database!),
        Provider<SignageApiClient>.value(value: _apiClient!),
        ChangeNotifierProvider<SignagePlayerEngine>.value(value: _playerEngine!),
        Provider<SignageHttpServer>.value(value: _httpServer!),
        Provider<HistoryTrackingService>.value(value: _historyTracker!),
        ChangeNotifierProvider<SyncService>.value(value: _syncService!),
        Provider<SignageDiscoveryService>.value(value: _discoveryService!),
        Provider<ConfigService>.value(value: _configService!),
      ],
      child: const SignagePlayerScreen(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (!_initialized) ...[
              const SizedBox(
                width: 60,
                height: 60,
                child: CircularProgressIndicator(
                  strokeWidth: 4,
                  color: Colors.blue,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                _statusMessage,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                ),
              ),
            ] else ...[
              const Icon(
                Icons.check_circle,
                color: Colors.green,
                size: 60,
              ),
              const SizedBox(height: 16),
              const Text(
                'Ready!',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
            if (_errorMessage != null) ...[
              const SizedBox(height: 24),
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 24),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red.shade900,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(color: Colors.white),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
