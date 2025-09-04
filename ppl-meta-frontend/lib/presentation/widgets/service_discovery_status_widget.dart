import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/service_discovery_providers.dart';
import '../services/dynamic_service_provider.dart';
import '../services/discovery_service_client.dart';

class ServiceDiscoveryStatusWidget extends ConsumerWidget {
  const ServiceDiscoveryStatusWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final discoveryInit = ref.watch(serviceDiscoveryInitProvider);
    
    return discoveryInit.when(
      data: (initialized) {
        if (!initialized) {
          return const Card(
            child: ListTile(
              leading: Icon(Icons.warning, color: Colors.orange),
              title: Text('Service Discovery Disabled'),
              subtitle: Text('Using static service URLs'),
            ),
          );
        }
        
        return const ExpandableServiceDiscoveryStatus();
      },
      loading: () => const Card(
        child: ListTile(
          leading: CircularProgressIndicator(),
          title: Text('Initializing Service Discovery'),
          subtitle: Text('Connecting to discovery service...'),
        ),
      ),
      error: (error, stack) => Card(
        child: ListTile(
          leading: const Icon(Icons.error, color: Colors.red),
          title: const Text('Service Discovery Error'),
          subtitle: Text('Error: $error'),
          trailing: IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.refresh(serviceDiscoveryInitProvider),
          ),
        ),
      ),
    );
  }
}

class ExpandableServiceDiscoveryStatus extends ConsumerStatefulWidget {
  const ExpandableServiceDiscoveryStatus({super.key});

  @override
  ConsumerState<ExpandableServiceDiscoveryStatus> createState() =>
      _ExpandableServiceDiscoveryStatusState();
}

class _ExpandableServiceDiscoveryStatusState
    extends ConsumerState<ExpandableServiceDiscoveryStatus> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.hub, color: Colors.green),
            title: const Text('Service Discovery Active'),
            subtitle: const Text('Dynamic service URLs enabled'),
            trailing: IconButton(
              icon: Icon(_isExpanded ? Icons.expand_less : Icons.expand_more),
              onPressed: () => setState(() => _isExpanded = !_isExpanded),
            ),
          ),
          if (_isExpanded) ...[
            const Divider(),
            _buildServiceStatusList(),
          ],
        ],
      ),
    );
  }

  Widget _buildServiceStatusList() {
    final services = ['gateway', 'media', 'orchestrator', 'vision', 'node', 'cameras'];
    
    return Column(
      children: services.map((serviceName) {
        return _buildServiceStatusTile(serviceName);
      }).toList(),
    );
  }

  Widget _buildServiceStatusTile(String serviceName) {
    final serviceUrlAsync = ref.watch(serviceUrlProvider(serviceName));
    
    return serviceUrlAsync.when(
      data: (url) => ListTile(
        dense: true,
        leading: const Icon(Icons.check_circle, color: Colors.green, size: 16),
        title: Text(serviceName.toUpperCase()),
        subtitle: Text(url),
        trailing: IconButton(
          icon: const Icon(Icons.refresh, size: 16),
          onPressed: () => ref.refresh(serviceUrlProvider(serviceName)),
        ),
      ),
      loading: () => ListTile(
        dense: true,
        leading: const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        title: Text(serviceName.toUpperCase()),
        subtitle: const Text('Discovering...'),
      ),
      error: (error, stack) => ListTile(
        dense: true,
        leading: const Icon(Icons.error, color: Colors.orange, size: 16),
        title: Text(serviceName.toUpperCase()),
        subtitle: Text('Error: $error'),
        trailing: IconButton(
          icon: const Icon(Icons.refresh, size: 16),
          onPressed: () => ref.refresh(serviceUrlProvider(serviceName)),
        ),
      ),
    );
  }
}

/// Service Discovery Debug Panel for developers
class ServiceDiscoveryDebugPanel extends ConsumerWidget {
  const ServiceDiscoveryDebugPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const ListTile(
            leading: Icon(Icons.bug_report),
            title: Text('Service Discovery Debug'),
          ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    ElevatedButton(
                      onPressed: () => ref.refresh(serviceDiscoveryInitProvider),
                      child: const Text('Refresh Discovery'),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: () => _testAllServices(ref),
                      child: const Text('Test All Services'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Text('Discovery Service Status:'),
                StreamBuilder<List<ServiceInfo>>(
                  stream: DiscoveryService.instance.servicesStream,
                  builder: (context, snapshot) {
                    if (snapshot.hasData) {
                      final services = snapshot.data!;
                      return Column(
                        children: services.map((service) {
                          return ListTile(
                            dense: true,
                            leading: Icon(
                              service.status == 'healthy' 
                                ? Icons.check_circle 
                                : Icons.warning,
                              color: service.status == 'healthy' 
                                ? Colors.green 
                                : Colors.orange,
                              size: 16,
                            ),
                            title: Text('${service.name} (${service.serviceType})'),
                            subtitle: Text('${service.host}:${service.port} - ${service.status}'),
                          );
                        }).toList(),
                      );
                    } else if (snapshot.hasError) {
                      return Text('Error: ${snapshot.error}');
                    } else {
                      return const CircularProgressIndicator();
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _testAllServices(WidgetRef ref) {
    final services = ['gateway', 'media', 'orchestrator', 'vision', 'node', 'cameras'];
    for (final service in services) {
      ref.refresh(serviceUrlProvider(service));
    }
  }
}
