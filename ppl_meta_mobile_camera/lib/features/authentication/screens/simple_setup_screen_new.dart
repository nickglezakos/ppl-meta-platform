import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../services/simplified_discovery_client.dart';
import '../../../services/discovery_based_authentication_service.dart';
import '../../../services/discovery_config_service.dart';
import '../../../services/platform_config_service.dart';
import '../../../services/authority_api_client.dart';
import '../../../services/tailscale_service.dart';
import '../../../core/providers/authentication_provider.dart';
import '../../../core/services/authentication_service.dart';

class SimpleSetupScreen extends StatefulWidget {
  const SimpleSetupScreen({super.key});

  @override
  State<SimpleSetupScreen> createState() => _SimpleSetupScreenState();
}

class _SimpleSetupScreenState extends State<SimpleSetupScreen> {
  // Storage keys for persistent credentials
  static const String _backendIPKey = 'saved_backend_ip';
  static const String _portKey = 'saved_port';
  static const String _usernameKey = 'saved_username';
  static const String _passwordKey = 'saved_password';
  
  final _backendIPController = TextEditingController(text: '');
  final _portController = TextEditingController(text: '8006');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
final _enrollmentTokenController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  
  bool _isLoading = false;
  bool _isAttemptingAutoLogin = true;
  String? _errorMessage;
bool _isEnrolling = false;
  String? _enrollmentMessage;
  bool _isHowTosExpanded = false;
  bool _hasStoredCredentials = false;
  bool _isPasswordVisible = false;

  @override
  void initState() {
    super.initState();
    _attemptAutoLogin();
  }

