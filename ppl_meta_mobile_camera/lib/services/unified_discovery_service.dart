import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'multicast_network_discovery.dart';

/// Service information from PPL Meta Discovery Service
class DiscoveredServiceInfo {
  final String serviceId;
  final String name;
  final String serviceType;
  final String version;
  final String host;
  final int port;
  final String healthEndpoint;
  final String status;
  final List<String> capabilities;
  final Map<String, dynamic> metadata;
  final DateTime registeredAt;
  final DateTime lastSeen;
  final String discoveryMethod;

  DiscoveredServiceInfo({
    required this.serviceId,
    required this.name,
    required this.serviceType,
    required this.version,
    required this.host,
    required this.port,
    required this.healthEndpoint,
    required this.status,
    required this.capabilities,
    required this.metadata,
    required this.registeredAt,
    required this.lastSeen,
    required this.discoveryMethod,
  });

  factory DiscoveredServiceInfo.fromDiscoveryService(Map<String, dynamic> json) {
    return DiscoveredServiceInfo(
      serviceId: json['service_id'] ?? '',
      name: json['name'] ?? '',
      serviceType: json['service_type'] ?? '',
      version: json['version'] ?? '',
      host: json['host'] ?? '',
      port: json['port'] ?? 0,
      healthEndpoint: json['health_endpoint'] ?? '/health',
      status: json['status'] ?? 'unknown',
      capabilities: List<String>.from(json['capabilities'] ?? []),
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
      registeredAt: DateTime.tryParse(json['registered_at'] ?? '') ?? DateTime.now(),
      lastSeen: DateTime.tryParse(json['last_seen'] ?? '') ?? DateTime.now(),
      discoveryMethod: 'central_discovery',
    );
  }

  factory DiscoveredServiceInfo.fromMulticast(ServiceAnnouncement announcement) {
    return DiscoveredServiceInfo(
      serviceId: '${announcement.ip}:${announcement.port}',
      name: announcement.service,
      serviceType: 'backend',
      version: announcement.version,
      host: announcement.ip,
      port: announcement.port,
      healthEndpoint: announcement.healthUrl ?? '/health',
      status: announcement.isRecent ? 'healthy' : 'stale',
      capabilities: announcement.capabilities,
      metadata: {
        'protocol': announcement.protocol,
        'endpoints': announcement.endpoints,
      },
      registeredAt: DateTime.fromMillisecondsSinceEpoch(announcement.timestamp * 1000),
      lastSeen: DateTime.fromMillisecondsSinceEpoch(announcement.timestamp * 1000),
      discoveryMethod: 'multicast',
    );
  }

  /// Get the base URL for this service
  String get baseUrl => 'http://$host:$port';

  /// Check if this service is healthy
  bool get isHealthy => status == 'healthy';

  /// Check if this service is a Node service
  bool get isNodeService => name.contains('node') || capabilities.contains('authentication');

  @override
  String toString() {
    return 'DiscoveredServiceInfo(name: $name, host: $host:$port, status: $status, method: $discoveryMethod)';
  }
}

/// Unified discovery service combining multicast and centralized discovery
class UnifiedDiscoveryService {
  static const String _defaultDiscoveryUrl = 'http://localhost:8006';
  static const Duration _discoveryTimeout = Duration(seconds: 10);
  static const Duration _healthCheckTimeout = Duration(seconds: 5);

  final Dio _dio;
  final EnhancedNetworkDiscoveryService _multicastService;
  final Map<String, DiscoveredServiceInfo> _discoveredServices = {};
  final StreamController<List<DiscoveredServiceInfo>> _servicesController =
      StreamController<List<DiscoveredServiceInfo>>.broadcast();

  UnifiedDiscoveryService() 
    : _dio = Dio(BaseOptions(
        connectTimeout: _healthCheckTimeout,
        receiveTimeout: _healthCheckTimeout,
      )),
      _multicastService = EnhancedNetworkDiscoveryService();

  /// Stream of discovered services
  Stream<List<DiscoveredServiceInfo>> get servicesStream => _servicesController.stream;

  /// Get current list of discovered services
  List<DiscoveredServiceInfo> get currentServices => _discoveredServices.values.toList();

