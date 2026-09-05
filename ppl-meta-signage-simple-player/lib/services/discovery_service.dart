import 'dart:async';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../models/device_info_model.dart';
import '../config/app_config.dart';
import '../utils/device_info_helper.dart';
import 'authority_api_client.dart';
import 'config_service.dart';
import 'tailscale_service.dart';
import 'tailscale_http_adapter.dart';

/// Service for discovering and registering with ppl-meta-discovery.
/// Phase 5: VPN-first discovery — when a Tailscale IP is configured, the
/// player queries the discovery service directly over VPN for zero-config setup.
class SignageDiscoveryService {
  final Dio _dio;
  final Logger _logger;
  final ConfigService _configService;
  
  Timer? _heartbeatTimer;
  Timer? _registrationRetryTimer;
  bool _isRegistered = false;
  String? _serviceId;
  DeviceInfoModel? _deviceInfo;
  String? _lastError;

  /// Heartbeat interval suggested by the discovery service on registration (Issue #7).
  /// Falls back to [AppConfig.heartbeatInterval] when the server omits it.
  Duration? _serverHeartbeatInterval;

  /// Cached VPN node IP for direct discovery (Phase 5)
  String? _vpnNodeIp;

  /// Cached player's own Tailscale IP resolved from the Authority.
  String? _ownTailscaleIp;

  /// Most recent VPN-direct topology fetched from ppl-meta-discovery (Phase 5).
  Map<String, dynamic>? _lastTopology;
/// Edge-device registration (Issue #6): the player is registered both as a
  /// service (control/health plane) and as an edge device (device registry).
  bool _isDeviceRegistered = false;
  /// Device id assigned by the edge-device registry (/api/v1/devices/register).
  String? _deviceRegistrationId;

  /// Optional embedded Tailscale node (Phase 4). When provided and up, this
  /// player's own mesh node routes discovery/registration over the tailnet.
  final TailscaleService? _tailscaleService;

