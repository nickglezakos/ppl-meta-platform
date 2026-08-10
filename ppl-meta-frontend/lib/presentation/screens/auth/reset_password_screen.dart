import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class ResetPasswordScreen extends StatelessWidget {
  final String token;
  const ResetPasswordScreen({super.key, this.token = ''});

  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.go('/forgot-password');
    });
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
