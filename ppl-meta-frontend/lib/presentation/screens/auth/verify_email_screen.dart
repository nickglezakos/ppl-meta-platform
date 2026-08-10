import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/services/auth_service.dart';
import '../../../core/providers/auth_provider.dart';

class VerifyEmailScreen extends ConsumerStatefulWidget {
  final String token;

  const VerifyEmailScreen({super.key, required this.token});

  @override
  ConsumerState<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  bool _isLoading = true;
  bool _success = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _verify();
  }

  Future<void> _verify() async {
    if (widget.token.isEmpty) {
      setState(() {
        _isLoading = false;
        _success = false;
        _message = 'Invalid or missing verification token.';
      });
      return;
    }

    try {
      final authService = ref.read(authServiceProvider);
      await authService.verifyEmail(widget.token);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _success = true;
          _message = 'Your email has been verified successfully!';
          // Refresh auth state so the current user reflects email_verified
          ref.read(authNotifierProvider.notifier).checkAuth();
        });
      }
    } on AuthenticationException catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _success = false;
          _message = e.message;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _success = false;
          _message = 'Verification failed. The link may have expired.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Email Verification')),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: _isLoading ? _buildLoading() : _buildResult(),
          ),
        ),
      ),
    );
  }

  Widget _buildLoading() {
    return const Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        CircularProgressIndicator(),
        SizedBox(height: 24),
        Text('Verifying your email...'),
      ],
    );
  }

  Widget _buildResult() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Icon(
          _success ? Icons.check_circle_outline : Icons.error_outline,
          size: 80,
          color: _success ? Colors.green[600] : Theme.of(context).colorScheme.error,
        ),
        const SizedBox(height: 24),
        Text(
          _success ? 'Email Verified!' : 'Verification Failed',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        Text(
          _message ?? '',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).textTheme.bodySmall?.color,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        ElevatedButton(
          onPressed: () => context.go('/home'),
          child: const Text('Go to Home'),
        ),
      ],
    );
  }
}