  /// Attempt automatic login with stored credentials
  Future<void> _attemptAutoLogin() async {
    try {
      final authService = AuthenticationService.instance;
      
      // Check if we have a valid token already
      if (authService.isAuthenticated && authService.authToken != null) {
        print('🔐 Existing authentication found, validating token...');
        
        // Validate the existing token
        final isValid = await authService.validateToken();
        if (isValid) {
          print('✅ Existing token is valid, auto-login successful');
          // Update provider state
          if (mounted) {
            final authProvider = Provider.of<AuthenticationProvider>(context, listen: false);
            authProvider.notifyListeners();
          }
          return;
        } else {
          print('⚠️ Existing token is invalid, clearing credentials');
          await authService.clearCredentials();
        }
      }
      
      // Load saved credentials
      final prefs = await SharedPreferences.getInstance();
      final savedBackendIP = prefs.getString(_backendIPKey);
      final savedPort = prefs.getString(_portKey);
      final savedUsername = prefs.getString(_usernameKey);
      final savedPassword = prefs.getString(_passwordKey);
      
      if (savedBackendIP != null && savedUsername != null && savedPassword != null) {
        print('🔑 Found stored credentials, attempting auto-login...');
        setState(() {
          _hasStoredCredentials = true;
          _isLoading = true;
        });
        
        // Set controllers with saved values
        _backendIPController.text = savedBackendIP;
        _portController.text = savedPort ?? '8006';
        _usernameController.text = savedUsername;
        _passwordController.text = savedPassword;
        
        // Attempt automatic connection and authentication
        await _connectAndAuthenticate(isAutoLogin: true);
      } else {
        print('📝 No stored credentials found, showing login form');
        setState(() {
          _hasStoredCredentials = false;
        });
      }
    } catch (e) {
      print('❌ Auto-login error: $e');
      setState(() {
        _errorMessage = 'Auto-login failed. Please login manually.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isAttemptingAutoLogin = false;
        });
      }
    }
  }

  /// Save credentials to persistent storage
  Future<void> _saveCredentials() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_backendIPKey, _backendIPController.text.trim());
      await prefs.setString(_portKey, _portController.text.trim());
      await prefs.setString(_usernameKey, _usernameController.text.trim());
      await prefs.setString(_passwordKey, _passwordController.text.trim());
      print('✅ Credentials saved to persistent storage');
    } catch (e) {
      print('❌ Failed to save credentials: $e');
    }
  }

  /// Clear stored credentials
  Future<void> _clearStoredCredentials() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_backendIPKey);
      await prefs.remove(_portKey);
      await prefs.remove(_usernameKey);
      await prefs.remove(_passwordKey);
      print('🗑️ Stored credentials cleared');
    } catch (e) {
      print('❌ Failed to clear credentials: $e');
    }
  }

  Future<void> _connectAndAuthenticate({bool isAutoLogin = false}) async {
    if (!isAutoLogin && !_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // === VPN-mesh aware path (preferred after token redemption) ===
      final platformConfig = await PlatformConfigService.getInstance();

      String host;
      String portStr;

      if (platformConfig.vpnEnrolled ||
          (platformConfig.vpnPlatformTailscaleIp != null &&
              platformConfig.vpnPlatformTailscaleIp!.isNotEmpty)) {
        // Use the platform host resolved from the enrollment token
        // (LAN first, mesh when remote). This prevents timeout on 100.64.x.x
        host = platformConfig.platformHost;
        portStr = '${PlatformConfigService.discoveryPort}';
        print('🔐 Using VPN-mesh resolved host: $host');
      } else {
        // === Legacy manual LAN path ===
        host = _backendIPController.text.trim();
        portStr = _portController.text.trim();

        await DiscoveryConfigService.instance.configureFromUserInput(
          ipLastPart: host.split('.').last,
          port: portStr,
          deviceIPPrefix: host.split('.').take(3).join('.'),
        );
      }

      print('🔍 Attempting to connect to Discovery Service at $host:$portStr');

      final discoveryClient = SimplifiedDiscoveryClient();
      final services =
          await discoveryClient.discoverServicesAtAddress('$host:$portStr');

      final nodeService = services.firstWhere(
        (s) => s.name == 'ppl-meta-node',
        orElse: () => throw Exception('Node service not found in Discovery Service'),
      );

      final nodeUrl = 'http://${nodeService.host}:${nodeService.port}';

      final authProvider =
          Provider.of<AuthenticationProvider>(context, listen: false);
      final loginSuccess = await authProvider.login(
        serverUrl: nodeUrl,
        username: _usernameController.text.trim(),
        password: _passwordController.text.trim(),
      );

      if (loginSuccess) {
        print('🎉 Authentication successful! App state updated.');
        await _saveCredentials();
      } else {
        throw Exception(authProvider.error ?? 'Authentication failed');
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection failed: $e';
      });
      print('❌ Setup failed: $e');

      if (isAutoLogin) {
        await _clearStoredCredentials();
        print('🗑️ Cleared invalid stored credentials');
      }
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }
/// Join the VPN mesh by redeeming a one-time enrollment token minted by a
  /// platform admin. One internet round-trip returns the assigned platform
  /// (mesh IP, LAN IP, hostname), which the camera then uses to discover and
  /// connect to the platform — no LAN IP typing required.
  Future<void> _redeemVpnEnrollmentToken() async {
    final token = _enrollmentTokenController.text.trim();
    if (token.isEmpty) {
      setState(() => _enrollmentMessage = 'Enter the enrollment token from the platform.');
      return;
    }

    setState(() {
      _isEnrolling = true;
      _enrollmentMessage = null;
    });

    try {
      // 1. Redeem the token against the Authority.
      final config = await PlatformConfigService.getInstance();
      final client = AuthorityApiClient(baseUrl: config.authorityServiceUrl);
      final enrollment = await client.redeemEnrollmentToken(token: token, nodeType: 'mobile');

      // 2. Persist the full VPN metadata (platform LAN + mesh IPs, auth key,
      //    headscale server, api_token, installation uuid).
      await config.saveVpnMetadata(
        authKey: enrollment.authKey,
        headscaleServer: enrollment.headscaleServer,
        matrixGroupId: enrollment.matrixGroupId,
        primaryNodeIp: enrollment.primaryNodeIp,
        apiToken: enrollment.apiToken,
        platformTailscaleIp: enrollment.platformTailscaleIp,
        platformHostname: enrollment.platformHostname,
        platformLocalIp: enrollment.platformLocalIp,
      );

      // 3. Bring up the camera's own mesh node, then resolve the platform.
      final tailscale = TailscaleService(config: config);
      await tailscale.initialize();
      await config.ensurePlatformReachable();

      // 4. Discovery now resolves to the enrolled platform host (LAN or mesh).
      final platformHost = config.platformHost;

      setState(() {
        _enrollmentMessage =
            'Joined VPN mesh. Connected to platform at $platformHost. You can now '
            'sign in below (or re-open the app to skip setup).';
        _backendIPController.text = platformHost;
        _portController.text = '${PlatformConfigService.discoveryPort}';
      });
    } catch (e) {
      setState(() => _enrollmentMessage = 'Enrollment failed: $e');
    } finally {
      setState(() => _isEnrolling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Show loading screen during auto-login attempt
    if (_isAttemptingAutoLogin) {
      return Scaffold(
        appBar: AppBar(
          centerTitle: true,
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(
                'Checking saved credentials...',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
            ],
          ),
        ),
      );
    }
    
    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        actions: [
          // Add logout button if credentials are stored
          if (_hasStoredCredentials)
            IconButton(
              icon: const Icon(Icons.logout),
              tooltip: 'Clear saved credentials',
              onPressed: () async {
                await _clearStoredCredentials();
                await AuthenticationService.instance.clearCredentials();
                setState(() {
                  _hasStoredCredentials = false;
                  _backendIPController.clear();
                  _usernameController.clear();
                  _passwordController.clear();
                });
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Credentials cleared. Please login again.')),
                  );
                }
              },
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              
              // Logo
              Center(
                child: Image.asset(
                  'assets/images/eyenet-logo.png',
                  height: 120,
                  errorBuilder: (context, error, stackTrace) {
                    return const Icon(Icons.visibility, size: 120);
                  },
                ),
              ),
              
              const SizedBox(height: 12),
              
              // App subtitle
              Center(
                child: Text(
                  'Mobile Camera App',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              ),
              
              const SizedBox(height: 32),
              
              // Platform Connection
              const Text(
                'Platform Connection',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              
              // Complete Backend IP Input
              TextFormField(
                controller: _backendIPController,
                decoration: const InputDecoration(
                  labelText: 'Backend IP Address',
                  hintText: 'e.g., 10.109.198.107 (complete IP from frontend settings)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.computer),
                ),
                keyboardType: TextInputType.text,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter the complete backend IP address';
                  }
                  // Basic IP validation
                  final parts = value.split('.');
                  if (parts.length != 4) {
                    return 'Enter a valid IP address (e.g., 10.109.198.107)';
                  }
                  for (final part in parts) {
                    final num = int.tryParse(part);
                    if (num == null || num < 0 || num > 255) {
                      return 'Enter a valid IP address';
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
                  if (value == null || value.isEmpty) {
                    return 'Please enter the port';
                  }
                  final num = int.tryParse(value);
                  if (num == null || num < 1 || num > 65535) {
                    return 'Enter a valid port (1-65535)';
                  }
                  return null;
                },
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
                decoration: InputDecoration(
                  labelText: 'Password',
                  border: const OutlineInputBorder(),
                  prefixIcon: const Icon(Icons.lock),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _isPasswordVisible ? Icons.visibility_off : Icons.visibility,
                    ),
                    onPressed: () {
                      setState(() {
                        _isPasswordVisible = !_isPasswordVisible;
                      });
                    },
                  ),
                ),
                obscureText: !_isPasswordVisible,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter your password';
                  }
                  return null;
                },
              ),
              
