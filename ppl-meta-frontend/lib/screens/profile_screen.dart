import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/providers/auth_provider.dart';
import '../core/api/api_client.dart';
import '../core/theme/app_theme.dart';
import '../core/models/user.dart';
import '../widgets/change_password_dialog.dart';
import '../widgets/custom_app_bar.dart';
import '../presentation/pages/developer_settings_page.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  final int? targetUserId;

  const ProfileScreen({super.key, this.targetUserId});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  User? _targetUser;
  List<String> _targetCapabilities = [];
  List<String> _targetRoles = [];
  bool _isLoadingTarget = false;
  bool _isTogglingCapability = false;
  bool _isSettingPassword = false;

  bool get _isAdminMode => widget.targetUserId != null;

  @override
  void initState() {
    super.initState();
    if (_isAdminMode) {
      _loadTargetUser();
    }
  }

  Future<void> _loadTargetUser() async {
    setState(() => _isLoadingTarget = true);
    try {
      final apiClient = ref.read(apiClientProvider);
      final resp = await apiClient.get('/api/v1/users/user-profile/${widget.targetUserId}');
      if (resp.data != null) {
        final data = resp.data as Map<String, dynamic>;
        _targetUser = User.fromJson(data);
        _targetRoles = List<String>.from(data['roles'] ?? []);
        _targetCapabilities = List<String>.from(data['capabilities'] ?? []);
      }
    } catch (e) {
      debugPrint('Error loading target user: $e');
    }
    if (mounted) setState(() => _isLoadingTarget = false);
  }

  Future<void> _toggleCapability(String capability, bool enabled) async {
    setState(() => _isTogglingCapability = true);
    try {
      final apiClient = ref.read(apiClientProvider);
      final resp = await apiClient.post(
        '/api/v1/users/toggle-capability/${widget.targetUserId}',
        data: {'capability': capability, 'enabled': enabled},
      );
      if (resp.data != null) {
        final data = resp.data as Map<String, dynamic>;
        setState(() {
          _targetCapabilities = List<String>.from(data['capabilities'] ?? []);
          _targetRoles = List<String>.from(data['roles'] ?? []);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update capability: $e')),
        );
      }
    }
    if (mounted) setState(() => _isTogglingCapability = false);
  }

  Future<void> _adminSetPassword(User targetUser, String newPassword, bool sendEmail) async {
    setState(() => _isSettingPassword = true);
    try {
      final apiClient = ref.read(apiClientProvider);
      final resp = await apiClient.post(
        '/api/v1/users/admin/set-password/${widget.targetUserId}',
        data: {'new_password': newPassword, 'send_email': sendEmail},
      );
      if (mounted) {
        final emailSent = (resp.data as Map<String, dynamic>?)?['email_sent'] == true;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              emailSent
                  ? 'Password updated and sent to ${targetUser.email}'
                  : 'Password updated successfully',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to set password: $e')),
        );
      }
    }
    if (mounted) setState(() => _isSettingPassword = false);
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final authNotifier = ref.read(authNotifierProvider.notifier);
    final currentUser = authState.user;

    if (currentUser == null) {
      return Scaffold(
        appBar: const CustomAppBar(title: 'Profile'),
        body: const Center(child: Text('User not found')),
      );
    }

    // Admin viewing another user
    if (_isAdminMode) {
      if (_isLoadingTarget) {
        return Scaffold(
          appBar: const CustomAppBar(title: 'User Profile'),
          body: const Center(child: CircularProgressIndicator()),
        );
      }
      final user = _targetUser;
      if (user == null) {
        return Scaffold(
          appBar: const CustomAppBar(title: 'User Profile'),
          body: const Center(child: Text('User not found')),
        );
      }
      return _buildAdminProfileView(context, user, currentUser);
    }

    // Own profile
    return _buildOwnProfileView(context, currentUser, authNotifier);
  }

  Widget _buildAdminProfileView(BuildContext context, User user, User currentUser) {
    final isAdmin = currentUser.isAdmin;

    return Scaffold(
      appBar: const CustomAppBar(title: 'User Profile'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildProfileHeader(context, user),
            const SizedBox(height: 16),
            _buildAccountInfo(context, user),
            const SizedBox(height: 24),
            // Roles
            Text(
              'Roles',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _targetRoles.map((role) {
                return Chip(
                  label: Text(role),
                  backgroundColor: role == 'admin'
                      ? Colors.deepPurple.withOpacity(0.15)
                      : Colors.blue.withOpacity(0.15),
                );
              }).toList(),
            ),
            if (_targetRoles.isEmpty)
              const Text('No roles assigned', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 24),
            // Capabilities (admin can toggle)
            Text(
              'Capabilities',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            if (isAdmin) ...[
              _CapabilityToggle(
                capability: 'media:view',
                label: 'Media Viewing',
                description: 'Allow this user to view, download, and stream media files',
                enabled: _targetCapabilities.contains('media:view'),
                isLoading: _isTogglingCapability,
                onChanged: (enabled) => _toggleCapability('media:view', enabled),
              ),
            ] else ...[
              _ProfileInfoCard(
                icon: Icons.visibility,
                title: 'Media Viewing',
                value: _targetCapabilities.contains('media:view') ? 'Enabled' : 'Disabled',
              ),
            ],
            const SizedBox(height: 24),
            // Admin: Set Password
            if (isAdmin) ...[              Text(
                'Set Password',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 12),
              _AdminSetPasswordCard(
                isLoading: _isSettingPassword,
                onSubmit: (newPassword, sendEmail) => _adminSetPassword(user, newPassword, sendEmail),
              ),
              const SizedBox(height: 24),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildOwnProfileView(BuildContext context, User user, authNotifier) {
    return Scaffold(
      appBar: const CustomAppBar(title: 'Profile'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildProfileHeader(context, user),
            const SizedBox(height: 16),
            _buildAccountInfo(context, user),
            const SizedBox(height: 24),

            // Settings Section
            Text(
              'Settings',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            _SettingsOption(
              icon: Icons.edit,
              title: 'Edit Profile',
              subtitle: 'Update your personal information',
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Edit profile feature coming soon!')),
                );
              },
            ),
            _SettingsOption(
              icon: Icons.security,
              title: 'Change Password',
              subtitle: 'Update your account password',
              onTap: () {
                showDialog(
                  context: context,
                  builder: (context) => const ChangePasswordDialog(),
                );
              },
            ),
            _SettingsOption(
              icon: Icons.notifications,
              title: 'Notifications',
              subtitle: 'Manage notification preferences',
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Notification settings coming soon!')),
                );
              },
            ),
            _SettingsOption(
              icon: Icons.privacy_tip,
              title: 'Privacy & Security',
              subtitle: 'Manage your privacy settings',
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Privacy settings coming soon!')),
                );
              },
            ),
            _SettingsOption(
              icon: Icons.developer_mode,
              title: 'Developer Settings',
              subtitle: 'Marketing tools and screenshots',
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => const DeveloperSettingsPage(),
                  ),
                );
              },
            ),
            _SettingsOption(
              icon: Icons.featured_play_list,
              title: 'Features',
              subtitle: 'Manage advanced features and capabilities',
              onTap: () => context.go('/features'),
            ),
            const SizedBox(height: 24),

            // Quick Actions Section
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            _SettingsOption(
              icon: Icons.cloud_upload,
              title: 'Upload Media',
              subtitle: 'Upload new files to your library',
              onTap: () => context.go('/upload'),
            ),
            _SettingsOption(
              icon: Icons.photo_library,
              title: 'View Gallery',
              subtitle: 'Browse your media collection',
              onTap: () => context.go('/gallery'),
            ),
            _SettingsOption(
              icon: Icons.analytics,
              title: 'Analytics',
              subtitle: 'View your usage statistics',
              onTap: () => context.go('/analytics'),
            ),
            const SizedBox(height: 32),

            // Logout Button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _showLogoutDialog(context, authNotifier),
                icon: const Icon(Icons.logout, color: Colors.red),
                label: const Text('Logout', style: TextStyle(color: Colors.red)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.red),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileHeader(BuildContext context, User user) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            CircleAvatar(
              radius: 60,
              backgroundColor: AppColors.primary.withOpacity(0.1),
              child: Text(
                user.username.isNotEmpty ? user.username[0].toUpperCase() : 'U',
                style: TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              user.username,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              user.email,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: user.emailVerified
                    ? Colors.green.withOpacity(0.1)
                    : Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: user.emailVerified ? Colors.green : Colors.orange,
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    user.emailVerified ? Icons.verified : Icons.warning,
                    size: 16,
                    color: user.emailVerified ? Colors.green : Colors.orange,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    user.emailVerified ? 'Email Verified' : 'Email Not Verified',
                    style: TextStyle(
                      color: user.emailVerified ? Colors.green : Colors.orange,
                      fontWeight: FontWeight.w500,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAccountInfo(BuildContext context, User user) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Account Information',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        _ProfileInfoCard(
          icon: Icons.calendar_today,
          title: 'Member Since',
          value: user.createdAt != null ? _formatDate(user.createdAt!) : 'Unknown',
        ),
        _ProfileInfoCard(
          icon: Icons.update,
          title: 'Last Updated',
          value: user.updatedAt != null ? _formatDate(user.updatedAt!) : 'Unknown',
        ),
      ],
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    if (difference.inDays > 365) {
      final years = (difference.inDays / 365).floor();
      return '$years year${years == 1 ? '' : 's'} ago';
    } else if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return '$months month${months == 1 ? '' : 's'} ago';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} day${difference.inDays == 1 ? '' : 's'} ago';
    } else {
      return 'Today';
    }
  }

  void _showLogoutDialog(BuildContext context, authNotifier) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await authNotifier.logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Logout'),
          ),
        ],
      ),
    );
  }
}

