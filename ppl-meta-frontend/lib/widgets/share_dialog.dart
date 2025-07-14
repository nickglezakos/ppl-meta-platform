import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';
import '../core/theme/app_theme.dart';
import '../core/models/api_response.dart';
import '../models/media_models.dart';
import '../services/media_api_client.dart';

/// Share dialog with permission controls and multiple sharing options
class ShareDialog extends StatefulWidget {
  final List<MediaItem> items;
  final MediaCollection? collection;

  const ShareDialog({
    super.key,
    required this.items,
    this.collection,
  });

  @override
  State<ShareDialog> createState() => _ShareDialogState();
}

class _ShareDialogState extends State<ShareDialog>
    with TickerProviderStateMixin {
  final MediaApiClient _apiClient = MediaApiClient();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _messageController = TextEditingController();
  
  late TabController _tabController;
  
  // Share settings
  SharePermission _permission = SharePermission.view;
  DateTime? _expiryDate;
  bool _requirePassword = false;
  String? _password;
  bool _allowDownload = true;
  bool _allowComments = false;
  bool _notifyByEmail = true;
  
  // State
  bool _isGeneratingLink = false;
  bool _isSharingByEmail = false;
  String? _shareLink;
  String? _error;
  
  // Animation
  late AnimationController _successAnimationController;
  late Animation<double> _successAnimation;

  @override
  void initState() {
    super.initState();
    
    _tabController = TabController(length: 3, vsync: this);
    
    _successAnimationController = AnimationController(
      duration: AppDurations.normal,
      vsync: this,
    );
    
    _successAnimation = CurvedAnimation(
      parent: _successAnimationController,
      curve: AppCurves.bounce,
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    _successAnimationController.dispose();
    _emailController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  /// Generate share link
  Future<void> _generateShareLink() async {
    setState(() {
      _isGeneratingLink = true;
      _error = null;
    });

    try {
      final link = await _apiClient.createShareLink(
        itemIds: widget.items.map((item) => item.id).toList(),
        collectionId: widget.collection?.id,
        permission: _permission,
        expiryDate: _expiryDate,
        requirePassword: _requirePassword,
        password: _password,
        allowDownload: _allowDownload,
        allowComments: _allowComments,
      );
      
      setState(() {
        _shareLink = link;
        _isGeneratingLink = false;
      });
      
      _successAnimationController.forward();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isGeneratingLink = false;
      });
    }
  }

  /// Share by email
  Future<void> _shareByEmail() async {
    final emails = _emailController.text
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    
    if (emails.isEmpty) {
      _showError('Please enter at least one email address');
      return;
    }

    setState(() {
      _isSharingByEmail = true;
      _error = null;
    });

    try {
      await _apiClient.shareByEmail(
        itemIds: widget.items.map((item) => item.id).toList(),
        collectionId: widget.collection?.id,
        emails: emails,
        message: _messageController.text.trim(),
        permission: _permission,
        expiryDate: _expiryDate,
        allowDownload: _allowDownload,
        allowComments: _allowComments,
        notifyByEmail: _notifyByEmail,
      );
      
      setState(() {
        _isSharingByEmail = false;
      });
      
      _showSuccess('Successfully shared with ${emails.length} recipients');
      
      // Close dialog after success
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          Navigator.pop(context);
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSharingByEmail = false;
      });
    }
  }

  /// Share using system share sheet
  Future<void> _shareNative() async {
    if (_shareLink == null) {
      await _generateShareLink();
      if (_shareLink == null) return;
    }

    final text = widget.collection != null
        ? 'Check out this collection: ${widget.collection!.name}\n$_shareLink'
        : 'Check out ${widget.items.length} media file${widget.items.length == 1 ? '' : 's'}\n$_shareLink';

    await Share.share(text);
  }

  /// Copy link to clipboard
  void _copyToClipboard() {
    if (_shareLink == null) return;
    
    Clipboard.setData(ClipboardData(text: _shareLink!));
    _showSuccess('Link copied to clipboard');
  }

  /// Show success message
  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.success,
      ),
    );
  }

  /// Show error message
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.error,
      ),
    );
  }

  /// Set expiry date
  Future<void> _setExpiryDate() async {
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: _expiryDate ?? DateTime.now().add(const Duration(days: 7)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );

    if (selectedDate != null) {
      setState(() {
        _expiryDate = selectedDate;
      });
    }
  }

  /// Clear expiry date
  void _clearExpiryDate() {
    setState(() {
      _expiryDate = null;
    });
  }

  /// Show password dialog
  Future<void> _showPasswordDialog() async {
    final password = await showDialog<String>(
      context: context,
      builder: (context) => _PasswordDialog(),
    );

    if (password != null) {
      setState(() {
        _password = password;
        _requirePassword = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: 600,
        height: 700,
        child: Column(
          children: [
            // Header
            _buildHeader(),
            
            // Tab bar
            TabBar(
              controller: _tabController,
              labelColor: AppColors.primary,
              unselectedLabelColor: AppColors.textSecondary,
              indicatorColor: AppColors.primary,
              tabs: const [
                Tab(
                  icon: Icon(Icons.link),
                  text: 'Share Link',
                ),
                Tab(
                  icon: Icon(Icons.email),
                  text: 'Email',
                ),
                Tab(
                  icon: Icon(Icons.settings),
                  text: 'Settings',
                ),
              ],
            ),
            
            // Tab content
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildLinkTab(),
                  _buildEmailTab(),
                  _buildSettingsTab(),
                ],
              ),
            ),
            
            // Error message
            if (_error != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: const BoxDecoration(
                  color: AppColors.error,
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(AppRadius.lg),
                    bottomRight: Radius.circular(AppRadius.lg),
                  ),
                ),
                child: Text(
                  _error!,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.white,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build header
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          Icon(
            widget.collection != null ? Icons.collections : Icons.share,
            color: AppColors.primary,
            size: 28,
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.collection != null
                      ? 'Share Collection'
                      : 'Share Media',
                  style: AppTextStyles.h5,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  widget.collection != null
                      ? widget.collection!.name
                      : '${widget.items.length} item${widget.items.length == 1 ? '' : 's'}',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }

  /// Build share link tab
  Widget _buildLinkTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Generate a shareable link',
            style: AppTextStyles.h6,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Create a secure link that can be shared with anyone',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Generate link button
          if (_shareLink == null)
            ElevatedButton(
              onPressed: _isGeneratingLink ? null : _generateShareLink,
              child: _isGeneratingLink
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Generate Link'),
            ),
          
          // Share link display
          if (_shareLink != null) ...[
            AnimatedBuilder(
              animation: _successAnimation,
              builder: (context, child) {
                return Transform.scale(
                  scale: 1.0 + (_successAnimation.value * 0.1),
                  child: Container(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.1),
                      border: Border.all(color: AppColors.success),
                      borderRadius: BorderRadius.circular(AppRadius.md),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: AppColors.success,
                              size: 20,
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Text(
                              'Link generated successfully',
                              style: AppTextStyles.labelLarge.copyWith(
                                color: AppColors.success,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Container(
                          padding: const EdgeInsets.all(AppSpacing.sm),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceVariant,
                            borderRadius: BorderRadius.circular(AppRadius.sm),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  _shareLink!,
                                  style: AppTextStyles.bodySmall.copyWith(
                                    fontFamily: 'monospace',
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              IconButton(
                                onPressed: _copyToClipboard,
                                icon: const Icon(Icons.copy),
                                tooltip: 'Copy to clipboard',
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            
            const SizedBox(height: AppSpacing.lg),
            
            // Share actions
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _copyToClipboard,
                    icon: const Icon(Icons.copy),
                    label: const Text('Copy Link'),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _shareNative,
                    icon: const Icon(Icons.share),
                    label: const Text('Share'),
                  ),
                ),
              ],
            ),
          ],
          
          const Spacer(),
          
          // Permission summary
          _buildPermissionSummary(),
        ],
      ),
    );
  }

  /// Build email tab
  Widget _buildEmailTab() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Share by email',
            style: AppTextStyles.h6,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Send a secure link directly to recipients',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Email addresses
          TextField(
            controller: _emailController,
            decoration: const InputDecoration(
              labelText: 'Email addresses',
              hintText: 'Enter emails separated by commas',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.email),
            ),
            keyboardType: TextInputType.emailAddress,
            maxLines: 3,
          ),
          
          const SizedBox(height: AppSpacing.md),
          
          // Message
          TextField(
            controller: _messageController,
            decoration: const InputDecoration(
              labelText: 'Message (optional)',
              hintText: 'Add a personal message',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.message),
            ),
            maxLines: 4,
            maxLength: 500,
          ),
          
          const SizedBox(height: AppSpacing.md),
          
          // Email notifications
          SwitchListTile(
            title: const Text('Email notifications'),
            subtitle: const Text('Notify recipients by email'),
            value: _notifyByEmail,
            onChanged: (value) {
              setState(() {
                _notifyByEmail = value;
              });
            },
          ),
          
          const Spacer(),
          
          // Send button
          ElevatedButton(
            onPressed: _isSharingByEmail ? null : _shareByEmail,
            child: _isSharingByEmail
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Send Email'),
          ),
        ],
      ),
    );
  }

  /// Build settings tab
  Widget _buildSettingsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Share settings',
            style: AppTextStyles.h6,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Configure permissions and security',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Permission level
          Text(
            'Permission Level',
            style: AppTextStyles.labelLarge,
          ),
          const SizedBox(height: AppSpacing.sm),
          ...SharePermission.values.map((permission) {
            return RadioListTile<SharePermission>(
              title: Text(_getPermissionTitle(permission)),
              subtitle: Text(_getPermissionDescription(permission)),
              value: permission,
              groupValue: _permission,
              onChanged: (value) {
                setState(() {
                  _permission = value!;
                });
              },
            );
          }),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Expiry date
          Text(
            'Link Expiry',
            style: AppTextStyles.labelLarge,
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _setExpiryDate,
                  child: Text(
                    _expiryDate != null
                        ? 'Expires: ${_expiryDate!.month}/${_expiryDate!.day}/${_expiryDate!.year}'
                        : 'Set expiry date',
                  ),
                ),
              ),
              if (_expiryDate != null) ...[
                const SizedBox(width: AppSpacing.sm),
                IconButton(
                  onPressed: _clearExpiryDate,
                  icon: const Icon(Icons.clear),
                  tooltip: 'Remove expiry',
                ),
              ],
            ],
          ),
          
          const SizedBox(height: AppSpacing.lg),
          
          // Password protection
          SwitchListTile(
            title: const Text('Password protection'),
            subtitle: Text(
              _requirePassword && _password != null
                  ? 'Password set'
                  : 'Require password to access',
            ),
            value: _requirePassword,
            onChanged: (value) {
              if (value) {
                _showPasswordDialog();
              } else {
                setState(() {
                  _requirePassword = false;
                  _password = null;
                });
              }
            },
          ),
          
          // Additional options
          SwitchListTile(
            title: const Text('Allow downloads'),
            subtitle: const Text('Recipients can download files'),
            value: _allowDownload,
            onChanged: (value) {
              setState(() {
                _allowDownload = value;
              });
            },
          ),
          
          SwitchListTile(
            title: const Text('Allow comments'),
            subtitle: const Text('Recipients can leave comments'),
            value: _allowComments,
            onChanged: (value) {
              setState(() {
                _allowComments = value;
              });
            },
          ),
        ],
      ),
    );
  }

  /// Build permission summary
  Widget _buildPermissionSummary() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Current Settings',
            style: AppTextStyles.labelLarge,
          ),
          const SizedBox(height: AppSpacing.sm),
          _PermissionItem(
            icon: Icons.visibility,
            text: _getPermissionTitle(_permission),
          ),
          if (_expiryDate != null)
            _PermissionItem(
              icon: Icons.schedule,
              text: 'Expires ${_expiryDate!.month}/${_expiryDate!.day}/${_expiryDate!.year}',
            ),
          if (_requirePassword)
            const _PermissionItem(
              icon: Icons.lock,
              text: 'Password protected',
            ),
          if (_allowDownload)
            const _PermissionItem(
              icon: Icons.download,
              text: 'Downloads allowed',
            ),
          if (_allowComments)
            const _PermissionItem(
              icon: Icons.comment,
              text: 'Comments allowed',
            ),
        ],
      ),
    );
  }

  /// Get permission title
  String _getPermissionTitle(SharePermission permission) {
    switch (permission) {
      case SharePermission.view:
        return 'View only';
      case SharePermission.comment:
        return 'View and comment';
      case SharePermission.edit:
        return 'View and edit';
    }
  }

  /// Get permission description
  String _getPermissionDescription(SharePermission permission) {
    switch (permission) {
      case SharePermission.view:
        return 'Recipients can only view the shared content';
      case SharePermission.comment:
        return 'Recipients can view and leave comments';
      case SharePermission.edit:
        return 'Recipients can view, comment, and make changes';
    }
  }
}

