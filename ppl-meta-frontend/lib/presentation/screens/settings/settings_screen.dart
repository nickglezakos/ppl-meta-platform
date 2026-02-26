import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/settings/network_settings_section.dart';
import '../../widgets/settings/storage_settings_section.dart';
import '../../widgets/settings/communications_settings_section.dart';
import 'cross_video_tracking_section.dart';
import '../setup/platform_connection_setup_screen.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/config/app_config.dart';
import '../../../services/platform_connectivity_service.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Settings',
      ),
      backgroundColor: AppColors.background,
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Communications Settings Section (Email/SMTP)
            CommunicationsSettingsSection(),

            SizedBox(height: 24),

            // Platform Connection Section (Android)
            _PlatformConnectionSection(),
            
            SizedBox(height: 24),
            
            // Network Settings Section
            NetworkSettingsSection(),
            
            SizedBox(height: 24),
            
            // Storage Settings Section
            StorageSettingsSection(),
            
            SizedBox(height: 24),
            
            // MVR Settings Section
            _MVRSettingsSection(),
          ],
        ),
      ),
    );
  }
}

class _PlatformConnectionSection extends StatelessWidget {
  const _PlatformConnectionSection();

  bool get _isAndroid => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  @override
  Widget build(BuildContext context) {
    if (!_isAndroid) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Row(
            children: [
              Icon(Icons.link, color: AppColors.primary, size: 28),
              const SizedBox(width: 12),
              Text(
                'Platform Connection',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                    ),
              ),
            ],
          ),
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.settings_ethernet),
            title: const Text('Change Platform Connection'),
            subtitle: const Text('Re-run URL and discovery port setup (default 8006).'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              final result = await Navigator.of(context).push<bool>(
                MaterialPageRoute(
                  builder: (_) => PlatformConnectionSetupScreen(
                    onSetupComplete: () {
                      Navigator.of(context).pop(true);
                    },
                  ),
                ),
              );

              if (result == true && context.mounted) {
                final connectivityService = await PlatformConnectivityService.getInstance();
                await AppConfig.initialize(
                  backendHostOverride: connectivityService.backendHost,
                );

                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Platform connection updated successfully.'),
                    ),
                  );
                }
              }
            },
          ),
        ),
      ],
    );
  }
}

/// MVR Settings Section
class _MVRSettingsSection extends StatelessWidget {
  const _MVRSettingsSection();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Row(
            children: [
              Icon(Icons.face, color: AppColors.primary, size: 28),
              const SizedBox(width: 12),
              Text(
                'MVR Settings',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                    ),
              ),
            ],
          ),
        ),
        const CrossVideoTrackingSection(),
      ],
    );
  }
}
