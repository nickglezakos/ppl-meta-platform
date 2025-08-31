import 'package:flutter/material.dart';
import '../services/ppl_meta_discovery_client.dart';
import '../services/unified_discovery_service.dart';

/// Service discovery status widget for mobile camera app
class ServiceDiscoveryStatusWidget extends StatefulWidget {
  const ServiceDiscoveryStatusWidget({super.key});

  @override
  State<ServiceDiscoveryStatusWidget> createState() => _ServiceDiscoveryStatusWidgetState();
}

class _ServiceDiscoveryStatusWidgetState extends State<ServiceDiscoveryStatusWidget> {
  final UnifiedDiscoveryService _discoveryService = UnifiedDiscoveryService();
  List<DiscoveredServiceInfo> _services = [];
  bool _isDiscovering = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _startDiscovery();
  }

  @override
  void dispose() {
    _discoveryService.dispose();
    super.dispose();
  }

  Future<void> _startDiscovery() async {
    if (_isDiscovering) return;

    setState(() {
      _isDiscovering = true;
      _error = null;
    });

    try {
      final services = await _discoveryService.discoverAllServices();
      if (mounted) {
        setState(() {
          _services = services;
          _isDiscovering = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isDiscovering = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.hub, color: Colors.blue),
                    SizedBox(width: 8),
                    Text(
                      'Service Discovery',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                IconButton(
                  icon: _isDiscovering 
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh),
                  onPressed: _isDiscovering ? null : _startDiscovery,
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  border: Border.all(color: Colors.red.shade200),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error, color: Colors.red.shade700),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Discovery Error: $_error',
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (_isDiscovering) ...[
              const Row(
                children: [
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 12),
                  Text('Discovering services...'),
                ],
              ),
            ] else if (_services.isEmpty) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  border: Border.all(color: Colors.orange.shade200),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning, color: Colors.orange.shade700),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text('No services discovered'),
                    ),
                  ],
                ),
              ),
            ] else ...[
              Text(
                'Found ${_services.length} services',
                style: TextStyle(
                  color: Colors.green.shade700,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 12),
              ..._services.map((service) => _buildServiceTile(service)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildServiceTile(DiscoveredServiceInfo service) {
    IconData icon;
    Color iconColor;
    
    switch (service.status) {
      case 'healthy':
        icon = Icons.check_circle;
        iconColor = Colors.green;
        break;
      case 'unhealthy':
        icon = Icons.error;
        iconColor = Colors.red;
        break;
      default:
        icon = Icons.help;
        iconColor = Colors.orange;
    }

    Color methodColor;
    IconData methodIcon;
    
    switch (service.discoveryMethod) {
      case 'central_discovery':
        methodColor = Colors.blue;
        methodIcon = Icons.cloud;
        break;
      case 'multicast':
        methodColor = Colors.green;
        methodIcon = Icons.wifi;
        break;
      case 'local_scan':
        methodColor = Colors.orange;
        methodIcon = Icons.network_ping;
        break;
      default:
        methodColor = Colors.grey;
        methodIcon = Icons.help;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: iconColor, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  service.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: methodColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: methodColor.withOpacity(0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(methodIcon, size: 12, color: methodColor),
                    const SizedBox(width: 4),
                    Text(
                      _getMethodDisplayName(service.discoveryMethod),
                      style: TextStyle(
                        fontSize: 10,
                        color: methodColor,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${service.host}:${service.port}',
            style: TextStyle(
              color: Colors.grey.shade600,
              fontSize: 12,
            ),
          ),
          if (service.capabilities.isNotEmpty) ...[
            const SizedBox(height: 4),
            Wrap(
              spacing: 4,
              children: service.capabilities.take(3).map((capability) =>
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  child: Text(
                    capability,
                    style: TextStyle(
                      fontSize: 10,
                      color: Colors.blue.shade700,
                    ),
                  ),
                ),
              ).toList(),
            ),
          ],
        ],
      ),
    );
  }

  String _getMethodDisplayName(String method) {
    switch (method) {
      case 'central_discovery':
        return 'Central';
      case 'multicast':
        return 'Multicast';
      case 'local_scan':
        return 'Scan';
      default:
        return method;
    }
  }
}

/// Compact service discovery indicator for app bars
class ServiceDiscoveryIndicator extends StatefulWidget {
  const ServiceDiscoveryIndicator({super.key});

  @override
  State<ServiceDiscoveryIndicator> createState() => _ServiceDiscoveryIndicatorState();
}

class _ServiceDiscoveryIndicatorState extends State<ServiceDiscoveryIndicator> {
  final UnifiedDiscoveryService _discoveryService = UnifiedDiscoveryService();
  int _serviceCount = 0;
  bool _isDiscovering = false;

  @override
  void initState() {
    super.initState();
    _checkServices();
  }

  @override
  void dispose() {
    _discoveryService.dispose();
    super.dispose();
  }

  Future<void> _checkServices() async {
    setState(() => _isDiscovering = true);
    
    try {
      final services = await _discoveryService.discoverAllServices();
      if (mounted) {
        setState(() {
          _serviceCount = services.length;
          _isDiscovering = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _serviceCount = 0;
          _isDiscovering = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isDiscovering) {
      return const SizedBox(
        width: 16,
        height: 16,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }

    return InkWell(
      onTap: () => _showServiceDialog(context),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: _serviceCount > 0 ? Colors.green.shade100 : Colors.orange.shade100,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _serviceCount > 0 ? Colors.green.shade300 : Colors.orange.shade300,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _serviceCount > 0 ? Icons.hub : Icons.warning,
              size: 14,
              color: _serviceCount > 0 ? Colors.green.shade700 : Colors.orange.shade700,
            ),
            const SizedBox(width: 4),
            Text(
              '$_serviceCount',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: _serviceCount > 0 ? Colors.green.shade700 : Colors.orange.shade700,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showServiceDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 400, maxHeight: 500),
          child: const ServiceDiscoveryStatusWidget(),
        ),
      ),
    );
  }
}
