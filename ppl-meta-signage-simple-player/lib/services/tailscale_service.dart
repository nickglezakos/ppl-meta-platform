import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as pkg_http;
import 'package:logger/logger.dart';
import 'package:path_provider/path_provider.dart';
// The embedded Tailscale runtime is supported on Android / iOS / Linux / macOS.
// The import is platform-scoped by the package, so it is safe on web too; we
// guard against unsupported surfaces at runtime below.
import 'package:tailscale/tailscale.dart';

import '../config/app_config.dart';
import 'config_service.dart';

/// Own per-app embedded Tailscale node (Phase 4 — one node per app).
///
/// The signage player enrolls itself as its *own* `100.64.0.XX` node over the
/// mesh (LAN-direct when co-located), routing its in-app HTTP (playlist pull +
/// discovery registration) through the tailnet when the embedded node is up.
/// Enrollment happens *once*: after a successful `Tailscale.instance.up(...)` the
/// runtime persists the node key in its `stateDir`, and subsequent launches
/// reconnect automatically — no internet needed after the first enroll.
///
/// This is **best-effort and optional**: if the embedded runtime/binary is not
/// available on this runtime, `initialize()` returns false and the caller falls
/// back to the existing Authority-resolved Tailscale IP path. Failures are
/// non-fatal.
class TailscaleService {
  final Logger _logger;
  final ConfigService _configService;

  bool _initialized = false;
  bool _supported = false;
  bool _up = false;
  String? _ipv4;
  pkg_http.Client? _httpClient;

  TailscaleService({
    required ConfigService configService,
    Logger? logger,
  })  : _configService = configService,
        _logger = logger ?? Logger();

  /// Whether the embedded Tailscale runtime is supported on this platform.
  bool get isSupported => !kIsWeb && _initialized && _supported;

  /// Whether the embedded node is currently up (connected to the tailnet).
  bool get isUp => _up;

  /// This player's own mesh IP (`100.64.x.x`), once enrolled.
  String? get tailscaleIp => _ipv4;

  /// The live tailnet HTTP client — route requests through the player's own node.
  pkg_http.Client? get httpClient => _up ? _httpClient : null;

  /// Initialize the embedded Tailscale engine and bring up this player's own node.
  ///
  /// Safe to call every boot; no-ops when already initialized. If no VPN auth
  /// metadata is configured, returns false without error (the OS-level tailscale,
  /// when present, is left untouched).
  Future<bool> initialize() async {
    if (_initialized) {
      return _supported && _up;
    }
    _initialized = true;
    _supported = true;

    try {
      if (kIsWeb) {
        _supported = false;
        _logger.w('Tailscale: embedded runtime not supported on web — skipping');
        return false;
      }

      // Only meaningful when the Authority has issued VPN credentials.
      final authKey = _configService.vpnAuthKey;
      if (authKey == null || authKey.isEmpty) {
        _logger.d('Tailscale: no pre-auth key configured — not enrolling '
            '(falling back to OS tailscale / Authority IP)');
        return false;
      }

      final headscaleServer = _configService.vpnHeadscaleServer;
      final controlUrl = Uri.tryParse(headscaleServer ?? '');
      // A real control URL is required to bring up the node. If the persisted
      // headscale server is missing/malformed (e.g. from a partial prior enroll),
      // clear the stale VPN credentials so a later setup run starts clean, and do
      // not call up() with a bad URL (which throws an invalid-base-url error).
      if (headscaleServer == null ||
          headscaleServer.trim().isEmpty ||
          controlUrl == null ||
          !controlUrl.hasAuthority) {
        _logger.w(
            'Tailscale: invalid/missing headscale server ($headscaleServer) — '
            'clearing stale VPN metadata and skipping node bring-up');
        await _configService.clearVpnMetadata();
        return false;
      }

      final stateDir = await _resolveStateDir();
      if (stateDir == null) {
        return false;
      }

      _logger.i('Tailscale: initializing embedded node (stateDir: $stateDir)');
      Tailscale.init(stateDir: stateDir);

      // Derive a stable per-app hostname from the installation UUID so the tailnet
      // shows one node per app, re-connectable across restarts.
      final hostname = _deriveHostname(_configService.authorityInstallationUuid);

      final status = await Tailscale.instance.up(
        hostname: hostname,
        authKey: authKey,
        controlUrl: controlUrl,
        timeout: AppConfig.tailscaleUpTimeout,
      );

      final state = status.state.toString();
      _logger.i('Tailscale: node state=$state ip=${status.ipv4}');

      if (status.isRunning) {
        _up = true;
        _ipv4 = status.ipv4;
        _httpClient = Tailscale.instance.http.client;
        // Persist our own mesh IP so discovery can register it even before the
        // Authority has ingested our new node.
        await _configService.saveTailscaleIp(_ipv4);
        await _configService.saveVpnEnrolled(true);
        _logger.i('Tailscale: own node up — mesh IP=$_ipv4');
      } else {
        // needsLogin / needsMachineAuth etc. — not yet ready for traffic, but the
        // configured state is persisted so the login flow can finish later.
        _logger.w('Tailscale: node not running (state=$state); tunnel not yet live');
        if (status.ipv4 != null) {
          _ipv4 = status.ipv4;
          await _configService.saveTailscaleIp(_ipv4);
        }
      }
      return _up;
    } on TailscaleUsageException catch (e) {
      _supported = false;
      _logger.w('Tailscale: embedded runtime unavailable — falling back to OS/Authority IP: $e');
      return false;
    } catch (e, stackTrace) {
      _supported = false;
      _logger.w(
          'Tailscale: init/up failed (non-fatal, falling back to Authority IP): $e');
      _logger.d('Tailscale: init stack trace: $stackTrace');
      return false;
    }
  }

