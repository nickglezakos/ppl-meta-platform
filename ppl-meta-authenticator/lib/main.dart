import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/auth/auth_service.dart';
import 'features/enroll/enroll_gate.dart';
import 'features/setup/setup_screen.dart';
import 'services/platform_config_service.dart';
import 'services/tailscale_service.dart';

/// Shared EyeNet / PPL Meta Camera brand blue.
const Color kEyeNetBrandBlue = Color(0xFF2196F3);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Paint UI immediately. Never block the first frame on network token checks
  // or embedded Tailscale — that produced a permanent white screen on devices
  // that cannot reach the last server / VPN mesh at cold start.
  runApp(AuthenticatorApp(auth: AuthService.instance));
}

Future<void> _prepareVpnMesh() async {
  try {
    final config = await PlatformConfigService.getInstance()
        .timeout(const Duration(seconds: 5));
    if (!config.vpnEnrolled) return;
    final tailscale = TailscaleService(config: config);
    await tailscale.initialize().timeout(const Duration(seconds: 12));
    await config.ensurePlatformReachable().timeout(const Duration(seconds: 8));
  } catch (_) {
    // Best-effort; setup screen can re-enroll.
  }
}

ThemeData _eyeNetTheme(Brightness brightness) {
  return ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: kEyeNetBrandBlue,
      brightness: brightness,
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
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
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
  );
}

class AuthenticatorApp extends StatefulWidget {
  const AuthenticatorApp({super.key, required this.auth});

  final AuthService auth;

  @override
  State<AuthenticatorApp> createState() => _AuthenticatorAppState();
}

class _AuthenticatorAppState extends State<AuthenticatorApp> {
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    unawaited(_bootstrap());
  }

  Future<void> _bootstrap() async {
    try {
      await widget.auth.loadPersisted().timeout(const Duration(seconds: 6));
    } catch (_) {
      // Offline / slow network: show setup; user can sign in again.
    }
    if (!mounted) return;
    setState(() => _ready = true);
    unawaited(_prepareVpnMesh());
  }

  @override
  Widget build(BuildContext context) {
    return Provider<AuthService>.value(
      value: widget.auth,
      child: MaterialApp(
        title: 'EyeNet Authenticator',
        debugShowCheckedModeBanner: false,
        theme: _eyeNetTheme(Brightness.light),
        darkTheme: _eyeNetTheme(Brightness.dark),
        home: !_ready
            ? const _BootstrapSplash()
            : (widget.auth.isAuthenticated
                ? const EnrollGate()
                : const SetupScreen()),
      ),
    );
  }
}

class _BootstrapSplash extends StatelessWidget {
  const _BootstrapSplash();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Starting EyeNet Authenticator…'),
          ],
        ),
      ),
    );
  }
}