  SignageDiscoveryService({
    Dio? dio,
    Logger? logger,
    required ConfigService configService,
    TailscaleService? tailscaleService,
  })  : _dio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: AppConfig.discoveryConnectTimeout,
                sendTimeout: AppConfig.discoverySendTimeout,
                receiveTimeout: AppConfig.discoveryReceiveTimeout,
              ),
            ),
        _logger = logger ?? Logger(),
        _configService = configService,
        _tailscaleService = tailscaleService {
    _setupAuthInterceptor();
    _setupTailscaleAdapter();
  }

  /// Route discovery / registration requests through the player's own mesh node
  /// (Phase 4) when the embedded Tailscale node is up. Best-effort — the default
  /// io adapter remains otherwise.
  void _setupTailscaleAdapter() {
    final tailscale = _tailscaleService;
    if (tailscale == null || !tailscale.isUp) {
      return;
    }
    final client = tailscale.httpClient;
    if (client == null) {
      return;
    }
    _dio.httpClientAdapter = TailscaleHttpClientAdapter(client);
    _logger.i(
        'Discovery service routing through embedded Tailscale node (${tailscale.tailscaleIp})');
  }

  /// Attach installation-token auth headers (Issue #8) to every request when the
  /// Authority has issued a token. Safe no-op when no token is configured.
  void _setupAuthInterceptor() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = _configService.installationApiToken;
          var uuid = _configService.authorityInstallationUuid;
          // If we hold a token but not the real installation UUID (older authority
          // that omitted it), try to resolve it from the matrix-group nodes so
          // discovery's HMAC check passes. Cheapest after the first success.
          if (token.isNotEmpty && uuid.isEmpty) {
            await _resolveOwnInstallationUuidIfMissing();
            uuid = _configService.authorityInstallationUuid;
          }
          if (token.isNotEmpty && uuid.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
            options.headers['X-Installation-Uuid'] = uuid;
          }
          handler.next(options);
        },
      ),
    );
  }

  /// Set the VPN node IP for direct discovery (Phase 5)
  void setVpnNodeIp(String? ip) {
    _vpnNodeIp = ip;
    if (ip != null && ip.isNotEmpty) {
      _logger.i('VPN node IP set for direct discovery: $ip');
    }
  }

  /// Check if VPN is connected for direct discovery
  bool get isVpnConnected => _vpnNodeIp != null && _vpnNodeIp!.isNotEmpty;

  /// Attempt VPN-direct discovery of all backend services.
  /// Phase 5: Calls GET /api/v1/discovery/topology?vpn=true on the primary node.
  Future<Map<String, dynamic>?> discoverTopology() async {
    if (!isVpnConnected) return null;

    try {
      final vpnDiscoveryUrl = 'http://$_vpnNodeIp:8006';
      _logger.i('Attempting VPN-direct topology discovery at $vpnDiscoveryUrl');

      final response = await _dio.get(
        '$vpnDiscoveryUrl/api/v1/discovery/topology?vpn=true',
        options: Options(
          headers: {'Accept': 'application/json'},
          sendTimeout: AppConfig.topologySendTimeout,
          receiveTimeout: AppConfig.topologyReceiveTimeout,
        ),
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        _lastTopology = data;
        _logger.i('VPN-direct topology discovered: ${data['backend_services']?.length ?? 0} services');
        return data;
      }
    } catch (e) {
      _logger.w('VPN-direct topology discovery failed: $e');
    }
    return null;
  }

  /// Initialize and register the service
  Future<bool> initialize() async {
    try {
      _lastError = null;
      _logger.i('Initializing Discovery Service...');
      
      // Get device information
      _deviceInfo = await DeviceInfoHelper.getDeviceInfo();
      _logger.d('Device ID: ${_deviceInfo!.deviceId}');
      _logger.d('Device Name: ${_deviceInfo!.deviceName}');
      
      // VPN-direct discovery (Phase 5): prefer the assigned platform mesh IP
      // (issue #10) over the legacy primary-node IP, which may still point at
      // headscale in older deployments.
      final vpnNodeIp = _configService.vpnDiscoveryNodeIp;
      if (vpnNodeIp != null && vpnNodeIp.isNotEmpty) {
        setVpnNodeIp(vpnNodeIp);
        await discoverTopology();
      }


      // Edge-device registration (Issue #6, dual registration): also register the
      // player as an edge device so the device registry can track it by type,
      // capabilities and VPN reachability. Best-effort — failure does not block
      // service registration.
      // Ensure the install-token auth header carries our REAL installation uuid
      // (the token is HMAC(secret, real_uuid)). When the enrollment response
      // omitted it, resolve it from the Authority's matrix-group nodes now so
      // discovery accepts registration and heartbeats.
      await _resolveOwnInstallationUuidIfMissing();
      await _registerAsEdgeDevice();

      // Register with discovery service
      // Register with discovery service
      final registered = await register();
      
      if (registered) {
        _startHeartbeat();
        _logger.i('Discovery Service initialized successfully');
      } else {
        _logger.w('Failed to register with discovery service');
        _startRegistrationRetry();
      }
      
      return registered;
    } catch (e, stackTrace) {
      _lastError = 'Discovery initialization failed: $e';
      _logger.e('Failed to initialize discovery service', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Resolve this player's own Tailscale (VPN) IP.
  ///
  /// Prefers the embedded per-app Tailscale node (Phase 4) — its own
  /// `100.64.x.x` address is authoritative because the node *is* the player.
  /// Falls back to asking the Authority for the matrix group's nodes and matching
  /// our own installation_uuid (populated from the tag:install-* ACL tag). On
  /// Android the VPN tun is otherwise invisible to NetworkInterface.list().
/// Ensure the player has the REAL installation UUID it's bound to, resolving it
  /// from the Authority's matrix-group nodes when the enrollment response omitted
  /// it (older authority). Discovery validates the install token as
  /// HMAC(secret, X-Installation-Uuid), so the header must carry the real UUID the
  /// token was minted for — otherwise registration is rejected with 401. Idempotent.
  Future<String?> _resolveOwnInstallationUuidIfMissing() async {
    final existing = _configService.authorityInstallationUuid;
    if (existing.isNotEmpty) {
      return existing;
    }

    final matrixGroupId = _configService.vpnMatrixGroupId;
    if (matrixGroupId == null || matrixGroupId.isEmpty) {
      return null;
    }

    try {
      final authority = AuthorityApiClient(
        baseUrl: _configService.authorityServiceUrl,
        logger: _logger,
      );
      final nodes = await authority.listMatrixGroupNodes(matrixGroupId);

      AuthorityVpnNode? selfNode;
      // 1. Best: match by our own mesh IP (persisted when our node came up).
      final ownMeshIp = _configService.tailscaleIp ?? _tailscaleService?.tailscaleIp;
      if (ownMeshIp != null && ownMeshIp.isNotEmpty) {
        for (final node in nodes) {
          if (node.tailscaleIp == ownMeshIp) {
            selfNode = node;
            break;
          }
        }
      }
      // 2. Fallback: a token-enrolled mesh has exactly one leaf (non-node)
      // installation entry — that's us.
      if (selfNode == null) {
        for (final node in nodes) {
          if (!node.isNode && node.installationUuid.isNotEmpty) {
            selfNode = node;
            break;
          }
        }
      }

      if (selfNode == null || selfNode.installationUuid.isEmpty) {
        _logger.w(
            'Could not self-identify in matrix group $matrixGroupId '
            '(nodes=${nodes.length})');
        return null;
      }

      await _configService.saveAuthorityCredentials(
        applicationKey: _configService.authorityApplicationKey,
        installationUuid: selfNode.installationUuid,
      );
      _logger.i('Resolved own installation UUID: ${selfNode.installationUuid}');
      return selfNode.installationUuid;
    } catch (e) {
      _logger.w('Failed to resolve own installation UUID: $e');
      return null;
    }
  }

  /// Resolve this player's own Tailscale (VPN) IP.
  Future<String?> _resolveOwnTailscaleIp() async {
    if (_ownTailscaleIp != null && _ownTailscaleIp!.isNotEmpty) {
      return _ownTailscaleIp;
    }

    // 1. The embedded per-app node knows its own IP directly.
    final tailscale = _tailscaleService;
    final embeddedIp = tailscale?.tailscaleIp;
    if (embeddedIp != null && embeddedIp.isNotEmpty) {
      _ownTailscaleIp = embeddedIp;
      _logger.i('Tailscale IP from embedded node: $embeddedIp');
      return _ownTailscaleIp;
    }

    final matrixGroupId = _configService.vpnMatrixGroupId;
    final installationUuid = _configService.authorityInstallationUuid;
    if (matrixGroupId == null ||
        matrixGroupId.isEmpty ||
        installationUuid.isEmpty) {
      return null;
    }

    try {
      final authority = AuthorityApiClient(
        baseUrl: _configService.authorityServiceUrl,
      );
      final nodes = await authority.listMatrixGroupNodes(matrixGroupId);
      for (final node in nodes) {
        if (node.installationUuid == installationUuid &&
            node.tailscaleIp != null &&
            node.tailscaleIp!.isNotEmpty) {
          _ownTailscaleIp = node.tailscaleIp;
          _logger.i(
              'Resolved own Tailscale IP from Authority: ${node.tailscaleIp}');
          return _ownTailscaleIp;
        }
      }
      _logger.w('Own node not found in Authority matrix group $matrixGroupId '
          '(installation_uuid=$installationUuid)');
    } catch (e) {
      _logger.w('Failed to resolve own Tailscale IP from Authority: $e');
    }
    return null;
  }

  /// Register service with ppl-meta-discovery
  Future<bool> register() async {
    if (_deviceInfo == null) {
      _logger.e('Device info not available for registration');
      return false;
    }

    try {
      _lastError = null;
      _logger.i('Registering with discovery service...');
      
      final localIp = await DeviceInfoHelper.getLocalIpAddress();
      // Include the Tailscale IP in registration metadata so ppl-meta-discovery
      // marks the player as VPN-reachable and returns it in ?vpn=true topology.
      // Prefer the Authority (works on Android where the VPN tun is invisible to
      // NetworkInterface.list()); fall back to a locally-detected 100.x address
      // for desktop/Linux players.
      final authorityTailscaleIp = await _resolveOwnTailscaleIp();
      final metadata = _deviceInfo!.toJson();
      final tailscaleIp = authorityTailscaleIp ??
          (localIp.startsWith('100.') ? localIp : null);
      if (tailscaleIp != null && tailscaleIp.isNotEmpty) {
        metadata['tailscale_ip'] = tailscaleIp;
      }


      
      final registration = ServiceRegistration(
        name: '${AppConfig.serviceName}-${_deviceInfo!.deviceId}',
        serviceType: AppConfig.serviceType,
        host: localIp,
        port: AppConfig.httpServerPort,
        metadata: metadata,
        healthCheckEndpoint: '/health',
        version: AppConfig.version,
      );

      final discoveryUrl = '${_configService.discoveryServiceUrl}/api/v1/services/register';
      _logger.d('Registering at: $discoveryUrl');
      
      final response = await _dio.post(
        discoveryUrl,
        data: registration.toJson(),
        options: Options(
          sendTimeout: AppConfig.discoverySendTimeout,
          receiveTimeout: AppConfig.discoveryReceiveTimeout,
          headers: {
            'Content-Type': 'application/json',
          },
          validateStatus: (status) => status != null && status < 500,
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        _isRegistered = true;
        // Extract service_id from response
        final responseData = response.data as Map<String, dynamic>;
        _serviceId = responseData['service_id'] as String?;
        
        if (_serviceId == null) {
          _logger.w('No service_id in registration response, using service name as fallback');
          _serviceId = registration.name;
        }
        
        // Honor the server-suggested heartbeat interval if provided (Issue #7),
        // otherwise keep the configured default.
        final serverInterval = responseData['heartbeat_interval'];
        if (serverInterval is int && serverInterval > 0) {
          _serverHeartbeatInterval = Duration(seconds: serverInterval);
          _logger.d('Using server heartbeat interval: ${serverInterval}s');
        } else {
          _serverHeartbeatInterval = null;
        }

        _logger.i('Successfully registered with discovery service');
        _logger.d('Service ID: $_serviceId');
        return true;
      } else if (response.statusCode == 401 || response.statusCode == 403) {
        _lastError = 'Authentication failed (credentials mismatch). Please verify backend credentials/configuration.';
        _logger.w('Discovery registration unauthorized: ${response.statusCode}');
        _logger.d('Response: ${response.data}');
        return false;
      } else {
        _lastError = 'Discovery registration failed (HTTP ${response.statusCode})';
        _logger.w('Registration failed with status: ${response.statusCode}');
        _logger.d('Response: ${response.data}');
        return false;
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        _lastError = 'Connection timeout to discovery service (${_configService.discoveryServiceUrl}).';
        _logger.w('Discovery service connection timeout - will retry with heartbeat');
      } else if (e.type == DioExceptionType.connectionError) {
        _lastError = 'Cannot connect to discovery service at ${_configService.discoveryServiceUrl}';
        _logger.w('Cannot connect to discovery service at ${_configService.discoveryServiceUrl}');
        _logger.w('Service will continue without registration');
      } else if (
          e.type == DioExceptionType.badResponse &&
          (e.response?.statusCode == 401 || e.response?.statusCode == 403)) {
        _lastError = 'Authentication failed (credentials mismatch). Please verify backend credentials/configuration.';
        _logger.w('Discovery registration unauthorized: ${e.response?.statusCode}');
      } else {
        _lastError = 'Discovery registration failed: ${e.message}';
        _logger.e('DioException during registration', error: e);
      }
      return false;
    } catch (e, stackTrace) {
      _lastError = 'Unexpected discovery registration error: $e';
      _logger.e('Unexpected error during registration', error: e, stackTrace: stackTrace);
      return false;
    }
  }

/// Register the player as an edge device (Issue #6, dual registration) so the
  /// device registry can track it by type, capabilities and VPN reachability.
  Future<bool> _registerAsEdgeDevice() async {
    if (_deviceInfo == null) {
      return false;
    }
    try {
      final localIp = await DeviceInfoHelper.getLocalIpAddress();
      final authorityTailscaleIp = await _resolveOwnTailscaleIp();
      final metadata = _deviceInfo!.toJson();
      final tailscaleIp = authorityTailscaleIp ??
          (localIp.startsWith('100.') ? localIp : null);
      if (tailscaleIp != null && tailscaleIp.isNotEmpty) {
        metadata['tailscale_ip'] = tailscaleIp;
      }

      final deviceData = {
        'device_name': '${AppConfig.serviceName}-${_deviceInfo!.deviceId}',
        'device_type': 'signage_player',
        'capabilities': _deviceInfo!.capabilities,
        'platform_info': {
          'platform': _deviceInfo!.platform,
          'platform_version': _deviceInfo!.platformVersion,
          'app_version': _deviceInfo!.appVersion,
        },
        'network_interfaces': [
          {
            'interface_name': 'default',
            'ip_address': localIp,
            'network_type': localIp.startsWith('100.') ? 'vpn' : 'ethernet',
            'is_active': true,
          },
        ],
        'metadata': metadata,
      };

      final url = '${_configService.discoveryServiceUrl}/api/v1/devices/register';
      _logger.i('Registering as edge device at $url');
      final response = await _dio.post(
        url,
        data: deviceData,
        options: Options(
          sendTimeout: AppConfig.discoverySendTimeout,
          receiveTimeout: AppConfig.discoveryReceiveTimeout,
          headers: {'Content-Type': 'application/json'},
          validateStatus: (status) => status != null && status < 500,
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data as Map<String, dynamic>;
        _deviceRegistrationId =
            (data['device_id'] as String?) ?? (data['service_id'] as String?);
        _isDeviceRegistered = true;
        _logger.i('Successfully registered as edge device: $_deviceRegistrationId');
        return true;
      }
      _logger.w('Edge device registration failed with status: ${response.statusCode}');
      return false;
    } on DioException catch (e) {
      _logger.w('Edge device registration DioException: ${e.message}');
      return false;
    } catch (e, stackTrace) {
      _logger.w('Edge device registration error: $e');
      _logger.w('Stack trace: $stackTrace');
      return false;
    }
  }

  /// Send heartbeat to discovery service
  Future<void> sendHeartbeat() async {
    // Edge-device heartbeat (Issue #6) — independent of the service heartbeat.
    await _sendDeviceHeartbeat();

    if (!_isRegistered || _serviceId == null) {
      _logger.d('Not registered, attempting registration...');
      await register();
      return;
    }

    try {
      _logger.d('Sending heartbeat to discovery service...');
      
      final heartbeatUrl = '${_configService.discoveryServiceUrl}/api/v1/services/heartbeat';
      _logger.d('Heartbeat URL: $heartbeatUrl');
      _logger.d('Service ID: $_serviceId');
      // Re-resolve our own mesh (VPN) IP on every heartbeat so discovery's
      // top-level `tailscale_ip` stays current. Else the platform signage
      // resolver keeps dialing our (unreachable) LAN host over the mesh.

      final meshIp = await _resolveOwnTailscaleIp();
      final heartbeatMetadata = (meshIp == null || meshIp.isEmpty)
          ? <String, dynamic>{}
          : <String, dynamic>{
              'tailscale_ip': meshIp,
              'tailscale_port': AppConfig.httpServerPort,
            };
      
      final heartbeatData = {
        'service_id': _serviceId,
        'status': 'healthy',
        'metadata': heartbeatMetadata,
      };
      _logger.d('Heartbeat payload: $heartbeatData');
      
      final response = await _dio.post(
        heartbeatUrl,
        data: heartbeatData,
        options: Options(
          headers: {
            'Content-Type': 'application/json',
          },
          sendTimeout: AppConfig.heartbeatSendTimeout,
          receiveTimeout: AppConfig.heartbeatReceiveTimeout,
        ),
      );

      if (response.statusCode == 200) {
        _logger.d('Heartbeat sent successfully');
      } else {
        _logger.w('Heartbeat failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        _logger.w('Heartbeat timeout - discovery service may be unavailable');
        _logger.w('Timeout details: ${e.message}');
      } else if (e.type == DioExceptionType.connectionError) {
        _logger.w('Heartbeat connection error - will retry on next interval');
        _logger.w('Connection error details: ${e.message}');
        _logger.w('Error type: ${e.type}');
        if (e.response != null) {
          _logger.w('Response status: ${e.response?.statusCode}');
          _logger.w('Response data: ${e.response?.data}');
        }
      } else {
        _logger.w('Heartbeat DioException type: ${e.type}');
        _logger.w('Heartbeat DioException message: ${e.message}');
        _logger.w('Heartbeat DioException response: ${e.response?.statusCode} - ${e.response?.data}');
      }
    } catch (e, stackTrace) {
      _logger.w('Heartbeat error: $e');
      _logger.w('Stack trace: $stackTrace');
    }
  }

/// Keep the edge-device registration alive (Issue #6). Independent of, and
  /// in addition to, the service heartbeat.
  Future<void> _sendDeviceHeartbeat() async {
    if (!_isDeviceRegistered || _deviceRegistrationId == null) {
      return;
    }
    try {
      final url = '${_configService.discoveryServiceUrl}/api/v1/devices/heartbeat';
      // Re-resolve our own mesh IP on every device heartbeat so discovery's edge
      // device registry also tracks the fresh VPN address after enrollment.
      final deviceMeshIp = await _resolveOwnTailscaleIp();
      final deviceHeartbeatMetadata =
          (deviceMeshIp == null || deviceMeshIp.isEmpty)
              ? <String, dynamic>{}
              : <String, dynamic>{
                  'tailscale_ip': deviceMeshIp,
                  'tailscale_port': AppConfig.httpServerPort,
                };

      final data = {
        'device_id': _deviceRegistrationId,
        'status': 'healthy',
        'metadata': deviceHeartbeatMetadata,
      };
      final response = await _dio.post(
        url,
        data: data,
        options: Options(
          headers: {'Content-Type': 'application/json'},
          sendTimeout: AppConfig.heartbeatSendTimeout,
          receiveTimeout: AppConfig.heartbeatReceiveTimeout,
        ),
      );
      if (response.statusCode == 200) {
        _logger.d('Edge device heartbeat sent successfully');
      } else {
        _logger.w('Edge device heartbeat failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.w('Edge device heartbeat DioException: ${e.message}');
    } catch (e) {
      _logger.w('Edge device heartbeat error: $e');
    }
  }
  /// Start heartbeat timer using the server-suggested interval when available (Issue #7)
  void _startHeartbeat() {
    final interval = _serverHeartbeatInterval ?? AppConfig.heartbeatInterval;
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(
      interval,
      (_) => sendHeartbeat(),
    );
    _logger.d('Heartbeat timer started (${interval.inSeconds}s interval)');
  }

  /// Retry registration periodically after a failure so the player does not stay
  /// stuck in offline mode indefinitely (Issue #3).
  void _startRegistrationRetry() {
    if (_isRegistered) return;

    _registrationRetryTimer?.cancel();
    _registrationRetryTimer = Timer.periodic(
      AppConfig.registrationRetryDelay,
      (_) async {
        if (_isRegistered) {
          _registrationRetryTimer?.cancel();
          _registrationRetryTimer = null;
          return;
        }
        final ok = await register();
        if (ok) {
          _registrationRetryTimer?.cancel();
          _registrationRetryTimer = null;
          if (_heartbeatTimer == null) {
            _startHeartbeat();
          }
          _logger.i('Registration recovered; heartbeat active');
        } else {
          _logger.d('Registration retry still failing; will retry again in '
              '${AppConfig.registrationRetryDelay.inSeconds}s');
        }
      },
    );
    _logger.d('Registration retry timer started '
        '(${AppConfig.registrationRetryDelay.inSeconds}s interval)');
  }

/// Deregister the edge-device registration (Issue #6).
  Future<void> _deregisterDevice() async {
    if (!_isDeviceRegistered || _deviceRegistrationId == null) {
      return;
    }
    try {
      final url =
          '${_configService.discoveryServiceUrl}/api/v1/devices/$_deviceRegistrationId';
      final response = await _dio.delete(
        url,
        options: Options(
          sendTimeout: AppConfig.deregisterSendTimeout,
          receiveTimeout: AppConfig.deregisterReceiveTimeout,
        ),
      );
      if (response.statusCode == 200 || response.statusCode == 204) {
        _logger.i('Successfully deregistered edge device');
      } else {
        _logger.w('Edge device deregistration failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.w('Edge device deregistration DioException: ${e.message}');
    } catch (e) {
      _logger.w('Edge device deregistration error: $e');
    } finally {
      _isDeviceRegistered = false;
      _deviceRegistrationId = null;
    }
  }
  /// Deregister from discovery service
  Future<void> deregister() async {
    // Edge-device deregistration (Issue #6) — independent of service registration.
    await _deregisterDevice();

    if (!_isRegistered || _serviceId == null) {
      _logger.d('Not registered, skipping deregistration');
      return;
    }

    try {
      _logger.i('Deregistering from discovery service...');
      
      final response = await _dio.delete(
        '${_configService.discoveryServiceUrl}/api/v1/services/$_serviceId',
        options: Options(
          sendTimeout: AppConfig.deregisterSendTimeout,
          receiveTimeout: AppConfig.deregisterReceiveTimeout,
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        _logger.i('Successfully deregistered from discovery service');
      } else {
        _logger.w('Deregistration failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.w('Deregistration DioException: ${e.message}');
    } catch (e) {
      _logger.w('Deregistration error: $e');
    } finally {
      _isRegistered = false;
      _serviceId = null;
    }
  }

  /// Stop the heartbeat timer, cancel any pending registration retry, and deregister
  Future<void> dispose() async {
    _logger.i('Disposing Discovery Service...');
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _registrationRetryTimer?.cancel();
    _registrationRetryTimer = null;
    await deregister();
    _logger.i('Discovery Service disposed');
  }

  // Getters
  bool get isRegistered => _isRegistered;
  String? get serviceId => _serviceId;
  DeviceInfoModel? get deviceInfo => _deviceInfo;
  String? get lastError => _lastError;
  Map<String, dynamic>? get discoveredTopology => _lastTopology;
  bool get isDeviceRegistered => _isDeviceRegistered;
  String? get deviceRegistrationId => _deviceRegistrationId;
}