class _CapabilityToggle extends StatelessWidget {
  final String capability;
  final String label;
  final String description;
  final bool enabled;
  final bool isLoading;
  final ValueChanged<bool> onChanged;

  const _CapabilityToggle({
    required this.capability,
    required this.label,
    required this.description,
    required this.enabled,
    required this.isLoading,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: SwitchListTile(
        secondary: Icon(
          enabled ? Icons.visibility : Icons.visibility_off,
          color: enabled ? AppColors.primary : Colors.grey,
        ),
        title: Text(
          label,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        subtitle: Text(
          description,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
        value: enabled,
        onChanged: isLoading ? null : onChanged,
      ),
    );
  }
}

class _ProfileInfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _ProfileInfoCard({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              icon,
              color: AppColors.primary,
              size: 24,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w500,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    value,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsOption extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _SettingsOption({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          icon,
          color: AppColors.primary,
        ),
        title: Text(
          title,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        subtitle: Text(
          subtitle,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class _AdminSetPasswordCard extends StatefulWidget {
  final bool isLoading;
  final void Function(String newPassword, bool sendEmail) onSubmit;

  const _AdminSetPasswordCard({
    required this.isLoading,
    required this.onSubmit,
  });

  @override
  State<_AdminSetPasswordCard> createState() => _AdminSetPasswordCardState();
}

class _AdminSetPasswordCardState extends State<_AdminSetPasswordCard> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  bool _obscure = true;
  bool _sendEmail = true;

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Set a new password for this user',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _passwordController,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: 'New Password',
                  prefixIcon: const Icon(Icons.lock_outlined),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                  border: const OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) return 'Enter a password';
                  if (value.length < 8) return 'Must be at least 8 characters';
                  return null;
                },
              ),
              const SizedBox(height: 8),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Send password via email'),
                subtitle: const Text('The user will receive the new password by email'),
                value: _sendEmail,
                onChanged: (v) => setState(() => _sendEmail = v),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: widget.isLoading
                      ? null
                      : () {
                          if (_formKey.currentState?.validate() ?? false) {
                            widget.onSubmit(_passwordController.text, _sendEmail);
                            _passwordController.clear();
                          }
                        },
                  icon: widget.isLoading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save),
                  label: const Text('Set Password'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
