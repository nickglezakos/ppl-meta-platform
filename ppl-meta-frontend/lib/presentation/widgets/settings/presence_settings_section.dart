import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../models/presence_models.dart';
import '../../../services/presence_api_client.dart';

class PresenceSettingsSection extends ConsumerStatefulWidget {
  const PresenceSettingsSection({super.key});

  @override
  ConsumerState<PresenceSettingsSection> createState() =>
      _PresenceSettingsSectionState();
}

class _PresenceSettingsSectionState
    extends ConsumerState<PresenceSettingsSection> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _timeoutController;
  late final TextEditingController _attemptsController;

  PresenceInstallationContext? _context;
  bool _allowConcurrentTriggerOperations = true;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _timeoutController = TextEditingController();
    _attemptsController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _timeoutController.dispose();
    _attemptsController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final client = ref.read(presenceApiClientProvider);
    final response = await client.getInstallationContext();

    if (!mounted) {
      return;
    }

    if (!response.success || response.data == null) {
      setState(() {
        _errorMessage = response.error ?? 'Failed to load presence settings.';
        _isLoading = false;
      });
      return;
    }

    final installationContext = response.data!;
    setState(() {
      _context = installationContext;
      _timeoutController.text = installationContext.sessionSettings.sessionTimeoutSeconds.toString();
      _attemptsController.text = installationContext.sessionSettings.maxUnsuccessfulAttempts.toString();
      _allowConcurrentTriggerOperations =
          installationContext.sessionSettings.allowConcurrentTriggerOperations;
      _isLoading = false;
    });
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate() || _context == null) {
      return;
    }

    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    final client = ref.read(presenceApiClientProvider);
    final response = await client.updateInstallationSettings(
      installationUuid: _context!.installationUuid,
      sessionSettings: PresenceSessionSettings(
        sessionTimeoutSeconds: int.parse(_timeoutController.text.trim()),
        maxUnsuccessfulAttempts: int.parse(_attemptsController.text.trim()),
        allowConcurrentTriggerOperations: _allowConcurrentTriggerOperations,
      ),
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _isSaving = false;
    });

    if (!response.success || response.data == null) {
      setState(() {
        _errorMessage = response.error ?? 'Failed to save presence settings.';
      });
      return;
    }

    setState(() {
      _context = response.data;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Presence settings saved.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Row(
            children: [
              Icon(Icons.verified_user, color: AppColors.primary, size: 28),
              const SizedBox(width: 12),
              Text(
                'Presence',
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
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Configure how long presence sessions stay active, how many unsuccessful attempts are allowed before the session fails, and whether concurrent trigger operations remain enabled.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _timeoutController,
                    enabled: !_isLoading && !_isSaving,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Session timeout (seconds)',
                      hintText: '300',
                    ),
                    validator: (value) {
                      final parsed = int.tryParse((value ?? '').trim());
                      if (parsed == null || parsed < 30) {
                        return 'Enter at least 30 seconds.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _attemptsController,
                    enabled: !_isLoading && !_isSaving,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Max unsuccessful attempts',
                      hintText: '3',
                    ),
                    validator: (value) {
                      final parsed = int.tryParse((value ?? '').trim());
                      if (parsed == null || parsed < 1) {
                        return 'Enter at least 1 attempt.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Allow concurrent trigger operations'),
                    subtitle: const Text(
                      'Keep presence-trigger actions allowed to operate alongside parallel triggers on the same camera.',
                    ),
                    value: _allowConcurrentTriggerOperations,
                    onChanged: _isLoading || _isSaving
                        ? null
                        : (value) {
                            setState(() {
                              _allowConcurrentTriggerOperations = value;
                            });
                          },
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ],
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _isLoading || _isSaving ? null : _saveSettings,
                    icon: _isSaving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.save),
                    label: Text(_isSaving ? 'Saving...' : 'Save presence settings'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}