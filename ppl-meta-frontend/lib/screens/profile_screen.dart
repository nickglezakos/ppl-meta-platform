import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/providers/auth_provider.dart';
import '../core/api/api_client.dart';
import '../core/theme/app_theme.dart';
import '../core/models/user.dart';
import '../widgets/change_password_dialog.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/authority_status_card.dart';
import '../presentation/pages/developer_settings_page.dart';
import '../presentation/pages/people_counters_page.dart';
import '../presentation/screens/users/role_assign_dialog.dart';

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
  void _showRoleAssignDialog(BuildContext context, User user) async {
    final result = await RoleAssignDialog.show(
      context,
      userId: user.id,
      userEmail: user.email,
      currentRoles: _targetRoles,
    );
    if (result != null) {
      setState(() => _targetRoles = result);
    }
  }

  Future<void> _removeRole(User user, String roleName) async {
    // Safeguard: cannot remove last owner
    if (roleName == 'owner' && _targetRoles.where((r) => r == 'owner').length <= 1) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cannot remove the last owner role'), backgroundColor: Colors.red),
        );
      }
      return;
    }
    try {
      final apiClient = ref.read(apiClientProvider);
      // Need to find role ID — reload user profile after
      await _loadTargetUser();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Use the Assign dialog to remove roles'), backgroundColor: Colors.orange),
      );
      _showRoleAssignDialog(context, user);
    } catch (_) {}
  }

  Color _getRoleColor(String role) {
    switch (role) {
      case 'owner': return Colors.amber.shade800;
      case 'admin': return Colors.deepPurple;
      case 'user': return Colors.blue;
      default: return Colors.teal;
    }
  }

  // All known capabilities for building the toggle list
  static const _allCapabilities = <String>[
    'auth.session.use', 'auth.roles.read', 'auth.roles.create', 'auth.roles.update',
    'auth.roles.delete', 'auth.roles.assign', 'auth.roles.unassign',
    'auth.capabilities.read', 'auth.capabilities.assign', 'auth.capabilities.unassign',
    'auth.capabilities.manage',
    'users.profile.read', 'users.profile.update', 'users.password.change_self',
    'users.password.recover_self', 'users.accounts.read', 'users.accounts.create',
    'users.accounts.update', 'users.accounts.disable', 'users.accounts.delete',
    'cameras.view', 'cameras.manage',
    'cameras:detect', 'cameras:view', 'cameras:connect', 'cameras:disconnect',
    'cameras:stream:start', 'cameras:stream:stop', 'cameras:stream:view',
    'cameras:record:start', 'cameras:sessions:manage', 'cameras:settings:update',
    'cameras:admin', 'cameras:configure',
    'media.view', 'media.manage', 'analytics.view', 'workflows.use',
    'operations.execute', 'system.installation.manage', 'system.licensing.manage',
    'system.recovery.manage', 'vision',
  ];

  String _capabilityNamespace(String cap) {
    if (cap.contains(':')) return cap.split(':').first;
    if (cap.contains('.')) return cap.split('.').first;
    return 'other';
  }

  Widget _buildCapabilityToggleList(BuildContext context, User user) {
    final grouped = <String, List<String>>{};
    for (final cap in _allCapabilities) {
      final ns = _capabilityNamespace(cap);
      grouped.putIfAbsent(ns, () => []).add(cap);
    }
    return Column(
      children: grouped.entries.map((entry) {
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ExpansionTile(
            title: Text(_namespaceLabel(entry.key), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
            subtitle: Text('${entry.value.length} capabilities'),
            initiallyExpanded: entry.key == 'auth' || entry.key == 'users',
            children: entry.value.map((cap) {
              final enabled = _targetCapabilities.contains(cap);
              return ListTile(
                dense: true,
                title: Text(cap, style: TextStyle(fontSize: 13, fontFamily: 'monospace', color: enabled ? null : Colors.grey)),
                trailing: Switch(
                  value: enabled,
                  onChanged: _isTogglingCapability ? null : (v) => _toggleCapability(cap, v),
                ),
              );
            }).toList(),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildCapabilityInfoList(BuildContext context) {
    return Column(
      children: _targetCapabilities.map((cap) {
        return ListTile(
          dense: true,
          leading: const Icon(Icons.check_circle, color: Colors.green, size: 18),
          title: Text(cap, style: const TextStyle(fontSize: 13)),
        );
      }).toList(),
    );
  }

  String _namespaceLabel(String ns) {
    switch (ns) {
      case 'auth': return 'Auth & Session';
      case 'users': return 'User Accounts';
      case 'cameras': return 'Cameras';
      case 'media': return 'Media';
      case 'analytics': return 'Analytics';
      case 'workflows': return 'Workflows';
      case 'operations': return 'Operations';
      case 'system': return 'System';
      case 'vision': return 'Vision';
      default: return ns[0].toUpperCase() + ns.substring(1);
    }
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
            // Roles with assign button and removal
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Roles', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                if (isAdmin)
                  TextButton.icon(
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Assign'),
                    onPressed: () => _showRoleAssignDialog(context, user),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            if (_targetRoles.isNotEmpty)
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: _targetRoles.map((role) {
                  final color = _getRoleColor(role);
                  return Chip(
                    label: Text(role, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13)),
                    backgroundColor: color.withOpacity(0.15),
                    deleteIcon: isAdmin ? const Icon(Icons.close, size: 16) : null,
                    onDeleted: isAdmin ? () => _removeRole(user, role) : null,
                  );
                }).toList(),
              )
            else
              const Text('No roles assigned', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 24),
            // Capabilities grouped by namespace
            Text('Capabilities', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            if (isAdmin)
              _buildCapabilityToggleList(context, user)
            else
              _buildCapabilityInfoList(context),
            const SizedBox(height: 24),
            // Admin: Set Password
            if (isAdmin) ...[
              Text('Set Password', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
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
            const AuthorityStatusCard(showAdminDetails: false),
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
              icon: Icons.groups,
              title: 'People Counters',
              subtitle: 'Automation pipeline & precomputed batches',
              onTap: () {
                if (!user.isAdmin) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Admin role required to manage People Counters'),
                      backgroundColor: Colors.orange,
                    ),
                  );
                  return;
                }
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => const PeopleCountersPage(),
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
              backgroundColor: AppColors.primary.withValues(alpha: 0.1),
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
            GestureDetector(
              onTap: user.emailVerified
                  ? null
                  : () => _sendVerificationEmail(),
              child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: user.emailVerified
                    ? Colors.green.withValues(alpha: 0.1)
                    : Colors.orange.withValues(alpha: 0.1),
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
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _sendVerificationEmail() async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final resp = await apiClient.post('/api/v1/users/send-verification-email');
      final msg = (resp.data as Map<String, dynamic>?)?['detail']?.toString() ?? 'Verification email sent.';
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
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
