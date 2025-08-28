import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Service information returned by discovery service
class ServiceInfo {
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

  ServiceInfo({
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
  });

  factory ServiceInfo.fromJson(Map<String, dynamic> json) {
    return ServiceInfo(
      serviceId: json['service_id'] ?? '',
      name: json['name'] ?? '',
      serviceType: json['service_type'] ?? '',
      version: json['version'] ?? '',
      host: json['host'] ?? 'localhost',
      port: json['port'] ?? 8080,
      healthEndpoint: json['health_endpoint'] ?? '/health',
      status: json['status'] ?? 'unknown',
      capabilities: List<String>.from(json['capabilities'] ?? []),
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
      registeredAt: DateTime.tryParse(json['registered_at'] ?? '') ?? DateTime.now(),
      lastSeen: DateTime.tryParse(json['last_seen'] ?? '') ?? DateTime.now(),
    );
  }

  /// Get the service URL
  String get baseUrl => 'http://$host:$port';
  
  /// Check if the service is healthy
  bool get isHealthy => status == 'healthy';
  
  /// Check if the service has a specific capability
  bool hasCapability(String capability) => capabilities.contains(capability);
}

/// Discovery service response containing list of services
class DiscoveryResponse {
  final List<ServiceInfo> services;
  final int totalCount;
  final int healthyCount;

  DiscoveryResponse({
    required this.services,
    required this.totalCount,
    required this.healthyCount,
  });

  factory DiscoveryResponse.fromJson(Map<String, dynamic> json) {
    return DiscoveryResponse(
      services: (json['services'] as List? ?? [])
          .map((s) => ServiceInfo.fromJson(s))
          .toList(),
      totalCount: json['total_count'] ?? 0,
      healthyCount: json['healthy_count'] ?? 0,
    );
  }
}

/// PPL Meta Discovery Service Client for Flutter
/// 
/// Provides dynamic service discovery capabilities to the frontend,
/// allowing it to discover backend services automatically instead of
/// using hardcoded URLs.
class DiscoveryServiceClient {
  final Dio _dio;
  final String _discoveryServiceUrl;
  
  // Cache for discovered services
  final Map<String, ServiceInfo> _serviceCache = {};
  Timer? _refreshTimer;
  
  // Stream controller for service updates
  final StreamController<Map<String, ServiceInfo>> _servicesController = 
      StreamController<Map<String, ServiceInfo>>.broadcast();
  
  DiscoveryServiceClient({
    String discoveryServiceUrl = 'http://localhost:8006',
    Dio? dio,
  }) : _discoveryServiceUrl = discoveryServiceUrl,
       _dio = dio ?? Dio() {
    _dio.options.connectTimeout = const Duration(seconds: 5);
    _dio.options.receiveTimeout = const Duration(seconds: 10);
    
    // Start periodic refresh
    _startPeriodicRefresh();
  }

  /// Stream of service updates
  Stream<Map<String, ServiceInfo>> get servicesStream => _servicesController.stream;
  
  /// Get all discovered services
  Map<String, ServiceInfo> get services => Map.unmodifiable(_serviceCache);
  
  /// Discover all services
  Future<DiscoveryResponse> discoverServices({String? serviceType}) async {
    try {
      final uri = serviceType != null 
          ? '$_discoveryServiceUrl/api/v1/services?service_type=$serviceType'
          : '$_discoveryServiceUrl/api/v1/services';
          
      final response = await _dio.get(uri);
      
      if (response.statusCode == 200) {
        final discoveryResponse = DiscoveryResponse.fromJson(response.data);
        
        // Update cache
        _serviceCache.clear();
        for (final service in discoveryResponse.services) {
          _serviceCache[service.name] = service;
        }
        
        // Notify listeners
        _servicesController.add(Map.unmodifiable(_serviceCache));
        
        if (kDebugMode) {
          print('📡 Discovered ${discoveryResponse.services.length} services: ${discoveryResponse.services.map((s) => s.name).join(', ')}');
        }
        
        return discoveryResponse;
      } else {
        throw Exception('Discovery service returned ${response.statusCode}');
      }
    } catch (e) {
      if (kDebugMode) {
        print('❌ Failed to discover services: $e');
      }
      rethrow;
    }
  }
  
  /// Get a specific service by name
  Future<ServiceInfo?> getService(String serviceName) async {
    // Check cache first
    if (_serviceCache.containsKey(serviceName)) {
      final service = _serviceCache[serviceName]!;
      if (service.isHealthy) {
        return service;
      }
    }
    
    // Refresh and try again
    await discoverServices();
    return _serviceCache[serviceName];
  }
  
  /// Get service URL by name
  Future<String?> getServiceUrl(String serviceName) async {
    final service = await getService(serviceName);
    return service?.baseUrl;
  }
  
  /// Get services by capability
  List<ServiceInfo> getServicesByCapability(String capability) {
    return _serviceCache.values
        .where((service) => service.hasCapability(capability) && service.isHealthy)
        .toList();
  }
  
  /// Get services by type
  List<ServiceInfo> getServicesByType(String serviceType) {
    return _serviceCache.values
        .where((service) => service.serviceType == serviceType && service.isHealthy)
        .toList();
  }
  
  /// Check if discovery service is available
  Future<bool> isDiscoveryServiceAvailable() async {
    try {
      final response = await _dio.get('$_discoveryServiceUrl/health');
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Start periodic refresh of services
  void _startPeriodicRefresh() {
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      discoverServices().catchError((e) {
        if (kDebugMode) {
          print('⚠️ Periodic service discovery failed: $e');
        }
      });
    });
  }
  
  /// Stop periodic refresh and cleanup
  void dispose() {
    _refreshTimer?.cancel();
    _servicesController.close();
  }
}

/// Singleton instance for global access
class DiscoveryService {
  static DiscoveryServiceClient? _instance;
  
  static DiscoveryServiceClient get instance {
    _instance ??= DiscoveryServiceClient();
    return _instance!;
  }
  
  static void initialize({
    String discoveryServiceUrl = 'http://localhost:8006',
    Dio? dio,
  }) {
    _instance = DiscoveryServiceClient(
      discoveryServiceUrl: discoveryServiceUrl,
      dio: dio,
    );
  }
  
  static void dispose() {
    _instance?.dispose();
    _instance = null;
  }
}