  /// Get all healthy services
  List<DiscoveredServiceInfo> get healthyServices => 
      currentServices.where((s) => s.isHealthy).toList();

  /// Get Node services specifically
  List<DiscoveredServiceInfo> get nodeServices => 
      currentServices.where((s) => s.isNodeService).toList();

  /// Discover all services using multiple methods
  Future<List<DiscoveredServiceInfo>> discoverAllServices({
    List<String>? discoveryUrls,
    Duration? timeout,
  }) async {
    timeout ??= _discoveryTimeout;
    debugPrint('🎯 Starting unified service discovery...');

    final List<Future<List<DiscoveredServiceInfo>>> discoveryTasks = [];

    // Task 1: Central discovery service
    discoveryTasks.add(_discoverFromCentralService(discoveryUrls));

    // Task 2: Multicast discovery
    discoveryTasks.add(_discoverFromMulticast());

    // Task 3: Local network scanning (fallback)
    discoveryTasks.add(_discoverFromLocalScan());

    try {
      // Wait for all discovery methods to complete or timeout
      final results = await Future.wait(
        discoveryTasks,
        eagerError: false,
      ).timeout(timeout);

      // Combine and deduplicate results
      final allServices = <String, DiscoveredServiceInfo>{};
      
      for (final serviceList in results) {
        for (final service in serviceList) {
          final key = '${service.name}:${service.host}:${service.port}';
          // Prefer central discovery over multicast, multicast over local scan
          if (!allServices.containsKey(key) || 
              (service.discoveryMethod == 'central_discovery' && 
               allServices[key]?.discoveryMethod != 'central_discovery')) {
            allServices[key] = service;
          }
        }
      }

      _discoveredServices.clear();
      _discoveredServices.addAll(allServices);
      
      final servicesList = allServices.values.toList();
      _servicesController.add(servicesList);

      debugPrint('✅ Unified discovery completed: ${servicesList.length} services found');
      for (final service in servicesList) {
        debugPrint('   - ${service.name} at ${service.baseUrl} (${service.discoveryMethod})');
      }

      return servicesList;

    } catch (e) {
      debugPrint('❌ Unified discovery error: $e');
      return [];
    }
  }

  /// Discover services from central PPL Meta Discovery Service
  Future<List<DiscoveredServiceInfo>> _discoverFromCentralService(
    List<String>? discoveryUrls,
  ) async {
    debugPrint('📡 Attempting central discovery service...');
    
    final urls = discoveryUrls ?? [
      _defaultDiscoveryUrl,
      'http://localhost:8006',
      'http://127.0.0.1:8006',
    ];

    for (final url in urls) {
      try {
        debugPrint('🔍 Trying discovery service: $url');
        
        final response = await _dio.get(
          '$url/api/v1/services',
          options: Options(
            headers: {'Accept': 'application/json'},
          ),
        );

        if (response.statusCode == 200) {
          final data = response.data as Map<String, dynamic>;
          final services = (data['services'] as List)
              .map((s) => DiscoveredServiceInfo.fromDiscoveryService(s))
              .toList();

          debugPrint('✅ Central discovery successful: ${services.length} services');
          return services;
        }
      } catch (e) {
        debugPrint('⚠️ Central discovery failed for $url: $e');
      }
    }

    debugPrint('❌ All central discovery attempts failed');
    return [];
  }

  /// Discover services using multicast
  Future<List<DiscoveredServiceInfo>> _discoverFromMulticast() async {
    debugPrint('📻 Attempting multicast discovery...');
    
    try {
      final nodeService = await _multicastService.findNodeService(
        timeout: const Duration(seconds: 8),
      );

      if (nodeService != null) {
        final discoveredService = DiscoveredServiceInfo.fromMulticast(nodeService);
        debugPrint('✅ Multicast discovery successful: ${discoveredService.name}');
        return [discoveredService];
      } else {
        debugPrint('⚠️ No services found via multicast');
        return [];
      }
    } catch (e) {
      debugPrint('❌ Multicast discovery error: $e');
      return [];
    }
  }

