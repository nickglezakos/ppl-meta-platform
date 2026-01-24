import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/settings/network_settings_section.dart';
import '../../widgets/settings/storage_settings_section.dart';
import '../../widgets/settings/communications_settings_section.dart';
import 'cross_video_tracking_section.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../../core/theme/app_theme.dart';

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
