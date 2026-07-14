import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/vpn_service.dart';

/// Home screen — shows VPN connection status and connect/disconnect button.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.colorScheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('EyeNet VPN'),
        centerTitle: true,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings',
            onPressed: () => _showSettingsDialog(context),
          ),
        ],
      ),
      body: Consumer<VpnService>(
        builder: (context, vpn, _) {
          return Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // EyeNet logo
                  Image.asset(
                    'assets/images/eyenet-logo.png',
                    width: 120,
                    height: 120,
                  ),
                  const SizedBox(height: 32),

                  // Status text
                  Text(
                    vpn.isConnected ? 'Connected' : 'Disconnected',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: vpn.isConnected
                          ? Colors.green
                          : theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  const SizedBox(height: 8),

                  // VPN IP
                  if (vpn.vpnIp != null) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.green[50],
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.green[200]!),
                      ),
                      child: Text(
                        'VPN IP: ${vpn.vpnIp}',
                        style: TextStyle(
                          fontSize: 16,
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w600,
                          color: Colors.green[800],
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'All EyeNet apps can now use VPN mesh',
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                      ),
                    ),
                  ],

                  const SizedBox(height: 32),

                  // Connect/Disconnect button
                  SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton.icon(
                      onPressed: vpn.isConnecting
                          ? null
                          : () => vpn.isConnected ? vpn.disconnect() : vpn.connect(),
                      icon: vpn.isConnecting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : Icon(vpn.isConnected ? Icons.power_settings_new : Icons.vpn_lock),
                      label: Text(
                        vpn.isConnecting
                            ? 'Connecting...'
                            : vpn.isConnected
                                ? 'Disconnect'
                                : 'Connect to EyeNet VPN',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: vpn.isConnected
                            ? theme.colorScheme.error
                            : theme.colorScheme.primary,
                        foregroundColor: vpn.isConnected
                            ? theme.colorScheme.onError
                            : theme.colorScheme.onPrimary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Mesh Peers
                  if (vpn.isConnected) ...[
                    Row(
                      children: [
                        const Icon(Icons.hub, size: 18),
                        const SizedBox(width: 8),
                        Text(
                          'Mesh Peers',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: theme.colorScheme.onSurface,
                          ),
                        ),
                        const Spacer(),
                        TextButton.icon(
                          onPressed: () => vpn.fetchPeers(),
                          icon: const Icon(Icons.refresh, size: 16),
                          label: const Text('Refresh', style: TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    if (vpn.peers.isEmpty)
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.info_outline, size: 16, color: theme.colorScheme.onSurface.withValues(alpha: 0.5)),
                            const SizedBox(width: 8),
                            Text(
                              'Tap Refresh to load peers',
                              style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface.withValues(alpha: 0.5)),
                            ),
                          ],
                        ),
                      )
                    else
                      ...vpn.peers.map((peer) {
                        final ip = peer['tailscale_ip'] ?? '';
                        final name = peer['hostname'] ?? peer['node_id']?.toString() ?? 'Unknown';
                        final online = peer['online'] == true;
                        final nodeId = peer['node_id']?.toString() ?? '';
                        return Card(
                          child: ListTile(
                            leading: Icon(
                              online ? Icons.check_circle : Icons.cancel,
                              color: online ? Colors.green : Colors.red[300],
                              size: 24,
                            ),
                            title: Text(
                              '$name.eyenet-vpn.local',
                              style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                            ),
                            subtitle: Text('$ip'),
                            trailing: IconButton(
                              icon: const Icon(Icons.edit, size: 18),
                              onPressed: () => _showRenamePeerDialog(context, vpn, nodeId, name),
                            ),
                          ),
                        );
                      }),
                  ],

                  // Error message
                  if (vpn.error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red[50],
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red[200]!),
                      ),
                      child: Text(
                        vpn.error!,
                        style: TextStyle(color: Colors.red[700], fontSize: 13),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  /// Show settings dialog for configuring installation UUID and application key.
  void _showSettingsDialog(BuildContext context) {
    final vpn = context.read<VpnService>();

    final uuidController = TextEditingController(text: vpn.installationUuid);
    final keyController = TextEditingController(text: vpn.applicationKey);
    final urlController = TextEditingController(text: vpn.authorityUrl);
    final hostnameController = TextEditingController(text: vpn.hostname);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('VPN Settings'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: urlController,
                decoration: const InputDecoration(
                  labelText: 'Authority URL',
                  hintText: 'https://authority.eyenet-vision.com',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: uuidController,
                decoration: const InputDecoration(
                  labelText: 'Installation UUID',
                  hintText: 'From authority admin panel',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: keyController,
                decoration: const InputDecoration(
                  labelText: 'Application Key',
                  hintText: 'lic_...',
                  border: OutlineInputBorder(),
                ),
                obscureText: true,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: hostnameController,
                decoration: const InputDecoration(
                  labelText: 'Device Name',
                  hintText: 'eyenet-node-01',
                  border: OutlineInputBorder(),
                  helperText: 'Unique name for MagicDNS (disconnect first)',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              vpn.installationUuid = uuidController.text.trim();
              vpn.applicationKey = keyController.text.trim();
              vpn.authorityUrl = urlController.text.trim();
              vpn.hostname = hostnameController.text.trim();
              Navigator.pop(ctx);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showRenamePeerDialog(
    BuildContext context,
    VpnService vpn,
    String nodeId,
    String currentName,
  ) {
    final controller = TextEditingController(text: currentName);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Rename Device'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'New hostname',
                helperText: 'Alphanumeric + dashes',
                border: OutlineInputBorder(),
              ),
              autofocus: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              final newName = controller.text.trim();
              if (newName.isEmpty || newName == currentName) {
                Navigator.pop(ctx);
                return;
              }
              Navigator.pop(ctx);
              final success = await vpn.renamePeer(nodeId, newName);
              if (success && context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('$currentName → $newName.eyenet-vpn.local'),
                    backgroundColor: Colors.green,
                  ),
                );
                vpn.fetchPeers();
              } else if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Rename failed — check authority status'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            child: const Text('Rename'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    super.dispose();
  }
}
