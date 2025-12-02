import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/media_api_client.dart';
import '../../services/signage_api_client.dart';
import '../../services/discovery_service_client.dart';
import '../../providers/signage_provider.dart';
import '../theme/app_theme.dart';
import '../api/api_client.dart';

/// Provider setup for our custom components that use Provider instead of Riverpod
class ProviderBridge extends ConsumerWidget {
  final Widget child;

  const ProviderBridge({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Get the authenticated ApiClient from Riverpod
    final apiClient = ref.watch(apiClientProvider);
    
    // Create service clients
    final discoveryClient = DiscoveryServiceClient();
    
    return provider.MultiProvider(
      providers: [
        provider.Provider<MediaApiClient>(
          create: (_) => MediaApiClient(apiClient),
        ),
        provider.Provider<DiscoveryServiceClient>(
          create: (_) => discoveryClient,
        ),
        provider.Provider<SignageApiClient>(
          create: (_) => SignageApiClient(apiClient, discoveryClient),
        ),
        provider.ChangeNotifierProvider<SignageProvider>(
          create: (context) => SignageProvider(
            context.read<SignageApiClient>(),
          ),
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
