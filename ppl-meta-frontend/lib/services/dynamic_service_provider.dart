import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'discovery_service_client.dart';
import '../core/config.dart';

/// Dynamic service configuration that uses discovery service
class DynamicServiceConfig {
  final Map<String, String> _staticUrls = {};
  final Map<String, String> _discoveredUrls = {};
  bool _discoveryEnabled = true;
  
  DynamicServiceConfig() {
    // Initialize with static URLs from AppConfig as fallback
    _initializeStaticUrls();
  }
  
  void _initializeStaticUrls() {
    _staticUrls['gateway'] = Config.gatewayServiceUrl;
    _staticUrls['node'] = Config.nodeServiceUrl;
    _staticUrls['media'] = Config.mediaServiceUrl;
    _staticUrls['orchestrator'] = Config.orchestratorServiceUrl;
    _staticUrls['vision'] = Config.visionServiceUrl;
    _staticUrls['cameras'] = Config.camerasServiceUrl;
  }
  
  /// Update discovered URLs from discovery service
  void updateDiscoveredServices(Map<String, ServiceInfo> services) {
    _discoveredUrls.clear();
    
    for (final service in services.values) {
      if (service.isHealthy) {
        // Map service names to shorter keys
        final key = _getServiceKey(service.name);
        if (key != null) {
          _discoveredUrls[key] = service.baseUrl;
        }
      }
    }
  }
  
  /// Map full service names to shorter keys
  String? _getServiceKey(String serviceName) {
    switch (serviceName) {
      case 'ppl-meta-gateway':
        return 'gateway';
      case 'ppl-meta-node':
        return 'node';
      case 'ppl-meta-media':
        return 'media';
      case 'ppl-meta-orchestrator':
        return 'orchestrator';
      case 'ppl-meta-vision':
        return 'vision';
      case 'ppl-meta-cameras':
        return 'cameras';
      default:
        return null;
    }
  }
  
  /// Get service URL with fallback to static configuration
  String getServiceUrl(String serviceKey) {
    // Try discovered URL first (if discovery is enabled and available)
    if (_discoveryEnabled && _discoveredUrls.containsKey(serviceKey)) {
      return _discoveredUrls[serviceKey]!;
    }
    
    // Fallback to static URL
    return _staticUrls[serviceKey] ?? Config.gatewayServiceUrl;
  }
  
  /// Enable or disable discovery service usage
  void setDiscoveryEnabled(bool enabled) {
    _discoveryEnabled = enabled;
  }
  
  /// Check if discovery service is being used for a service
  bool isUsingDiscovery(String serviceKey) {
    return _discoveryEnabled && _discoveredUrls.containsKey(serviceKey);
  }
  
  /// Get all service URLs (both discovered and static)
  Map<String, String> getAllServiceUrls() {
    final result = Map<String, String>.from(_staticUrls);
    if (_discoveryEnabled) {
      result.addAll(_discoveredUrls);
    }
    return result;
  }
  
  /// Get discovery status for all services
  Map<String, dynamic> getDiscoveryStatus() {
    return {
      'discoveryEnabled': _discoveryEnabled,
      'discoveredServices': _discoveredUrls.keys.toList(),
      'staticServices': _staticUrls.keys.toList(),
      'serviceUrls': getAllServiceUrls(),
    };
  }
}

/// Provider for dynamic service configuration
final dynamicServiceConfigProvider = StateProvider<DynamicServiceConfig>((ref) {
  return DynamicServiceConfig();
});

/// Provider for discovery service client
final discoveryServiceProvider = Provider<DiscoveryServiceClient>((ref) {
  return DiscoveryService.instance;
});

/// Provider that watches for service discovery updates
final serviceDiscoveryWatcherProvider = StreamProvider<Map<String, ServiceInfo>>((ref) {
  final discoveryClient = ref.watch(discoveryServiceProvider);
  final config = ref.watch(dynamicServiceConfigProvider.notifier);
  
  // Listen to service updates and update configuration
  return discoveryClient.servicesStream.map((services) {
    config.state.updateDiscoveredServices(services);
    return services;
  });
});

/// Provider for specific service URLs with dynamic discovery
final serviceUrlProvider = Provider.family<String, String>((ref, serviceKey) {
  // Watch for service discovery updates
  ref.watch(serviceDiscoveryWatcherProvider);
  
  // Get current configuration
  final config = ref.watch(dynamicServiceConfigProvider);
  
  return config.getServiceUrl(serviceKey);
});

/// Convenience providers for specific services
final gatewayUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('gateway')));
final nodeUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('node')));
final mediaUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('media')));
final orchestratorUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('orchestrator')));
final visionUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('vision')));
final camerasUrlProvider = Provider<String>((ref) => ref.watch(serviceUrlProvider('cameras')));

/// Provider that initializes service discovery
final serviceDiscoveryInitProvider = FutureProvider<bool>((ref) async {
  final discoveryClient = ref.watch(discoveryServiceProvider);
  
  try {
    // Check if discovery service is available
    final isAvailable = await discoveryClient.isDiscoveryServiceAvailable();
    
    if (isAvailable) {
      // Initial discovery
      await discoveryClient.discoverServices();
      return true;
    } else {
      // Disable discovery and use static URLs
      final config = ref.read(dynamicServiceConfigProvider.notifier);
      config.state.setDiscoveryEnabled(false);
      return false;
    }
  } catch (e) {
    // Disable discovery on error
    final config = ref.read(dynamicServiceConfigProvider.notifier);
    config.state.setDiscoveryEnabled(false);
    return false;
  }
});
