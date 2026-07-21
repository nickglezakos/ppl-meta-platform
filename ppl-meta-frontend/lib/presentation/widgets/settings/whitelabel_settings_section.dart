import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import '../../../providers/whitelabel_provider.dart';
import '../../../core/theme/app_theme.dart';

class WhitelabelSettingsSection extends ConsumerStatefulWidget {
  const WhitelabelSettingsSection({super.key});

  @override
  ConsumerState<WhitelabelSettingsSection> createState() => _WhitelabelSettingsSectionState();
}

class _WhitelabelSettingsSectionState extends ConsumerState<WhitelabelSettingsSection> {
  late final TextEditingController _punchlineController;
  bool _punchlineLoaded = false;

  @override
  void initState() {
    super.initState();
    _punchlineController = TextEditingController();
  }

  @override
  void dispose() {
    _punchlineController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final whitelabelState = ref.watch(whitelabelProvider);

    // Populate the punchline controller on first load.
    whitelabelState.whenData((ws) {
      if (!_punchlineLoaded && _punchlineController.text != ws.punchline) {
        _punchlineController.text = ws.punchline;
        _punchlineLoaded = true;
      }
    });

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Row(
            children: [
              Icon(Icons.branding_watermark, color: AppColors.primary, size: 28),
              const SizedBox(width: 12),
              Text(
                'Whitelabel',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                    ),
              ),
            ],
          ),
        ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Customise the application logo and punchline.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),

                // ---- Logo preview ----
                Center(
                  child: whitelabelState.when(
                    data: (ws) {
                      if (ws.logoBytes != null) {
                        return Column(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.memory(
                                ws.logoBytes!,
                                height: 80,
                                fit: BoxFit.contain,
                                errorBuilder: (context, error, stackTrace) {
                                  return const Icon(Icons.broken_image, size: 80, color: Colors.grey);
                                },
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Custom logo active',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.green),
                            ),
                          ],
                        );
                      } else {
                        return Column(
                          children: [
                            Image.asset(
                              'assets/images/eyenet-logo.png',
                              height: 80,
                              errorBuilder: (context, error, stackTrace) {
                                return const Icon(Icons.image, size: 80, color: Colors.grey);
                              },
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Using default Eyenet logo',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
                            ),
                          ],
                        );
                      }
                    },
                    loading: () => const Padding(
                      padding: EdgeInsets.all(16),
                      child: CircularProgressIndicator(),
                    ),
                    error: (error, stack) => Column(
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.red),
                        const SizedBox(height: 8),
                        Text(
                          'Failed to load logo',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.red),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // ---- Logo action buttons ----
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => _pickAndUploadLogo(context, ref),
                      icon: const Icon(Icons.upload_file),
                      label: const Text('Upload Logo'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 12),
                    whitelabelState.when(
                      data: (ws) {
                        if (ws.logoBytes != null) {
                          return OutlinedButton.icon(
                            onPressed: () => _resetLogo(ref),
                            icon: const Icon(Icons.restore),
                            label: const Text('Reset Logo'),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.red,
                              side: const BorderSide(color: Colors.red),
                            ),
                          );
                        }
                        return const SizedBox.shrink();
                      },
                      loading: () => const SizedBox.shrink(),
                      error: (_, __) => const SizedBox.shrink(),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                const Divider(),
                const SizedBox(height: 16),

                // ---- Punchline field ----
                Text(
                  'Punchline',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  'Rendered below the logo on the login screen.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _punchlineController,
                  decoration: const InputDecoration(
                    labelText: 'Punchline',
                    hintText: 'Welcome to Eyenet Vision',
                    border: OutlineInputBorder(),
                  ),
                  maxLength: 100,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => _savePunchline(ref),
                      icon: const Icon(Icons.save),
                      label: const Text('Save Punchline'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: () => _resetPunchline(ref),
                      icon: const Icon(Icons.restore),
                      label: const Text('Reset to Default'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.orange,
                        side: const BorderSide(color: Colors.orange),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ---- Logo helpers ----

  Future<void> _pickAndUploadLogo(BuildContext context, WidgetRef ref) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['png', 'jpg', 'jpeg', 'svg', 'webp'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final bytes = result.files.first.bytes;
      if (bytes == null) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not read the selected file.'), backgroundColor: Colors.red),
          );
        }
        return;
      }

      await ref.read(whitelabelProvider.notifier).uploadLogo(Uint8List.fromList(bytes));

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Logo uploaded successfully!'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload logo: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _resetLogo(WidgetRef ref) async {
    try {
      await ref.read(whitelabelProvider.notifier).resetLogo();
    } catch (_) {}
  }

  // ---- Punchline helpers ----

  Future<void> _savePunchline(WidgetRef ref) async {
    final text = _punchlineController.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Punchline cannot be empty.'), backgroundColor: Colors.red),
      );
      return;
    }
    try {
      await ref.read(whitelabelProvider.notifier).updatePunchline(text);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Punchline saved!'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save punchline: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _resetPunchline(WidgetRef ref) async {
    try {
      await ref.read(whitelabelProvider.notifier).resetPunchline();
      _punchlineController.text = 'Welcome to Eyenet Vision';
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Punchline reset to default.'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to reset punchline: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }
}