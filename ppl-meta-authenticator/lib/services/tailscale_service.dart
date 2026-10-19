import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as pkg_http;
import 'package:path_provider/path_provider.dart';
// The embedded Tailscale runtime is supported on Android / iOS / Linux / macOS.
// It is platform-scoped by the package, so the import is safe on web too; we
// guard against unsupported surfaces at runtime below.
import 'package:tailscale/tailscale.dart';

import 'app_logger.dart';
import 'platform_config_service.dart';

/// Own per-app embedded Tailscale node for the mobile camera.
///
/// The camera enrolls itself as its *own* `100.64.0.XX` node over the mesh
/// (LAN-direct when co-located), routing its in-app HTTP (discovery +
/// registration + heartbeat) through the tailnet when the embedded node is up.
///
/// This is **best-effort and optional**: if the embedded runtime/binary is not
/// available on this runtime, `initialize()` returns false and the caller falls
/// back to the Authority-resolved Tailscale IP path. Failures are non-fatal.
class TailscaleService {
  final PlatformConfigService _config;
  final AppLogger _logger;

  bool _initialized = false;
  bool _supported = false;
  bool _up = false;
  String? _ipv4;
  pkg_http.Client? _httpClient;

  TailscaleService({required PlatformConfigService config})
      : _config = config,
        _logger = AppLogger.instance;

  /// Whether the embedded Tailscale runtime is supported on this platform.
  bool get isSupported => !kIsWeb && _initialized && _supported;

  /// Whether the embedded node is currently up (connected to the tailnet).
  bool get isUp => _up;

  /// This camera's own mesh IP (`100.64.x.x`), once enrolled.
  String? get tailscaleIp => _ipv4;

  /// The live tailnet HTTP client — route requests through the camera's node.
  pkg_http.Client? get httpClient => _up ? _httpClient : null;

