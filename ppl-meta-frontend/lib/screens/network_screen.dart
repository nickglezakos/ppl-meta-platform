import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../presentation/widgets/settings/network_settings_section.dart';
import '../widgets/custom_app_bar.dart';
import '../core/theme/app_theme.dart';

/// Dedicated Network & Services screen.
/// Contains the network settings previously housed in the Settings screen.
class NetworkScreen extends ConsumerWidget {
  const NetworkScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Network & Services',
        showBackButton: true,
        showHomeButton: true,
      ),
      backgroundColor: AppColors.background,
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: NetworkSettingsSection(),
      ),
    );
  }
}