  /// Discover services by scanning local network
  Future<List<DiscoveredServiceInfo>> _discoverFromLocalScan() async {
    debugPrint('🌐 Attempting local network scan...');
    
    try {
      // Use the existing network discovery logic
      final nodeUrl = await _multicastService.autoDiscoverNodeService();
      
      if (nodeUrl != null) {
        // Parse the URL to extract host and port
        final uri = Uri.parse(nodeUrl);
        final service = DiscoveredServiceInfo(
          serviceId: '${uri.host}:${uri.port}',
          name: 'ppl-meta-node',
          serviceType: 'backend',
          version: '1.0.0',
          host: uri.host,
          port: uri.port,
          healthEndpoint: '/api/v1/health',
          status: 'healthy',
          capabilities: ['authentication', 'node'],
          metadata: {'scanned': true},
          registeredAt: DateTime.now(),
          lastSeen: DateTime.now(),
          discoveryMethod: 'local_scan',
        );

        debugPrint('✅ Local scan successful: ${service.baseUrl}');
        return [service];
      } else {
        debugPrint('⚠️ Local scan found no services');
        return [];
      }
    } catch (e) {
      debugPrint('❌ Local scan error: $e');
      return [];
    }
  }

  /// Find the best Node service for authentication
  Future<DiscoveredServiceInfo?> findBestNodeService({
    List<String>? discoveryUrls,
  }) async {
    debugPrint('🎯 Finding best Node service...');
    
    final services = await discoverAllServices(discoveryUrls: discoveryUrls);
    final nodeServices = services.where((s) => s.isNodeService && s.isHealthy).toList();

    if (nodeServices.isEmpty) {
      debugPrint('❌ No healthy Node services found');
      return null;
    }

    // Priority: central_discovery > multicast > local_scan
    nodeServices.sort((a, b) {
      const methodPriority = {
        'central_discovery': 3,
        'multicast': 2,
        'local_scan': 1,
      };
      
      final aPriority = methodPriority[a.discoveryMethod] ?? 0;
      final bPriority = methodPriority[b.discoveryMethod] ?? 0;
      
      if (aPriority != bPriority) {
        return bPriority.compareTo(aPriority); // Higher priority first
      }
      
      // If same method, prefer more recent
      return b.lastSeen.compareTo(a.lastSeen);
    });

    final bestService = nodeServices.first;
    
    // Verify the service is actually accessible
    if (await _verifyServiceHealth(bestService)) {
      debugPrint('✅ Best Node service selected: ${bestService.baseUrl} (${bestService.discoveryMethod})');
      return bestService;
    } else {
      debugPrint('⚠️ Best Node service failed health check, trying alternatives...');
      
      // Try other services
      for (int i = 1; i < nodeServices.length; i++) {
        if (await _verifyServiceHealth(nodeServices[i])) {
          debugPrint('✅ Alternative Node service selected: ${nodeServices[i].baseUrl}');
          return nodeServices[i];
        }
      }
      
      debugPrint('❌ No accessible Node services found');
      return null;
    }
  }

  /// Verify service health
  Future<bool> _verifyServiceHealth(DiscoveredServiceInfo service) async {
    try {
      final healthUrl = '${service.baseUrl}${service.healthEndpoint}';
      debugPrint('🩺 Health check: $healthUrl');
      
      final response = await _dio.get(healthUrl);
      final isHealthy = response.statusCode == 200;
      
      debugPrint('🩺 Health check ${service.baseUrl}: ${isHealthy ? '✅' : '❌'} (${response.statusCode})');
      return isHealthy;
      
    } catch (e) {
      debugPrint('🩺 Health check ${service.baseUrl}: ❌ ($e)');
      return false;
    }
  }

  /// Get services of a specific type
  List<DiscoveredServiceInfo> getServicesByType(String serviceType) {
    return currentServices.where((s) => s.serviceType == serviceType).toList();
  }

  /// Get service by name
  DiscoveredServiceInfo? getServiceByName(String name) {
    return currentServices.where((s) => s.name == name).firstOrNull;
  }

  /// Dispose resources
  void dispose() {
    _multicastService.dispose();
    _servicesController.close();
    _dio.close();
  }
}

/// Extension for null-safe first operation
extension IterableExtension<T> on Iterable<T> {
  T? get firstOrNull {
    return isEmpty ? null : first;
  }
}
