import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/services/auth_service.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;
  bool _codeSent = false;
  bool _resetSuccess = false;
  String? _errorMessage;
  String? _userEmail;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  Future<void> _handleSendCode() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() { _isLoading = true; _errorMessage = null; });
    try {
      final authService = ref.read(authServiceProvider);
      await authService.forgotPassword(_emailController.text.trim());
      if (mounted) { setState(() { _userEmail = _emailController.text.trim(); _codeSent = true; _isLoading = false; }); }
    } catch (e) { if (mounted) { setState(() { _errorMessage = 'Failed to send code. Try again.'; _isLoading = false; }); } }
  }

  Future<void> _handleReset() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_passwordController.text != _confirmController.text) { setState(() => _errorMessage = 'Passwords do not match'); return; }
    setState(() { _isLoading = true; _errorMessage = null; });
    try {
      final authService = ref.read(authServiceProvider);
      await authService.verifyResetCode(_userEmail!, _codeController.text.trim(), _passwordController.text);
      if (mounted) { setState(() { _resetSuccess = true; _isLoading = false; }); }
    } catch (e) { if (mounted) { setState(() { _errorMessage = 'Invalid or expired code.'; _isLoading = false; }); } }
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) return 'Please enter a password';
    if (value.length < 8) return 'At least 8 characters';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.go('/login')),
        title: const Text('Forgot Password'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: _resetSuccess ? _buildSuccessView() : _codeSent ? _buildCodeForm() : _buildEmailForm(),
        ),
      ),
    );
  }

  Widget _buildEmailForm() => Form(key: _formKey, child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Icon(Icons.lock_reset, size: 80, color: Theme.of(context).colorScheme.primary), const SizedBox(height: 24),
    Text('Reset Password', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600), textAlign: TextAlign.center),
    const SizedBox(height: 8), const Text('Enter your email to receive a 6-digit code.', style: TextStyle(color: Colors.grey), textAlign: TextAlign.center),
    const SizedBox(height: 32),
    TextFormField(controller: _emailController, keyboardType: TextInputType.emailAddress, autocorrect: false,
      decoration: const InputDecoration(labelText: 'Email', hintText: 'you@example.com', prefixIcon: Icon(Icons.email_outlined), border: OutlineInputBorder()),
      validator: (v) => (v == null || v.isEmpty || !v.contains('@')) ? 'Enter a valid email' : null),
    const SizedBox(height: 16),
    if (_errorMessage != null) Padding(padding: const EdgeInsets.only(bottom: 16), child: Text(_errorMessage!, style: const TextStyle(color: Colors.red))),
    SizedBox(height: 48, child: ElevatedButton(onPressed: _isLoading ? null : _handleSendCode,
      child: _isLoading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Send Reset Code'))),
    const SizedBox(height: 16), TextButton(onPressed: () => context.go('/login'), child: const Text('Back to Sign In')),
  ]));

  Widget _buildCodeForm() => Form(key: _formKey, child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Icon(Icons.pin_outlined, size: 80, color: Theme.of(context).colorScheme.primary), const SizedBox(height: 24),
    Text('Enter Reset Code', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600), textAlign: TextAlign.center),
    const SizedBox(height: 8), Text('A 6-digit code was sent to $_userEmail', style: const TextStyle(color: Colors.grey), textAlign: TextAlign.center),
    const SizedBox(height: 24),
    TextFormField(controller: _codeController, keyboardType: TextInputType.number, maxLength: 6, textAlign: TextAlign.center,
      style: const TextStyle(fontSize: 28, letterSpacing: 12, fontWeight: FontWeight.bold),
      decoration: const InputDecoration(hintText: '000000', counterText: '', border: OutlineInputBorder()),
      validator: (v) => (v == null || v.length < 6) ? 'Enter the 6-digit code' : null),
    const SizedBox(height: 16),
    Text('Password requirements: at least 8 characters',
      style: TextStyle(fontSize: 12, color: Colors.grey[500])),
    const SizedBox(height: 8),
    TextFormField(controller: _passwordController, obscureText: _obscurePassword,
      decoration: InputDecoration(labelText: 'New Password', prefixIcon: const Icon(Icons.lock_outlined), border: const OutlineInputBorder(),
        suffixIcon: IconButton(icon: Icon(_obscurePassword ? Icons.visibility : Icons.visibility_off), onPressed: () => setState(() => _obscurePassword = !_obscurePassword))),
      validator: _validatePassword),
    const SizedBox(height: 12),
    TextFormField(controller: _confirmController, obscureText: _obscureConfirm,
      decoration: InputDecoration(labelText: 'Confirm Password', prefixIcon: const Icon(Icons.lock_outlined), border: const OutlineInputBorder(),
        suffixIcon: IconButton(icon: Icon(_obscureConfirm ? Icons.visibility : Icons.visibility_off), onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm))),
      validator: (v) => v != _passwordController.text ? 'Passwords do not match' : null),
    const SizedBox(height: 16),
    if (_errorMessage != null) Padding(padding: const EdgeInsets.only(bottom: 16), child: Text(_errorMessage!, style: const TextStyle(color: Colors.red))),
    SizedBox(height: 48, child: ElevatedButton(onPressed: _isLoading ? null : _handleReset,
      child: _isLoading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Reset Password'))),
    const SizedBox(height: 12), TextButton(onPressed: () => setState(() { _codeSent = false; _errorMessage = null; }), child: const Text('← Back to email')),
  ]));

  Widget _buildSuccessView() => Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Icon(Icons.check_circle_outline, size: 80, color: Colors.green[600]), const SizedBox(height: 24),
    Text('Password Reset!', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600), textAlign: TextAlign.center),
    const SizedBox(height: 12), const Text('Your password has been changed successfully.', style: TextStyle(color: Colors.grey), textAlign: TextAlign.center),
    const SizedBox(height: 32), ElevatedButton(onPressed: () => context.go('/login'), child: const Text('Sign In')),
  ]);
}
