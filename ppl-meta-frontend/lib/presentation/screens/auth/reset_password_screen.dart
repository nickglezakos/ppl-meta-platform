import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/services/auth_service.dart';

class ResetPasswordScreen extends ConsumerStatefulWidget {
  final String token;

  const ResetPasswordScreen({super.key, required this.token});

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;
  bool _resetSuccess = false;
  String? _errorMessage;

  @override
  void dispose() {
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) return 'Please enter a password';
    if (value.length < 8) return 'Password must be at least 8 characters';
    if (!RegExp(r'[A-Z]').hasMatch(value)) {
      return 'Password must contain an uppercase letter';
    }
    if (!RegExp(r'[a-z]').hasMatch(value)) {
      return 'Password must contain a lowercase letter';
    }
    if (!RegExp(r'[0-9]').hasMatch(value)) {
      return 'Password must contain a digit';
    }
    if (!RegExp(r'[!@#\$%\^&\*\(\)_\+\-=\[\]\{\};:,.<>?/\\|`~]')
        .hasMatch(value)) {
      return 'Password must contain a special character';
    }
    return null;
  }

  Future<void> _handleSubmit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = ref.read(authServiceProvider);
      await authService.resetPassword(
          widget.token, _passwordController.text);
      if (mounted) {
        setState(() {
          _resetSuccess = true;
          _isLoading = false;
        });
      }
    } on AuthenticationException catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.message;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'An unexpected error occurred. Please try again.';
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.token.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Reset Password')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline,
                  size: 64, color: Theme.of(context).colorScheme.error),
              const SizedBox(height: 16),
              const Text('Invalid or missing reset token.'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.go('/forgot-password'),
                child: const Text('Request New Link'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Reset Password')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: _resetSuccess ? _buildSuccessView() : _buildFormView(),
        ),
      ),
    );
  }

  Widget _buildSuccessView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Icon(
          Icons.check_circle_outline,
          size: 80,
          color: Colors.green[600],
        ),
        const SizedBox(height: 24),
        Text(
          'Password Reset!',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        Text(
          'Your password has been updated successfully.\nYou can now sign in with your new password.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).textTheme.bodySmall?.color,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        ElevatedButton(
          onPressed: () => context.go('/login'),
          child: const Text('Go to Sign In'),
        ),
      ],
    );
  }

  Widget _buildFormView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Icon(
          Icons.lock_outline,
          size: 80,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(height: 24),
        Text(
          'Set a new password',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'Your new password must be at least 8 characters and include uppercase, lowercase, a digit, and a special character.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).textTheme.bodySmall?.color,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        Form(
          key: _formKey,
          child: Column(
            children: [
              TextFormField(
                controller: _passwordController,
                obscureText: _obscurePassword,
                decoration: InputDecoration(
                  labelText: 'New Password',
                  prefixIcon: const Icon(Icons.lock_outlined),
                  suffixIcon: IconButton(
                    icon: Icon(_obscurePassword
                        ? Icons.visibility
                        : Icons.visibility_off),
                    onPressed: () =>
                        setState(() => _obscurePassword = !_obscurePassword),
                  ),
                  border: const OutlineInputBorder(),
                ),
                validator: _validatePassword,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _confirmController,
                obscureText: _obscureConfirm,
                decoration: InputDecoration(
                  labelText: 'Confirm Password',
                  prefixIcon: const Icon(Icons.lock_outlined),
                  suffixIcon: IconButton(
                    icon: Icon(_obscureConfirm
                        ? Icons.visibility
                        : Icons.visibility_off),
                    onPressed: () =>
                        setState(() => _obscureConfirm = !_obscureConfirm),
                  ),
                  border: const OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value != _passwordController.text) {
                    return 'Passwords do not match';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              if (_errorMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline,
                          color: Theme.of(context).colorScheme.error, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(
                              color: Theme.of(context).colorScheme.error),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _handleSubmit,
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Reset Password'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
