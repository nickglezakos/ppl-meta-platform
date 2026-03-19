import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../models/email_settings.dart';
import '../../../services/email_settings_client.dart';

class CommunicationsSettingsSection extends ConsumerStatefulWidget {
  const CommunicationsSettingsSection({super.key});

  @override
  ConsumerState<CommunicationsSettingsSection> createState() =>
      _CommunicationsSettingsSectionState();
}

class _CommunicationsSettingsSectionState
    extends ConsumerState<CommunicationsSettingsSection> {
  EmailSettings? _settings;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;
  String? _successMessage;

  // Form controllers
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _serverController;
  late TextEditingController _portController;
  late TextEditingController _usernameController;
  late TextEditingController _passwordController;
  late TextEditingController _fromEmailController;
  late TextEditingController _fromNameController;
  late TextEditingController _testEmailController;

  bool _mailEnabled = false;
  bool _useStartTls = true;
  bool _useSslTls = false;
  bool _useCredentials = true;
  bool _showPassword = false;

  @override
  void initState() {
    super.initState();
    _serverController = TextEditingController();
    _portController = TextEditingController();
    _usernameController = TextEditingController();
    _passwordController = TextEditingController();
    _fromEmailController = TextEditingController();
    _fromNameController = TextEditingController();
    _testEmailController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _serverController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _fromEmailController.dispose();
    _fromNameController.dispose();
    _testEmailController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(emailSettingsClientProvider);
      final settings = await client.getEmailSettings();

      setState(() {
        _settings = settings;
        _mailEnabled = settings.mailEnabled;
        _serverController.text = settings.mailServer;
        _portController.text = settings.mailPort.toString();
        _usernameController.text = settings.mailUsername;
        // Password comes masked from server, don't populate
        _fromEmailController.text = settings.mailFrom;
        _fromNameController.text = settings.mailFromName;
        _useStartTls = settings.mailStarttls;
        _useSslTls = settings.mailSslTls;
        _useCredentials = settings.useCredentials;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSaving = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final client = ref.read(emailSettingsClientProvider);
      
      // Only include password if it was changed
      final update = EmailSettingsUpdate(
        mailEnabled: _mailEnabled,
        mailServer: _serverController.text.trim(),
        mailPort: int.parse(_portController.text.trim()),
        mailUsername: _usernameController.text.trim(),
        mailPassword: _passwordController.text.isNotEmpty
            ? _passwordController.text
            : null,
        mailFrom: _fromEmailController.text.trim(),
        mailFromName: _fromNameController.text.trim(),
        mailStarttls: _useStartTls,
        mailSslTls: _useSslTls,
        useCredentials: _useCredentials,
      );

      final updatedSettings = await client.updateEmailSettings(update);

      setState(() {
        _settings = updatedSettings;
        _isSaving = false;
        _passwordController.clear(); // Clear password field after save
      });

      // Show success dialog
      _showSuccessDialog('Email settings saved successfully');
    } catch (e) {
      setState(() {
        _isSaving = false;
      });
      
      // Show error dialog
      _showErrorDialog(e.toString().replaceAll('Exception: ', ''));
    }
  }

  Future<void> _testEmail() async {
    if (_testEmailController.text.trim().isEmpty) {
      _showErrorDialog('Please enter a test email address');
      return;
    }

    if (!_testEmailController.text.contains('@')) {
      _showErrorDialog('Please enter a valid email address');
      return;
    }

    setState(() {
      _isSaving = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final client = ref.read(emailSettingsClientProvider);
      final result = await client.testEmailSettings(_testEmailController.text.trim());

      setState(() {
        _isSaving = false;
      });

      // Show success dialog
      _showSuccessDialog(result['message'] ?? 'Test email sent successfully');

    } catch (e) {
      setState(() {
        _isSaving = false;
      });
      
      // Show error dialog
      _showErrorDialog(e.toString().replaceAll('Exception: ', ''));
    }
  }

  void _showSuccessDialog(String message) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green),
              SizedBox(width: 12),
              Text('Success'),
            ],
          ),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('OK'),
            ),
          ],
        );
      },
    );
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(Icons.error, color: Colors.red),
              SizedBox(width: 12),
              Text('Error'),
            ],
          ),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('OK'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppColors.cardBackground,
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.email_outlined, color: AppColors.primary),
                const SizedBox(width: 12),
                Text(
                  'Communications',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure email and communication settings',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const Divider(height: 32),
            
            if (_isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(),
                ),
              )
            else ...[
              // Email Settings Subsection
              Text(
                'Email Settings (SMTP)',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 16),

              // Error/Success Messages
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.1),
                    border: Border.all(color: Colors.red),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: Colors.red),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                ),

              if (_successMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.1),
                    border: Border.all(color: Colors.green),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_outline, color: Colors.green),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _successMessage!,
                          style: const TextStyle(color: Colors.green),
                        ),
                      ),
                    ],
                  ),
                ),

              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Enable Email Switch
                    SwitchListTile(
                      title: const Text('Enable Email'),
                      subtitle: const Text('Turn on email notifications and alerts'),
                      value: _mailEnabled,
                      onChanged: (value) {
                        setState(() {
                          _mailEnabled = value;
                        });
                      },
                      activeColor: AppColors.primary,
                    ),
                    const SizedBox(height: 16),

                    // Server Settings
                    Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: TextFormField(
                            controller: _serverController,
                            decoration: const InputDecoration(
                              labelText: 'SMTP Server *',
                              hintText: 'smtp.gmail.com',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'Server is required';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _portController,
                            decoration: const InputDecoration(
                              labelText: 'Port *',
                              hintText: '587',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'Required';
                              }
                              final port = int.tryParse(value.trim());
                              if (port == null || port < 1 || port > 65535) {
                                return 'Invalid port';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Credentials
                    TextFormField(
                      controller: _usernameController,
                      decoration: const InputDecoration(
                        labelText: 'Username/Email *',
                        hintText: 'your-email@example.com',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Username is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _passwordController,
                      obscureText: !_showPassword,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        hintText: 'Leave empty to keep current password',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _showPassword ? Icons.visibility_off : Icons.visibility,
                          ),
                          onPressed: () {
                            setState(() {
                              _showPassword = !_showPassword;
                            });
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // From Email Settings
                    TextFormField(
                      controller: _fromEmailController,
                      decoration: const InputDecoration(
                        labelText: 'From Email *',
                        hintText: 'noreply@yourcompany.com',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'From email is required';
                        }
                        if (!value.contains('@')) {
                          return 'Invalid email address';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _fromNameController,
                      decoration: const InputDecoration(
                        labelText: 'From Name *',
                        hintText: 'PPL Meta Platform',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'From name is required';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Security Options
                    CheckboxListTile(
                      title: const Text('Use STARTTLS'),
                      subtitle: const Text('Recommended for port 587'),
                      value: _useStartTls,
                      onChanged: (value) {
                        setState(() {
                          _useStartTls = value ?? true;
                        });
                      },
                      activeColor: AppColors.primary,
                    ),

                    CheckboxListTile(
                      title: const Text('Use SSL/TLS'),
                      subtitle: const Text('Recommended for port 465'),
                      value: _useSslTls,
                      onChanged: (value) {
                        setState(() {
                          _useSslTls = value ?? false;
                        });
                      },
                      activeColor: AppColors.primary,
                    ),

                    CheckboxListTile(
                      title: const Text('Use Authentication'),
                      subtitle: const Text('Most servers require authentication'),
                      value: _useCredentials,
                      onChanged: (value) {
                        setState(() {
                          _useCredentials = value ?? true;
                        });
                      },
                      activeColor: AppColors.primary,
                    ),

                    const SizedBox(height: 24),

                    // Action Buttons
                    Row(
                      children: [
                        ElevatedButton.icon(
                          onPressed: _isSaving ? null : _saveSettings,
                          icon: _isSaving
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.save),
                          label: Text(_isSaving ? 'Saving...' : 'Save Settings'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 12,
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        TextButton.icon(
                          onPressed: _isSaving ? null : _loadSettings,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Reset'),
                        ),
                      ],
                    ),

                    const Divider(height: 48),

                    // Test Email Section
                    Text(
                      'Test Email Configuration',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _testEmailController,
                            decoration: const InputDecoration(
                              labelText: 'Test Email Address',
                              hintText: 'test@example.com',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        ElevatedButton.icon(
                          onPressed: _isSaving ? null : _testEmail,
                          icon: const Icon(Icons.send),
                          label: const Text('Send Test'),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 20,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