  /// Initialize the embedded Tailscale engine and bring up this camera's node.
  ///
  /// Safe to call every boot; no-ops when already initialized. If no VPN auth
  /// metadata is configured, returns false without error (the OS-level
  /// tailscale, when present, is left untouched).
  Future<bool> initialize() async {
    if (_initialized) {
      return _supported && _up;
    }
    _initialized = true;
    _supported = true;

    try {
      if (kIsWeb) {
        _supported = false;
        _logger.warning('Tailscale: embedded runtime not supported on web — skipping');
        return false;
      }

      // Only meaningful when the Authority has issued VPN credentials.
      final authKey = _config.vpnAuthKey;
      if (authKey == null || authKey.isEmpty) {
        _logger.warning(
          'Tailscale: no pre-auth key configured — not enrolling '
          '(falling back to OS tailscale / Authority IP)',
        );
        return false;
      }

      final headscaleServer = _config.vpnHeadscaleServer;
      final controlUrl = Uri.tryParse(headscaleServer ?? '');
      // A real control URL is required to bring up the node. If the persisted
      // headscale server is missing/malformed, clear the stale VPN credentials
      // so a later setup run starts clean, and do not call up() with a bad URL.
      if (headscaleServer == null ||
          headscaleServer.trim().isEmpty ||
          controlUrl == null ||
          !controlUrl.hasAuthority) {
        _logger.warning(
          'Tailscale: invalid/missing headscale server ($headscaleServer) — '
          'clearing stale VPN metadata and skipping node bring-up',
        );
        await _config.clearVpnMetadata();
        return false;
      }

      final stateDir = await _resolveStateDir();
      if (stateDir == null) {
        return false;
      }

      _logger.info('Tailscale: initializing embedded node (stateDir: $stateDir)');
      Tailscale.init(stateDir: stateDir);

      // Derive a stable per-app hostname from the installation UUID so the
      // tailnet shows one node per app, re-connectable across restarts.
      final hostname = _deriveHostname(_config.authorityInstallationUuid);

      final status = await Tailscale.instance.up(
        hostname: hostname,
        authKey: authKey,
        controlUrl: controlUrl,
        timeout: const Duration(seconds: 90),
      );

      // The tsnet engine can report `needsLogin` as its FIRST stable state even
      // with a valid pre-auth key while auth is still completing. Poll status()
      // (never re-call up(), which closes the node and registers a fresh one
      // every time) until the tunnel is actually up or we time out.
      TailscaleStatus current = status;
      var attempt = 0;
      const maxAttempts = 10;
      while (!current.isRunning && attempt < maxAttempts) {
        attempt++;
        await Future.delayed(const Duration(seconds: 3));
        try {
          current = await Tailscale.instance.status();
        } catch (e) {
          _logger.warning('Tailscale: status() poll $attempt failed: $e');
          break;
        }
        _logger.debug('Tailscale: state=${current.state.toString()} '
            'ip=${current.ipv4} (poll $attempt/$maxAttempts)');
      }

      final state = current.state.toString();
      _logger.info('Tailscale: final node state=$state ip=${current.ipv4}');

      if (current.isRunning) {
        _up = true;
        _ipv4 = current.ipv4;
        _httpClient = Tailscale.instance.http.client;
        // Persist our own mesh IP so discovery can register it even before the
        // Authority has ingested our new node.
        await _config.saveTailscaleIp(_ipv4);
        await _config.saveVpnEnrolled(true);
        _logger.info('Tailscale: own node up — mesh IP=$_ipv4');
      } else {
        _logger.warning('Tailscale: node still not running (state=$state) after '
            '$attempt attempts; tunnel not yet live');
        if (current.ipv4 != null) {
          _ipv4 = current.ipv4;
          await _config.saveTailscaleIp(_ipv4);
        }
      }
      return _up;
    } on TailscaleUsageException catch (e) {
      _supported = false;
      _logger.warning('Tailscale: embedded runtime unavailable — falling back to '
          'OS/Authority IP: $e');
      return false;
    } catch (e, stackTrace) {
      _supported = false;
      _logger.warning(
          'Tailscale: init/up failed (non-fatal, falling back to Authority IP): $e');
      _logger.debug('Tailscale: init stack trace: $stackTrace');
      return false;
    }
  }

  /// Perform a GET over the camera's own tailnet node. Returns null when the
  /// tailnet client is not available so the caller can fall back to its default
  /// transport.
  Future<pkg_http.Response?> get(String url, {Map<String, String>? headers}) async {
    final client = httpClient;
    if (client == null) return null;
    try {
      return await client.get(Uri.parse(url), headers: headers);
    } catch (e) {
      _logger.warning('Tailscale: GET via tailnet failed: $e');
      return null;
    }
  }

  /// Perform a POST over the camera's own tailnet node. Returns null when the
  /// tailnet client is not available so the caller can fall back to its default
  /// transport.
  Future<pkg_http.Response?> post(
    String url, {
    Map<String, String>? headers,
    Map<String, dynamic>? body,
  }) async {
    final client = httpClient;
    if (client == null) return null;
    try {
      return await client.post(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(body ?? const <String, dynamic>{}),
      );
    } catch (e) {
      _logger.warning('Tailscale: POST via tailnet failed: $e');
      return null;
    }
  }

  /// Bring the embedded node down (keeps persisted credentials for reconnect).
  Future<void> down() async {
    if (!_initialized) return;
    try {
      await Tailscale.instance.down();
    } catch (e) {
      _logger.warning('Tailscale: down failed: $e');
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
      _logger.warning('Tailscale: could not resolve state dir — skipping embedded enroll: $e');
      return null;
    }
  }

  String _deriveHostname(String installationUuid) {
    final base = installationUuid.isEmpty
        ? 'eyenet-mobile-camera'
        : installationUuid.replaceAll('@', '-').replaceAll('.', '-');
    final sanitized = base.replaceAll(RegExp(r'[^a-zA-Z0-9_-]'), '');
    return 'mobile-$sanitized'.toLowerCase();
  }
}