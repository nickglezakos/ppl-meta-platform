import 'package:flutter/material.dart';
import 'services/ppl_meta_discovery_client.dart';

/// Test app to verify PPL Meta Discovery Service integration
void main() {
  runApp(const DiscoveryTestApp());
}

class DiscoveryTestApp extends StatelessWidget {
  const DiscoveryTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta Discovery Test',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const DiscoveryTestScreen(),
    );
  }
}

class DiscoveryTestScreen extends StatefulWidget {
  const DiscoveryTestScreen({super.key});

  @override
  State<DiscoveryTestScreen> createState() => _DiscoveryTestScreenState();
}

class _DiscoveryTestScreenState extends State<DiscoveryTestScreen> {
  final PPLMetaDiscoveryClient _discoveryClient = PPLMetaDiscoveryClient();
  final EnhancedNetworkDiscoveryService _networkService = EnhancedNetworkDiscoveryService();
  
  List<ServiceInfo> _discoveredServices = [];
  String _status = 'Ready to test discovery';
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Meta Discovery Test'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Discovery Service Status',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(_status),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        ElevatedButton(
                          onPressed: _isLoading ? null : _testDiscoveryService,
                          child: const Text('Test Discovery Service'),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: _isLoading ? null : _discoverAllServices,
                          child: const Text('Discover All Services'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        ElevatedButton(
                          onPressed: _isLoading ? null : _testNodeDiscovery,
                          child: const Text('Find Node Service'),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: _isLoading ? null : _testGatewayDiscovery,
                          child: const Text('Find Gateway'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Discovered Services (${_discoveredServices.length})',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _discoveredServices.isEmpty
                  ? const Center(
                      child: Text(
                        'No services discovered yet.\nTap "Discover All Services" to start.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 16),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _discoveredServices.length,
                      itemBuilder: (context, index) {
                        final service = _discoveredServices[index];
                        return Card(
                          child: ListTile(
                            leading: Icon(
                              service.status == 'healthy' 
                                  ? Icons.check_circle 
                                  : Icons.warning,
                              color: service.status == 'healthy' 
                                  ? Colors.green 
                                  : Colors.orange,
                            ),
                            title: Text(service.name),
                            subtitle: Text(
                              '${service.serviceType} v${service.version}\n'
                              '${service.host}:${service.port} - ${service.status}\n'
                              'Capabilities: ${service.capabilities.join(", ")}',
                            ),
                            isThreeLine: true,
                            trailing: IconButton(
                              icon: const Icon(Icons.link),
                              onPressed: () => _testServiceConnection(service),
                            ),
                          ),
                        );
                      },
                    ),
            ),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Center(child: CircularProgressIndicator()),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _testDiscoveryService() async {
    setState(() {
      _isLoading = true;
      _status = 'Testing discovery service health...';
    });

    try {
      final isHealthy = await _discoveryClient.testDiscoveryService();
      setState(() {
        _status = isHealthy 
            ? '✅ Discovery service is healthy and accessible'
            : '❌ Discovery service is not accessible';
      });
    } catch (e) {
      setState(() {
        _status = '❌ Discovery service test failed: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _discoverAllServices() async {
    setState(() {
      _isLoading = true;
      _status = 'Discovering all services...';
    });

    try {
      final services = await _discoveryClient.discoverServices();
      setState(() {
        _discoveredServices = services;
        _status = '✅ Discovered ${services.length} healthy services';
      });
    } catch (e) {
      setState(() {
        _status = '❌ Service discovery failed: $e';
        _discoveredServices = [];
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _testNodeDiscovery() async {
    setState(() {
      _isLoading = true;
      _status = 'Testing enhanced node service discovery...';
    });

    try {
      final nodeUrl = await _networkService.autoDiscoverNodeService();
      setState(() {
        _status = nodeUrl != null
            ? '✅ Node service found: $nodeUrl'
            : '❌ Node service not found';
      });
    } catch (e) {
      setState(() {
        _status = '❌ Node discovery failed: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _testGatewayDiscovery() async {
    setState(() {
      _isLoading = true;
      _status = 'Finding gateway service...';
    });

    try {
      final gateway = await _discoveryClient.findGateway();
      setState(() {
        _status = gateway != null
            ? '✅ Gateway found: ${gateway.baseUrl}'
            : '❌ Gateway service not found';
      });
    } catch (e) {
      setState(() {
        _status = '❌ Gateway discovery failed: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _testServiceConnection(ServiceInfo service) async {
    setState(() {
      _status = 'Testing connection to ${service.name}...';
    });

    try {
      final isConnected = await _networkService._testConnection(service.baseUrl);
      setState(() {
        _status = isConnected
            ? '✅ ${service.name} is accessible at ${service.baseUrl}'
            : '❌ ${service.name} is not accessible at ${service.baseUrl}';
      });
    } catch (e) {
      setState(() {
        _status = '❌ Connection test failed for ${service.name}: $e';
      });
    }
  }
}
