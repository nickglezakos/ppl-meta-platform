import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/providers/authentication_provider.dart';

class LoginForm extends StatefulWidget {
  final VoidCallback onLoginSuccess;
  final String? prefilledServerUrl;

  const LoginForm({
    super.key,
    required this.onLoginSuccess,
    this.prefilledServerUrl,
  });

  @override
  State<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends State<LoginForm> {
  final _formKey = GlobalKey<FormState>();
  final _serverUrlController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  
  bool _isPasswordVisible = false;

  @override
  void initState() {
    super.initState();
    // If a server URL was discovered via automatic setup, prefill it
    if (widget.prefilledServerUrl != null) {
      _serverUrlController.text = widget.prefilledServerUrl!;
    }
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final authProvider = context.read<AuthenticationProvider>();
    
    // Determine the server URL (from prefilled or manual input)
    final serverUrl = widget.prefilledServerUrl ?? _serverUrlController.text.trim();
    
    if (serverUrl.isEmpty) {
      _showErrorSnackBar('No service URL available - please provide server URL');
      return;
    }

    // Check if this is automatic setup mode (has camera name)
    final isAutomaticMode = widget.prefilledServerUrl != null;
    
    if (isAutomaticMode) {
      // Automatic setup mode - use enhanced authentication
      await _handleAutomaticLogin();
    } else {
      // Manual mode - use existing authentication
      await _handleManualLogin(serverUrl, authProvider);
    }
  }

  Future<void> _handleManualLogin(String serverUrl, AuthenticationProvider authProvider) async {
    final success = await authProvider.login(
      serverUrl: serverUrl,
      username: _usernameController.text.trim(),
      password: _passwordController.text,
    );

    if (success) {
      _showSuccessSnackBar('Login successful!');
      widget.onLoginSuccess();
    } else {
      final error = authProvider.error ?? 'Login failed';
      _showErrorSnackBar(error);
    }
  }

  Future<void> _handleAutomaticLogin() async {
    try {
      // Step 1: Authenticate normally using the existing provider
      final authProvider = context.read<AuthenticationProvider>();
      final success = await authProvider.login(
        serverUrl: widget.prefilledServerUrl!,
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );

      if (!success) {
        throw Exception(authProvider.error ?? 'Authentication failed');
      }

      print('✅ Authentication successful');
      _showSuccessSnackBar('Login successful! Please register your camera.');

      // Navigate to home/camera registration
      widget.onLoginSuccess();

    } catch (e) {
      print('❌ Login failed: $e');
      _showErrorSnackBar('Login failed: ${e.toString()}');
    }
  }

  void _showSuccessSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.white),
              const SizedBox(width: 8),
              Expanded(child: Text(message)),
            ],
          ),
          backgroundColor: Colors.green,
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  void _showErrorSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.error, color: Colors.white),
              const SizedBox(width: 8),
              Expanded(child: Text(message)),
            ],
          ),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthenticationProvider>(
      builder: (context, authProvider, child) {
        return Container(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),
                
                // Server URL Field or Success Indicator
                if (widget.prefilledServerUrl != null) ...[
                  // Show success indicator for automatic setup
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.green.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Server Auto-Discovered',
                                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                  color: Colors.green[700],
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              Text(
                                widget.prefilledServerUrl!,
                                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Colors.green[600],
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ] else ...[
                  // Show manual server URL input
                  TextFormField(
                    controller: _serverUrlController,
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      labelText: 'Server URL',
                      hintText: 'http://localhost:8001 or https://your-server.com',
                      prefixIcon: const Icon(Icons.cloud),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      filled: true,
                      fillColor: Theme.of(context).colorScheme.surfaceContainer.withOpacity(0.3),
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Server URL is required';
                      }
                      final uri = Uri.tryParse(value.trim());
                      if (uri == null || (!uri.hasScheme || !uri.hasAuthority)) {
                        return 'Please enter a valid URL';
                      }
                      return null;
                    },
                  ),
                ],
                
                const SizedBox(height: 20),
                
                // Username Field
                TextFormField(
                  controller: _usernameController,
                  keyboardType: TextInputType.text,
                  textInputAction: TextInputAction.next,
                  decoration: InputDecoration(
                    labelText: 'Username',
                    hintText: 'Enter your username',
                    prefixIcon: const Icon(Icons.person),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: Theme.of(context).colorScheme.surfaceContainer.withOpacity(0.3),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Username is required';
                    }
                    return null;
                  },
                ),
                
                const SizedBox(height: 20),
                
                // Password Field
                TextFormField(
                  controller: _passwordController,
                  obscureText: !_isPasswordVisible,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _handleLogin(),
                  decoration: InputDecoration(
                    labelText: 'Password',
                    hintText: 'Enter your password',
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _isPasswordVisible ? Icons.visibility : Icons.visibility_off,
                      ),
                      onPressed: () {
                        setState(() {
                          _isPasswordVisible = !_isPasswordVisible;
                        });
                      },
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    filled: true,
                    fillColor: Theme.of(context).colorScheme.surfaceContainer.withOpacity(0.3),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Password is required';
                    }
                    return null;
                  },
                ),
                
                const SizedBox(height: 32),
                
                // Login Button
                ElevatedButton(
                  onPressed: authProvider.isLoading ? null : _handleLogin,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    foregroundColor: Theme.of(context).colorScheme.onPrimary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: authProvider.isLoading
                      ? const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            ),
                            SizedBox(width: 12),
                            Text('Setting up...'),
                          ],
                        )
                      : Text(
                          widget.prefilledServerUrl != null 
                              ? 'Login' 
                              : 'Login',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
                
                const SizedBox(height: 24),
              ],
            ),
          ),
        );
      },
    );
  }
}
