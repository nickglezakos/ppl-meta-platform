import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../widgets/settings/communications_settings_section.dart';
import '../../widgets/settings/presence_settings_section.dart';
import '../../widgets/settings/whitelabel_settings_section.dart';
import 'cross_video_tracking_section.dart';
import '../setup/platform_connection_setup_screen.dart';
import '../../../core/api/api_client.dart';
import '../../../widgets/custom_app_bar.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/config/app_config.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/providers/bootstrap_provider.dart';
import '../../../providers/authority_status_providers.dart';
import '../../../services/authority_status_client.dart';
import '../../../services/platform_connectivity_service.dart';
import '../../../widgets/authority_status_card.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(authNotifierProvider).user;
    final bootstrapStatus = ref.watch(bootstrapStatusProvider);

    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Settings',
      ),
      backgroundColor: AppColors.background,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Communications Settings Section (Email/SMTP)
            const CommunicationsSettingsSection(),

            const SizedBox(height: 24),

            const PresenceSettingsSection(),

            const SizedBox(height: 24),

            AuthorityStatusCard(showAdminDetails: currentUser?.isAdmin ?? false),

            const SizedBox(height: 24),

            bootstrapStatus.when(
              data: (status) => status.complete
                  ? const _AuthorityManagedNotice()
                  : const _AuthorityApplicationKeySection(),
              loading: () => const _AuthorityApplicationKeySection(),
              error: (_, __) => const _AuthorityApplicationKeySection(),
            ),

            const SizedBox(height: 24),

            // Platform Connection Section (Android)
            const _PlatformConnectionSection(),
            
            const SizedBox(height: 24),
            
            // MVR Settings Section
            const _MVRSettingsSection(),
            
            const SizedBox(height: 24),
            
            // Whitelabel Settings Section
            const WhitelabelSettingsSection(),
          ],
        ),
      ),
    );
  }
}

class _AuthorityApplicationKeySection extends ConsumerStatefulWidget {
  const _AuthorityApplicationKeySection();

  @override
  ConsumerState<_AuthorityApplicationKeySection> createState() =>
      _AuthorityApplicationKeySectionState();
}

class _AuthorityApplicationKeySectionState
    extends ConsumerState<_AuthorityApplicationKeySection> {
  static const String _applicationKeySetting = 'authority_application_key';
  static const String _installationUuidSetting = 'authority_installation_uuid';

  late final TextEditingController _applicationKeyController;
  late final TextEditingController _installationUuidController;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _applicationKeyController = TextEditingController();
    _installationUuidController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _applicationKeyController.dispose();
    _installationUuidController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final apiClient = ref.read(apiClientProvider);
    try {
      final applicationKeyResponse = await _readSetting(
        apiClient,
        _applicationKeySetting,
      );
      final installationUuidResponse = await _readSetting(
        apiClient,
        _installationUuidSetting,
      );
      if (!mounted) {
        return;
      }

      setState(() {
        _applicationKeyController.text = applicationKeyResponse ?? '';
        _installationUuidController.text = installationUuidResponse ?? '';
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = 'Failed to load saved authority settings.';
        _isLoading = false;
      });
    }
  }

  Future<String?> _readSetting(ApiClient apiClient, String key) async {
    try {
      final response = await apiClient.get('/api/v1/settings/$key');
      return response.data['value']?.toString();
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  Future<void> _saveSettings() async {
    final apiClient = ref.read(apiClientProvider);
    final applicationKey = _applicationKeyController.text.trim();
    final installationUuid = _installationUuidController.text.trim();

    setState(() {
      _isSaving = true;
      _errorMessage = null;
    });

    try {
      await apiClient.post('/api/v1/settings/', data: {
        'key': _applicationKeySetting,
        'value': applicationKey,
      });
      await apiClient.post('/api/v1/settings/', data: {
        'key': _installationUuidSetting,
        'value': installationUuid,
      });

      await ref.read(authorityStatusClientProvider).refreshAuthorityStatus();

      ref.invalidate(authorityStatusProvider);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Bootstrap authority binding saved and refreshed.'),
        ),
      );
    } catch (_) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = 'Failed to save authority settings.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _copyValue(String value, String label) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label copied.'),
      ),
    );
  }

  Widget _buildSettingField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required String copyLabel,
  }) {
    final trimmedValue = controller.text.trim();

    return TextField(
      controller: controller,
      enabled: !_isLoading && !_isSaving,
      autocorrect: false,
      enableSuggestions: false,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        errorText: _errorMessage,
        suffixIcon: _isLoading
            ? const Padding(
                padding: EdgeInsets.all(12),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              )
            : (trimmedValue.isEmpty
                ? null
                : IconButton(
                    tooltip: 'Copy $copyLabel',
                    onPressed: () => _copyValue(trimmedValue, copyLabel),
                    icon: const Icon(Icons.copy),
                  )),
      ),
      onChanged: (_) {
        if (_errorMessage != null) {
          setState(() {
            _errorMessage = null;
          });
        }
        setState(() {});
      },
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
              Icon(Icons.vpn_key, color: AppColors.primary, size: 28),
              const SizedBox(width: 12),
              Text(
                'Bootstrap Authority Binding',
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
                  'Use this only during bootstrap to bind the node to the correct Authority licence record. After bootstrap completes, licence state should be managed in Authority as the single source of truth.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                _buildSettingField(
                  controller: _applicationKeyController,
                  label: 'Application key',
                  hint: 'Paste the generated application key',
                  copyLabel: 'Application key',
                ),
                const SizedBox(height: 12),
                _buildSettingField(
                  controller: _installationUuidController,
                  label: 'Installation UUID',
                  hint: 'Paste or confirm the bound installation UUID',
                  copyLabel: 'Installation UUID',
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    FilledButton.icon(
                      onPressed: _isLoading || _isSaving ? null : _saveSettings,
                      icon: _isSaving
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.save),
                      label: Text(_isSaving ? 'Saving...' : 'Save settings'),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: _isLoading || _applicationKeyController.text.trim().isEmpty
                          ? null
                          : () => _copyValue(
                                _applicationKeyController.text.trim(),
                                'Application key',
                              ),
                      icon: const Icon(Icons.copy),
                      label: const Text('Copy key'),
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
}

class _AuthorityManagedNotice extends StatelessWidget {
  const _AuthorityManagedNotice();

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
                'Authority Managed Licence',
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
            child: Text(
              'This node is already bootstrapped. The application key is no longer editable here. Update licence status and related metadata in Authority only, then refresh the Authority Status card to sync the latest state.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ),
      ],
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
