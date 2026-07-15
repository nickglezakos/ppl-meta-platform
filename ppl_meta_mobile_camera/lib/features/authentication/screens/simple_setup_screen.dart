import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../../../services/simplified_discovery_client.dart';
import '../../../services/discovery_based_authentication_service.dart';
import '../../../core/providers/authentication_provider.dart';
import '../../../services/vpn_enrollment_service.dart';
import '../../../home_screen.dart';

class SimpleSetupScreen extends StatefulWidget {
  const SimpleSetupScreen({super.key});

  @override
  State<SimpleSetupScreen> createState() => _SimpleSetupScreenState();
}

class _SimpleSetupScreenState extends State<SimpleSetupScreen> {
  static const String _keySavedHostname = 'camera_node_hostname';

  final _hostnameController = TextEditingController(text: 'eyenet-node-hetzner');
  final _ipLastPartController = TextEditingController(text: '68');
  final _portController = TextEditingController(text: '8006');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  bool _isLoading = false;
  String? _errorMessage;
  String? _detectedNetwork;
  bool _isHowTosExpanded = false;
  bool _useMagicDns = true; // Primary: MagicDNS. Falls back to LAN on failure.

  @override
  void initState() {
    super.initState();
    _detectNetwork();
    _loadSavedHostname();
  }

