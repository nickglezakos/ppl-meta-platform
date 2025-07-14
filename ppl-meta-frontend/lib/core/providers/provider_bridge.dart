import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import '../services/media_api_client.dart';
import '../core/theme/app_theme.dart';

/// Provider setup for our custom components that use Provider instead of Riverpod
class ProviderBridge extends StatelessWidget {
  final Widget child;

  const ProviderBridge({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return provider.MultiProvider(
      providers: [
        provider.Provider<MediaApiClient>(
          create: (_) => MediaApiClient(),
        ),
      ],
      child: child,
    );
  }
}

/// Wrapper for screens that need Provider context
class ProviderScreenWrapper extends StatelessWidget {
  final Widget child;

  const ProviderScreenWrapper({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: Theme.of(context).copyWith(
        // Ensure our custom theme colors are available
        colorScheme: Theme.of(context).colorScheme.copyWith(
          primary: AppColors.primary,
          secondary: AppColors.secondary,
          surface: AppColors.surface,
          error: AppColors.error,
        ),
      ),
      child: ProviderBridge(
        child: child,
      ),
    );
  }
}
