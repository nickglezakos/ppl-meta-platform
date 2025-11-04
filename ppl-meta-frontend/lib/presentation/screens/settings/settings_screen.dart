import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/settings/network_settings_section.dart';
import '../../widgets/settings/storage_settings_section.dart';
import '../../widgets/settings/workflow_settings_section.dart';
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
            // Workflow Settings Section
            WorkflowSettingsSection(),
            
            SizedBox(height: 24),

            // Cross-Video Tracking Section (Merge Individuals Rules)
            CrossVideoTrackingSection(),

            SizedBox(height: 24),
            
            // Network Settings Section
            NetworkSettingsSection(),
            
            SizedBox(height: 24),
            
            // Storage Settings Section
            StorageSettingsSection(),
            
            // Additional sections can be added here in the future
            // e.g., UserSettingsSection(), AppearanceSettingsSection(), etc.
          ],
        ),
      ),
    );
  }
}
