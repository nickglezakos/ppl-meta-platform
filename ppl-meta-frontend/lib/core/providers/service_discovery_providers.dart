import 'package:flutter_riverpod/flutter_riverpod.dart';

// Placeholder provider for service discovery initialization
final serviceDiscoveryInitProvider = FutureProvider<bool>((ref) async {
  return true;
});

// Service info model placeholder
class ServiceInfo {
  final String name;
  final String serviceType;
  final String host;
  final int port;
  final String status;
  
  ServiceInfo({
    required this.name,
    required this.serviceType,
    required this.host,
    required this.port,
    required this.status,
  });
}

// Discovery service placeholder
class DiscoveryService {
  List<ServiceInfo> getServices() => [];
}
