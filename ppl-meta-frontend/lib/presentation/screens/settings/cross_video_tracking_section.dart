import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../providers/settings_providers.dart';

class CrossVideoTrackingSection extends ConsumerWidget {
  const CrossVideoTrackingSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settingsAsync = ref.watch(generalSettingsProvider);
    final notifier = ref.watch(generalSettingsProvider.notifier);

    return settingsAsync.when(
      data: (data) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ListTile(
                leading: const Icon(Icons.merge_type),
                title: const Text('Merge Individuals Rules'),
                subtitle: const Text('How to handle duplicate individuals'),
              ),
              RadioListTile<String>(
                title: const Text('No automatic merging'),
                subtitle: const Text('Manual selection only'),
                value: 'none',
                groupValue: data.mergeIndividualsRule,
                onChanged: (value) {
                  if (value != null) notifier.updateMergeIndividualsRule(value);
                },
              ),
              RadioListTile<String>(
                title: const Text('Semi-automatic merging'),
                subtitle: const Text('Suggest merges, require confirmation'),
                value: 'semi',
                groupValue: data.mergeIndividualsRule,
                onChanged: (value) {
                  if (value != null) notifier.updateMergeIndividualsRule(value);
                },
              ),
              RadioListTile<String>(
                title: const Text('Automatic merging'),
                subtitle: const Text('Automatically merge similar individuals'),
                value: 'auto',
                groupValue: data.mergeIndividualsRule,
                onChanged: (value) {
                  if (value != null) notifier.updateMergeIndividualsRule(value);
                },
              ),
              const SizedBox(height: 8),
              Text(
                'Default Merge Threshold: '
                '${(data.mergeIndividualsThreshold * 100).toStringAsFixed(0)}%',
                style: AppTextStyles.labelMedium,
              ),
              Slider(
                value: data.mergeIndividualsThreshold,
                min: 0.30,
                max: 0.95,
                divisions: 13,
                label:
                    '${(data.mergeIndividualsThreshold * 100).toStringAsFixed(0)}%',
                onChanged: (value) {
                  notifier.updateMergeIndividualsThreshold(value);
                },
              ),
              Text(
                'Used as default threshold for MVR merge operations.',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              SwitchListTile(
                secondary: const Icon(Icons.storage),
                title: const Text('MVR stored comparison'),
                subtitle: const Text(
                  'When enabled, backend-owned MVR analysis resolves through stored super-individual hierarchy.',
                ),
                value: data.mvrStoredComparison,
                onChanged: notifier.updateMvrStoredComparison,
              ),
            ],
          ),
        ),
      ),
      loading: () => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ListTile(
                leading: const Icon(Icons.merge_type),
                title: const Text('Merge Individuals Rules'),
                subtitle: const Text('How to handle duplicate individuals'),
              ),
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(20.0),
                  child: CircularProgressIndicator(),
                ),
              ),
            ],
          ),
        ),
      ),
      error: (error, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ListTile(
                leading: const Icon(Icons.merge_type),
                title: const Text('Merge Individuals Rules'),
                subtitle: Text('Error: $error'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
