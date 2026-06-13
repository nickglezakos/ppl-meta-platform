import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers/bootstrap_provider.dart';
import '../../../core/providers/auth_provider.dart';
import '../../widgets/common/loading_overlay.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  final bool isBootstrapFlow;

  const RegisterScreen({super.key, this.isBootstrapFlow = false});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _applicationKeyController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _applicationKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final bootstrapStatus = ref.watch(bootstrapStatusProvider);
    final authNotifier = ref.read(authNotifierProvider.notifier);
    final requiresBootstrap = widget.isBootstrapFlow;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Account'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Stack(
        children: [
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const SizedBox(height: 24),

                          // Title
                          Text(
                            requiresBootstrap ? 'Activate Your Installation' : 'Join Eyenet Vision',
                            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            requiresBootstrap
                                ? 'Create the first approved owner account for this installation'
                                : 'Create your account to get started',
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              color: Theme.of(context).textTheme.bodySmall?.color,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),

                          const SizedBox(height: 32),

                          if (requiresBootstrap)
                            bootstrapStatus.when(
                              data: (status) {
                                if (!status.needsOwnerBootstrap) {
                                  return const SizedBox.shrink();
                                }
                                final approvedOwner = status.owner.approvedOwnerEmail;
                                return Container(
                                  width: double.infinity,
                                  margin: const EdgeInsets.only(bottom: 24),
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: Colors.blue.shade700),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'First-install owner bootstrap',
                                        style: TextStyle(fontWeight: FontWeight.w600),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        approvedOwner != null && approvedOwner.isNotEmpty
                                            ? 'Create the approved owner account using $approvedOwner so the platform can complete its first activation.'
                                            : 'Create the approved owner account so the platform can complete its first activation.',
                                      ),
                                    ],
                                  ),
                                );
                              },
                              loading: () => const SizedBox.shrink(),
                              error: (error, __) => Container(
                                width: double.infinity,
                                margin: const EdgeInsets.only(bottom: 24),
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: Colors.red.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: Colors.red.shade700),
                                ),
                                child: Text(
                                  'Bootstrap status could not be loaded. Check gateway routing and Node availability. Error: $error',
                                ),
                              ),
                            ),

                          // Registration form
                          Form(
                            key: _formKey,
                            child: Column(
                              children: [
                                // Username field
                                TextFormField(
                                  controller: _usernameController,
                                  autocorrect: false,
                                  decoration: const InputDecoration(
                                    labelText: 'Username',
                                    hintText: 'Choose a username',
                                    prefixIcon: Icon(Icons.person_outlined),
                                    border: OutlineInputBorder(),
                                  ),
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter a username';
                                    }
                                    if (value.length < 3) {
                                      return 'Username must be at least 3 characters';
                                    }
                                    if (!RegExp(r'^[a-zA-Z0-9_]+$').hasMatch(value)) {
                                      return 'Username can only contain letters, numbers, and underscores';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 16),

                                // Email field
                                TextFormField(
                                  controller: _emailController,
                                  keyboardType: TextInputType.emailAddress,
                                  autocorrect: false,
                                  decoration: const InputDecoration(
                                    labelText: 'Email',
                                    hintText: 'Enter your email',
                                    prefixIcon: Icon(Icons.email_outlined),
                                    border: OutlineInputBorder(),
                                  ),
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter your email';
                                    }
                                    if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) {
                                      return 'Please enter a valid email';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 16),

                                if (requiresBootstrap) ...[
                                  TextFormField(
                                    controller: _applicationKeyController,
                                    autocorrect: false,
                                    decoration: const InputDecoration(
                                      labelText: 'Licence / Application Key',
                                      hintText: 'Enter the installation key',
                                      prefixIcon: Icon(Icons.vpn_key_outlined),
                                      border: OutlineInputBorder(),
                                    ),
                                    validator: (value) {
                                      if (!requiresBootstrap) {
                                        return null;
                                      }
                                      if (value == null || value.trim().isEmpty) {
                                        return 'Please enter the licence or application key';
                                      }
                                      if (value.trim().length < 3) {
                                        return 'Key must be at least 3 characters';
                                      }
                                      return null;
                                    },
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // Password field
                                TextFormField(
                                  controller: _passwordController,
                                  obscureText: _obscurePassword,
                                  decoration: InputDecoration(
                                    labelText: 'Password',
                                    hintText: 'Create a password',
                                    prefixIcon: const Icon(Icons.lock_outlined),
                                    suffixIcon: IconButton(
                                      icon: Icon(
                                        _obscurePassword ? Icons.visibility : Icons.visibility_off,
                                      ),
                                      onPressed: () {
                                        setState(() {
                                          _obscurePassword = !_obscurePassword;
                                        });
                                      },
                                    ),
                                    border: const OutlineInputBorder(),
                                  ),
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter a password';
                                    }
                                    if (value.length < 8) {
                                      return 'Password must be at least 8 characters';
                                    }
                                    if (!RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)').hasMatch(value)) {
                                      return 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 16),

                                // Confirm password field
                                TextFormField(
                                  controller: _confirmPasswordController,
                                  obscureText: _obscureConfirmPassword,
                                  decoration: InputDecoration(
                                    labelText: 'Confirm Password',
                                    hintText: 'Confirm your password',
                                    prefixIcon: const Icon(Icons.lock_outlined),
                                    suffixIcon: IconButton(
                                      icon: Icon(
                                        _obscureConfirmPassword ? Icons.visibility : Icons.visibility_off,
                                      ),
                                      onPressed: () {
                                        setState(() {
                                          _obscureConfirmPassword = !_obscureConfirmPassword;
                                        });
                                      },
                                    ),
                                    border: const OutlineInputBorder(),
                                  ),
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please confirm your password';
                                    }
                                    if (value != _passwordController.text) {
                                      return 'Passwords do not match';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 24),

                                // Error message
                                if (authState.error != null) ...[
                                  Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Theme.of(context).colorScheme.errorContainer,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.error_outline,
                                          color: Theme.of(context).colorScheme.error,
                                          size: 20,
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            authState.error!,
                                            style: TextStyle(
                                              color: Theme.of(context).colorScheme.error,
                                            ),
                                          ),
                                        ),
                                        IconButton(
                                          onPressed: () => authNotifier.clearError(),
                                          icon: Icon(
                                            Icons.close,
                                            color: Theme.of(context).colorScheme.error,
                                            size: 20,
                                          ),
                                          constraints: const BoxConstraints(),
                                          padding: EdgeInsets.zero,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // Register button
                                SizedBox(
                                  width: double.infinity,
                                  height: 48,
                                  child: ElevatedButton(
                                    onPressed: authState.isLoading ? null : _handleRegister,
                                    child: authState.isLoading
                                        ? const SizedBox(
                                            height: 20,
                                            width: 20,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                            ),
                                          )
                                        : const Text('Create Account'),
                                  ),
                                ),
                                const SizedBox(height: 16),

                                // Terms and privacy
                                if (!requiresBootstrap)
                                  Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 16),
                                    child: Text(
                                      'By creating an account, you agree to our Terms of Service and Privacy Policy',
                                      style: Theme.of(context).textTheme.bodySmall,
                                      textAlign: TextAlign.center,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Login link
                  if (!requiresBootstrap)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Already have an account? '),
                        TextButton(
                          onPressed: () => context.pop(),
                          child: const Text('Sign In'),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),

          // Loading overlay
          if (authState.isLoading)
            const LoadingOverlay(message: 'Creating account...'),
        ],
      ),
    );
  }

  Future<void> _handleRegister() async {
    if (_formKey.currentState?.validate() ?? false) {
      final authNotifier = ref.read(authNotifierProvider.notifier);
      final requiresBootstrap = widget.isBootstrapFlow;
      
      final success = requiresBootstrap
          ? await authNotifier.bootstrapActivate(
              _usernameController.text.trim(),
              _emailController.text.trim(),
              _passwordController.text,
              _applicationKeyController.text.trim(),
            )
          : await authNotifier.register(
              _usernameController.text.trim(),
              _emailController.text.trim(),
              _passwordController.text,
            );

      if (success && mounted) {
        if (requiresBootstrap) {
          context.go('/home');
          return;
        }

        // Show success message and navigate back to login
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => AlertDialog(
            icon: const Icon(
              Icons.check_circle,
              color: Colors.green,
              size: 48,
            ),
            title: const Text('Account Created'),
            content: const Text(
              'Your account has been created successfully! Please check your email to verify your account before signing in.',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  context.pop(); // Go back to login screen
                },
                child: const Text('Continue to Sign In'),
              ),
            ],
          ),
        );
      }
    }
  }
}