const SizedBox(height: 24),

              // Join VPN Mesh (enrollment token) — optional but recommended for
              // remote access. Redeems a one-time token to discover the platform
              // via the VPN mesh (no LAN IP typing required).
              const Divider(),
              const SizedBox(height: 12),
              Row(
                children: const [
                  Icon(Icons.vpn_lock, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'Join the VPN mesh (enrollment token)',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'Paste the one-time token from the platform. The camera will '
                'discover the platform over the mesh and enable remote access.',
                style: TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _enrollmentTokenController,
                decoration: const InputDecoration(
                  labelText: 'One-time enrollment token (optional)',
                  hintText: 'Paste token from the platform admin screen',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.key),
                ),
              ),
              const SizedBox(height: 12),
              if (_enrollmentMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.green.shade200),
                  ),
                  child: Text(
                    _enrollmentMessage!,
                    style: TextStyle(color: Colors.green.shade800),
                  ),
                ),
                const SizedBox(height: 12),
              ],
              ElevatedButton.icon(
                onPressed: _isEnrolling ? null : _redeemVpnEnrollmentToken,
                icon: _isEnrolling
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.link),
                label: Text(_isEnrolling ? 'Joining…' : 'Join VPN Mesh'),
              ),

              const SizedBox(height: 24),

              // Direct LAN connection (legacy) — collapsed by default
              ExpansionTile(
                title: const Text('Direct LAN connection (legacy)'),
                subtitle: const Text('Only use if you cannot obtain an enrollment token'),
                leading: const Icon(Icons.settings_ethernet),
                initiallyExpanded: false,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0),
                    child: Column(
                      children: [
                        TextFormField(
                          controller: _backendIPController,
                          decoration: const InputDecoration(
                            labelText: 'Backend IP Address',
                            hintText: 'e.g., 192.168.1.100',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.computer),
                          ),
                          keyboardType: TextInputType.text,
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _portController,
                          decoration: const InputDecoration(
                            labelText: 'Discovery Service Port',
                            hintText: '8006',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.settings_input_antenna),
                          ),
                          keyboardType: TextInputType.number,
                        ),
                        const SizedBox(height: 16),
                      ],
                    ),
                  ),
                ],
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _errorMessage!,
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                      const SizedBox(height: 8),
                      ElevatedButton.icon(
                        onPressed: () {
                          setState(() {
                            _errorMessage = null;
                          });
                        },
                        icon: const Icon(Icons.refresh),
                        label: const Text('Try Again'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.orange,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              
              const SizedBox(height: 24),
              
              // How Tos Dropdown
              _buildHowTosSection(),
              
              const SizedBox(height: 16),
              
              // Version Info
              Center(
                child: Text(
                  'Eyenet Vision v1.0.0',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                    fontSize: 12,
                  ),
                ),
              ),
              
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildHowTosSection() {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          // Dropdown Header
          InkWell(
            onTap: () {
              setState(() {
                _isHowTosExpanded = !_isHowTosExpanded;
              });
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    Icons.help_outline,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'How Tos',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    _isHowTosExpanded ? Icons.expand_less : Icons.expand_more,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
            ),
          ),
          
          // Expandable Content
          AnimatedSize(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            child: _isHowTosExpanded
                ? Container(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Divider(
                          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
                        ),
                        const SizedBox(height: 12),
                        
                        // Setup Instructions
                        _buildHowToSection(
                          'Setup Instructions',
                          [
                            '1. Open the web frontend at http://localhost:3000/#/settings',
                            '2. Check the IP address of the Eyenet Vision Platform services',
                            '3. Enter the complete backend IP address below',
                          ],
                        ),
                        
                        const SizedBox(height: 16),
                        
                        // Server Connection
                        _buildHowToSection(
                          'Server Connection',
                          [
                            '• Check the IP address shown for backend services in settings',
                            '• Enter the complete IP address in the "Backend IP Address" field',
                            '• Default port is 8006 (Discovery Service)',
                          ],
                        ),
                        
                        const SizedBox(height: 16),
                        
                        // Login Credentials
                        _buildHowToSection(
                          'Login Credentials',
                          [
                            '• Username and password are required to authenticate',
                            '• Use the same credentials as the web frontend',
                            '• Contact your administrator if you need access',
                          ],
                        ),
                        
                        const SizedBox(height: 16),
                        
                        // Camera Registration
                        _buildHowToSection(
                          'Camera Registration',
                          [
                            '• After successful login, you\'ll be prompted to register the camera',
                            '• Choose a descriptive camera name',
                            '• The camera will appear in the web frontend',
                          ],
                        ),
                        
                        const SizedBox(height: 16),
                        
                        // Troubleshooting
                        _buildHowToSection(
                          'Troubleshooting',
                          [
                            '• Ensure the backend services are running',
                            '• Check that your device is on the same network',
                            '• Verify the IP address and port are correct',
                            '• Check firewall settings if connection fails',
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
  
  Widget _buildHowToSection(String title, List<String> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 14,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
        const SizedBox(height: 8),
        ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                item,
                style: TextStyle(
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  height: 1.4,
                ),
              ),
            )),
      ],
    );
  }

  @override
  void dispose() {
    _backendIPController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _enrollmentTokenController.dispose();
    super.dispose();
  }
}
