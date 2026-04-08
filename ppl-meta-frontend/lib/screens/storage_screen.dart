import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../presentation/widgets/settings/storage_settings_section.dart';
import '../widgets/custom_app_bar.dart';
import '../core/theme/app_theme.dart';

/// Dedicated Storage Management screen.
/// Contains the storage dashboard and preferences
/// previously housed in the Settings screen.
class StorageScreen extends ConsumerWidget {
  const StorageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Storage',
        showBackButton: true,
        showHomeButton: true,
      ),
      backgroundColor: AppColors.background,
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: StorageSettingsSection(),
      ),
    );
  }
}