  /// Perform a GET over the player's own tailnet node. Returns null when the
  /// tailnet client is not available so the caller can fall back to its default
  /// dio transport.
  Future<pkg_http.Response?> get(String url, {Map<String, String>? headers}) async {
    final client = httpClient;
    if (client == null) {
      return null;
    }
    try {
      return await client.get(Uri.parse(url), headers: headers);
    } catch (e) {
      _logger.w('Tailscale: GET via tailnet failed: $e');
      return null;
    }
  }

  /// Perform a POST over the player's own tailnet node. Returns null when the
  /// tailnet client is not available so the caller can fall back to its default
  /// dio transport. The `body` map is JSON-encoded (package:http v1 semantics).
  Future<pkg_http.Response?> post(
    String url, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
  }) async {
    final client = httpClient;
    if (client == null) {
      return null;
    }
    try {
      return await client.post(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(body ?? const <String, dynamic>{}),
      );
    } catch (e) {
      _logger.w('Tailscale: POST via tailnet failed: $e');
      return null;
    }
  }

  /// Bring the embedded node down (keeps persisted credentials for reconnect).
  Future<void> down() async {
    if (!_initialized) {
      return;
    }
    try {
      await Tailscale.instance.down();
    } catch (e) {
      _logger.w('Tailscale: down failed: $e');
    }
    _up = false;
    _httpClient = null;
  }

  /// Resolve a persistent application-support subdirectory for the node's state.
  Future<String?> _resolveStateDir() async {
    try {
      final dir = await getApplicationSupportDirectory();
      final nodeDir = Directory('${dir.path}/tailscale');
      await nodeDir.create(recursive: true);
      return nodeDir.path;
    } catch (e) {
      _logger.w('Tailscale: could not resolve state dir — skipping embedded enroll: $e');
      return null;
    }
  }

  String _deriveHostname(String installationUuid) {
    final base = installationUuid.isEmpty
        ? 'eyenet-signage'
        : installationUuid.replaceAll('@', '-').replaceAll('.', '-');
    final sanitized = base.replaceAll(RegExp(r'[^a-zA-Z0-9_-]'), '');
    return 'signage-$sanitized-${AppConfig.httpServerPort}'.toLowerCase();
  }
}