  Future<void> _loadSavedHostname() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_keySavedHostname);
      if (saved != null && saved.isNotEmpty) {
        setState(() {
          _hostnameController.text = saved;
        });
      }
      // Also check VpnEnrollmentService for older saves
      final dns = await VpnEnrollmentService.getMagicDns();
      if (dns != null && dns.isNotEmpty) {
        final hostname = dns.replaceAll('.eyenet-vpn.local', '');
        if (hostname.isNotEmpty) {
          setState(() {
            _hostnameController.text = hostname;
          });
        }
      }
    } catch (e) {
      // Ignore — use default
    }
  }

  Future<void> _saveHostname(String hostname) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_keySavedHostname, hostname);
    } catch (e) {
      // Ignore
    }
  }

  Future<void> _detectNetwork() async {
    try {
      final discoveryClient = SimplifiedDiscoveryClient();
      final myIP = await discoveryClient.getMyIPAddress();
      if (myIP != null) {
        final parts = myIP.split('.');
        if (parts.length == 4) {
          setState(() {
            _detectedNetwork = '${parts[0]}.${parts[1]}.${parts[2]}.X';
          });
        }
      }
    } catch (e) {
      print('Network detection error: $e');
    }
  }

  /// Build the node URL from the MagicDNS hostname.
  String _buildNodeUrl() {
    final hostname = _hostnameController.text.trim();
    return 'http://$hostname.eyenet-vpn.local:8002';
  }

  /// Show info popup when MagicDNS connection fails.
  void _showVpnNotEnrolledDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('MagicDNS Connection Failed'),
        content: const Text(
          'Cannot reach the node via MagicDNS.\n\n'
          'Possible causes:\n'
          '• This device is not enrolled in the VPN mesh\n'
          '• The node\'s MagicDNS name has been changed\n'
          '• The node is offline or unreachable\n\n'
          'Check the MagicDNS name above and try again, '
          'or switch to LAN IP connection below.',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              setState(() => _useMagicDns = false);
            },
            child: const Text('Use LAN IP'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Future<void> _connectAndAuthenticate() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final username = _usernameController.text.trim();
      final password = _passwordController.text.trim();

      String targetHost;
      int targetPort;

      if (_useMagicDns) {
        // Primary: MagicDNS
        final hostname = _hostnameController.text.trim();
        targetHost = '$hostname.eyenet-vpn.local';
        targetPort = 8002;

        print('🔍 Attempting MagicDNS connection to $targetHost:$targetPort');

        // Try connecting via MagicDNS
        final discoveryClient = SimplifiedDiscoveryClient();
        final services = await discoveryClient.discoverServicesAtAddress('$targetHost:$targetPort');

        if (services.isEmpty) {
          // MagicDNS failed — show popup and switch to LAN
          if (mounted) {
            setState(() {
              _isLoading = false;
              _useMagicDns = false;
            });
            _showVpnNotEnrolledDialog();
          }
          return;
        }
      } else {
        // Fallback: LAN IP
        final ipLastPart = _ipLastPartController.text.trim();
        final port = _portController.text.trim();
        targetHost = await _buildTargetIP(ipLastPart);
        targetPort = int.tryParse(port) ?? 8006;
      }

      print('🔍 Connecting to Discovery Service at $targetHost:$targetPort');

      final discoveryClient = SimplifiedDiscoveryClient();
      final services = await discoveryClient.discoverServicesAtAddress('$targetHost:$targetPort');

      print('✅ Found ${services.length} services via Discovery Service');

      // Find node service for authentication
      final nodeService = services.firstWhere(
        (s) => s.name == 'ppl-meta-node',
        orElse: () => throw Exception('Node service not found in Discovery Service'),
      );

      print('🚪 Node service found at ${nodeService.host}:${nodeService.port}');

      // Authenticate directly with Node service
      await _authenticateWithNodeService(
        nodeService.host,
        nodeService.port,
        username,
        password,
      );

      print('🎉 Authentication successful!');

      // Save hostname for next launch
      if (_useMagicDns) {
        await _saveHostname(_hostnameController.text.trim());
      }

      // Update authentication provider with successful authentication
      if (mounted) {
        final authProvider = context.read<AuthenticationProvider>();

        final loginSuccess = await authProvider.login(
          serverUrl: 'http://${nodeService.host}:${nodeService.port}',
          username: username,
          password: password,
        );

        if (loginSuccess) {
          print('📱 Authentication provider updated successfully');
          // Try VPN enrollment in background (won't block login)
          _tryVpnEnrollment(nodeService.host, nodeService.port);
        } else {
          throw Exception('Failed to update authentication provider');
        }
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection failed: $e';
      });
      print('❌ Setup failed: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<String> _buildTargetIP(String lastPart) async {
    final discoveryClient = SimplifiedDiscoveryClient();
    final myIP = await discoveryClient.getMyIPAddress();

    if (myIP != null) {
      final parts = myIP.split('.');
      if (parts.length == 4) {
        return '${parts[0]}.${parts[1]}.${parts[2]}.$lastPart';
      }
    }

    // Fallback
    return '192.168.1.$lastPart';
  }

  /// Authenticate directly with Node service using form-urlencoded format
  Future<void> _authenticateWithNodeService(
    String nodeHost,
    int nodePort,
    String username,
    String password,
  ) async {
    final nodeUrl = 'http://$nodeHost:$nodePort';

    print('🔐 Authenticating with Node service at $nodeUrl');

    try {
      final response = await http.post(
        Uri.parse('$nodeUrl/api/v1/users/login'),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: 'username=$username&password=$password',
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        print('✅ Node service authentication successful');
        print('🔑 Token received: ${responseData['access_token']?.substring(0, 20)}...');
      } else {
        final errorData = json.decode(response.body);
        final errorMessage = errorData['detail'] ?? 'Authentication failed';
        throw Exception('Node service authentication failed: $errorMessage');
      }
    } catch (e) {
      print('❌ Node service authentication error: $e');
      throw Exception('Failed to authenticate with Node service: $e');
    }
  }

  /// Try to fetch a VPN enrollment key from the node in background.
  /// Does NOT block the login flow — failure is silent.
  Future<void> _tryVpnEnrollment(String nodeHost, int nodePort) async {
    try {
      final result = await VpnEnrollmentService.fetchKeyFromNode(
        nodeIp: nodeHost,
        nodePort: nodePort,
      );
      if (result != null) {
        final authKey = result['auth_key'] as String?;
        final headscaleServer = result['headscale_server'] as String?;
        if (authKey != null && headscaleServer != null) {
          await VpnEnrollmentService.saveEnrollment(
            authKey: authKey,
            headscaleServer: headscaleServer,
          );
          // Save MagicDNS discovery URL for future VPN-based connections
          final discoveryUrl = result['discovery_url'] as String?;
          if (discoveryUrl != null) {
            await VpnEnrollmentService.saveDiscoveryUrl(discoveryUrl);
          }
          final magicDns = result['magic_dns'] as String?;
          if (magicDns != null) {
            await VpnEnrollmentService.saveMagicDns(magicDns);
          }
          print('🔒 VPN enrollment key stored');
          print('   Discovery URL: $discoveryUrl');
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: const Text('✅ VPN Mesh enrollment ready — install Tailscale to connect'),
                backgroundColor: Colors.green,
                action: SnackBarAction(
                  label: 'OK',
                  textColor: Colors.white,
                  onPressed: () {},
                ),
                duration: const Duration(seconds: 6),
              ),
            );
          }
        }
      }
    } catch (e) {
      print('⚠️ VPN enrollment skipped: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 32,
              height: 32,
              margin: const EdgeInsets.only(right: 8),
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
              ),
              child: ClipOval(
                child: Image.asset(
                  'assets/logo.png',
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Icon(
                      Icons.camera_alt_rounded,
                      size: 20,
                      color: Theme.of(context).colorScheme.primary,
                    );
                  },
                ),
              ),
            ),
            const Text('Eyenet Vision'),
          ],
        ),
        centerTitle: true,
        automaticallyImplyLeading: false,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),

              // Network Info
              if (_detectedNetwork != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.blue.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Network Detected:',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        _detectedNetwork!,
                        style: TextStyle(
                          color: Colors.blue.shade700,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 24),

              // Platform Connection
              const Text(
                'Platform Connection',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),

              // MagicDNS Primary
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _useMagicDns
                      ? Colors.green.shade50
                      : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: _useMagicDns ? Colors.green.shade200 : Colors.grey.shade300,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _useMagicDns ? Icons.vpn_lock : Icons.vpn_lock_outlined,
                          size: 18,
                          color: _useMagicDns ? Colors.green.shade700 : Colors.grey,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'MagicDNS (Recommended)',
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: _useMagicDns ? Colors.green.shade700 : Colors.grey,
                          ),
                        ),
                        const Spacer(),
                        if (!_useMagicDns)
                          TextButton(
                            onPressed: () => setState(() => _useMagicDns = true),
                            child: const Text('Switch', style: TextStyle(fontSize: 12)),
                          ),
                      ],
                    ),
                    if (_useMagicDns) ...[
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _hostnameController,
                        decoration: InputDecoration(
                          labelText: 'Node MagicDNS Name',
                          hintText: 'eyenet-node-hetzner',
                          border: const OutlineInputBorder(),
                          prefixIcon: const Icon(Icons.dns),
                          suffix: const Text('.eyenet-vpn.local:8002',
                            style: TextStyle(fontFamily: 'monospace', fontSize: 11, color: Colors.grey),
                          ),
                        ),
                        validator: (value) {
                          if (_useMagicDns && (value == null || value.isEmpty)) {
                            return 'Please enter a MagicDNS hostname';
                          }
                          return null;
                        },
                      ),
                    ] else ...[
                      const SizedBox(height: 8),
                      const Text(
                        'Using LAN IP fallback',
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 12),

              // LAN Fallback
              if (!_useMagicDns)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.lan, size: 18, color: Colors.orange),
                          SizedBox(width: 8),
                          Text('LAN Connection', style: TextStyle(fontWeight: FontWeight.w600, color: Colors.orange)),
                        ],
                      ),
                      const SizedBox(height: 12),
                      // IP Last Part Input
                      TextFormField(
                        controller: _ipLastPartController,
                        decoration: const InputDecoration(
                          labelText: 'Platform IP Last Part',
                          hintText: 'e.g., 68 for 192.168.1.68',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.computer),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (!_useMagicDns) {
                            if (value == null || value.isEmpty) {
                              return 'Please enter the IP last part';
                            }
                            final num = int.tryParse(value);
                            if (num == null || num < 1 || num > 254) {
                              return 'Enter a valid IP part (1-254)';
                            }
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      // Port Input
                      TextFormField(
                        controller: _portController,
                        decoration: const InputDecoration(
                          labelText: 'Discovery Service Port',
                          hintText: 'e.g., 8006',
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.settings_input_antenna),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (!_useMagicDns) {
                            if (value == null || value.isEmpty) {
                              return 'Please enter the port';
                            }
                            final num = int.tryParse(value);
                            if (num == null || num < 1 || num > 65535) {
                              return 'Enter a valid port (1-65535)';
                            }
                          }
                          return null;
                        },
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 24),

              // User Credentials
              const Text(
                'User Credentials',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),

              // Username Input
              TextFormField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  labelText: 'Username',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your username';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Password Input
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),
                obscureText: true,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
              ),

              const SizedBox(height: 24),

              // Connect Button
              ElevatedButton(
                onPressed: _isLoading ? null : _connectAndAuthenticate,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator()
                    : const Text(
                        'Connect to Platform',
                        style: TextStyle(fontSize: 16),
                      ),
              ),

              // Error Message
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade700),
                  ),
                ),
              ],

              const SizedBox(height: 32),

              // How Tos Expandable Section at bottom
              _buildHowTosSection(),

              const SizedBox(height: 16),

              // Version Info
              Center(
                child: Text(
                  'Eyenet Vision v1.0.0',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHowTosSection() {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          // How Tos Header (clickable)
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                setState(() {
                  _isHowTosExpanded = !_isHowTosExpanded;
                });
              },
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.help_outline,
                          size: 20,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'How Tos',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: Theme.of(context).colorScheme.onSurface,
                          ),
                        ),
                      ],
                    ),
                    Icon(
                      _isHowTosExpanded ? Icons.expand_less : Icons.expand_more,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Expandable Content
          AnimatedSize(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            child: _isHowTosExpanded
                ? Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.3),
                      borderRadius: const BorderRadius.only(
                        bottomLeft: Radius.circular(12),
                        bottomRight: Radius.circular(12),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHowToItem(
                          icon: Icons.network_check,
                          title: 'Connecting to Your Platform',
                          steps: [
                            'Primary: Enter the MagicDNS hostname (e.g. eyenet-node-hetzner)',
                            'Fallback: If MagicDNS fails, use the LAN IP address',
                            'MagicDNS requires the device to be enrolled in the EyeNet VPN mesh',
                            'The hostname is saved and auto-filled on your next visit',
                          ],
                        ),
                        const SizedBox(height: 16),
                        _buildHowToItem(
                          icon: Icons.login,
                          title: 'Login Credentials',
                          steps: [
                            'Use your existing platform account credentials',
                            'If you don\'t have an account, contact your administrator',
                            'Default test credentials: fresh.user@example.com',
                          ],
                        ),
                        const SizedBox(height: 16),
                        _buildHowToItem(
                          icon: Icons.camera_alt,
                          title: 'After Login',
                          steps: [
                            'You\'ll be prompted to register this device as a camera',
                            'Choose a unique name for your mobile camera',
                            'Grant camera and storage permissions when requested',
                            'Your device will appear in the platform\'s camera list',
                          ],
                        ),
                        const SizedBox(height: 16),
                        _buildHowToItem(
                          icon: Icons.error_outline,
                          title: 'Troubleshooting',
                          steps: [
                            'MagicDNS: Ensure this device is enrolled in the VPN mesh',
                            'LAN: Ensure your device is on the same network as the platform',
                            'Verify the platform is running (check console logs)',
                            'Try different IP addresses if connection fails',
                            'Contact your system administrator for assistance',
                          ],
                        ),
                      ],
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  Widget _buildHowToItem({
    required IconData icon,
    required String title,
    required List<String> steps,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 18,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 8),
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...steps.map((step) => Padding(
              padding: const EdgeInsets.only(left: 26, bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '• ',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      step,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  @override
  void dispose() {
    _hostnameController.dispose();
    _ipLastPartController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}