/// Password dialog
class _PasswordDialog extends StatefulWidget {
  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Set Password'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _passwordController,
            decoration: InputDecoration(
              labelText: 'Password',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() {
                    _obscurePassword = !_obscurePassword;
                  });
                },
                icon: Icon(
                  _obscurePassword ? Icons.visibility : Icons.visibility_off,
                ),
              ),
            ),
            obscureText: _obscurePassword,
          ),
          const SizedBox(height: AppSpacing.md),
          TextField(
            controller: _confirmController,
            decoration: InputDecoration(
              labelText: 'Confirm Password',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() {
                    _obscureConfirm = !_obscureConfirm;
                  });
                },
                icon: Icon(
                  _obscureConfirm ? Icons.visibility : Icons.visibility_off,
                ),
              ),
            ),
            obscureText: _obscureConfirm,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            final password = _passwordController.text;
            final confirm = _confirmController.text;
            
            if (password.isEmpty) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Password cannot be empty'),
                  backgroundColor: AppColors.error,
                ),
              );
              return;
            }
            
            if (password != confirm) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Passwords do not match'),
                  backgroundColor: AppColors.error,
                ),
              );
              return;
            }
            
            Navigator.pop(context, password);
          },
          child: const Text('Set Password'),
        ),
      ],
    );
  }
}

/// Permission item widget
class _PermissionItem extends StatelessWidget {
  final IconData icon;
  final String text;

  const _PermissionItem({
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Row(
        children: [
          Icon(
            icon,
            size: 16,
            color: AppColors.textSecondary,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            text,
            style: AppTextStyles.bodySmall,
          ),
        ],
      ),
    );
  }
}
