import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/workflow_action_model.dart';
import '../models/user_action_model.dart';
import '../models/signage_models.dart';
import '../services/workflow_action_service.dart';
import '../services/user_action_service.dart';
import '../services/auth_service.dart';
import '../services/signage_api_client.dart';
import '../services/discovery_service_client.dart';
import '../core/api/api_client.dart';
import '../core/theme/theme_kit.dart';
import '../presentation/widgets/common/ux_breakpoints.dart';
import '../presentation/widgets/common/content_pane.dart';
import '../presentation/widgets/common/unified_toggle.dart';
import '../core/config/app_config.dart';
import '../screens/communication_logs_screen.dart';
import '../screens/communication_logs_screen.dart';

/// Actions tab with User Actions (CRUD-able) and System Workflows (read-only)
class ActionsTab extends StatefulWidget {
  const ActionsTab({Key? key}) : super(key: key);

  @override
  State<ActionsTab> createState() => ActionsTabState();
}

class ActionsTabState extends State<ActionsTab> {
  bool _isLoadingUser = false;
  bool _isLoadingSystem = false;
  String? _errorMessageUser;
  String? _errorMessageSystem;
  
  List<UserActionModel> _userActions = [];
  List<WorkflowAction> _systemWorkflows = [];
  
  final UserActionService _userActionService = UserActionService();
  final WorkflowActionService _workflowService = WorkflowActionService();
  final AuthService _authService = AuthService();
  
  bool? _filterIsActiveUser;
  bool? _filterIsActiveSystem;

  // Phase 4 unified UX
  UserActionModel? _selectedAction;
  final TextEditingController _searchControllerActions = TextEditingController();
  String _searchQueryActions = '';
  bool _editingAction = false;

  @override
  void dispose() {
    _searchControllerActions.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    // Get auth token if available
    final token = await _authService.getStoredToken();
    if (token != null) {
      _userActionService.setAuthToken(token);
      _workflowService.setAuthToken(token);
    }
    // Load only user actions - system workflows temporarily disabled
    await _loadUserActions();
    // await Future.wait([_loadUserActions(), _loadSystemWorkflows()]);
  }

  Future<void> _loadUserActions() async {
    if (!mounted) return;
    setState(() {
      _isLoadingUser = true;
      _errorMessageUser = null;
    });

    try {
      final response = await _userActionService.fetchUserActions(
        isActive: _filterIsActiveUser,
      );

      if (!mounted) return;
      setState(() {
        _userActions = response.actions;
        _isLoadingUser = false;
        // Default-select the first action so the right settings pane is
        // populated on load (unless the user already picked one).
        _selectedAction ??=
            _userActions.isNotEmpty ? _userActions.first : null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessageUser = 'Failed to load user actions: $e';
        _isLoadingUser = false;
      });
    }
  }

  Future<void> _loadSystemWorkflows() async {
    if (!mounted) return;
    setState(() {
      _isLoadingSystem = true;
      _errorMessageSystem = null;
    });

    try {
      final workflows = await _workflowService.getWorkflows(
        isActive: _filterIsActiveSystem,
      );

      if (!mounted) return;
      setState(() {
        _systemWorkflows = workflows;
        _isLoadingSystem = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessageSystem = 'Failed to load system workflows: $e';
        _isLoadingSystem = false;
      });
    }
  }

  Future<void> _deleteUserAction(UserActionModel action) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete User Action'),
        content: Text('Are you sure you want to delete "${action.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _userActionService.deleteUserAction(action.uuid);
        await _loadUserActions();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('User action deleted successfully'),
              backgroundColor: AppColors.success,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to delete: $e'),
              backgroundColor: AppColors.error,
            ),
          );
        }
      }
    }
  }

  Future<bool> _unifiedToggleUserAction(UserActionModel action) async {
    try {
      await _userActionService.toggleUserAction(action.uuid);
      await _loadUserActions();
      return true;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to toggle: $e')),
        );
      }
      return false;
    }
  }

  /// Public method to show the create/edit user action dialog from parent.
  /// Used by TriggersScreen's navigation bar + icon button.
  void showCreateEditDialog({UserActionModel? action}) {
    _showCreateEditUserActionDialog(action: action);
  }

  void _showCreateEditUserActionDialog({UserActionModel? action}) {
    showDialog(
      context: context,
      builder: (context) => _UserActionDialog(
        action: action,
        onSave: () async {
          Navigator.pop(context);
          await _loadUserActions();
        },
        userActionService: _userActionService,
        authService: _authService,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final master = Column(
      children: [
        // Shared search + status filter action bar
        ListableItemsActionBar(
          searchController: _searchControllerActions,
          onSearchChanged: (value) => setState(() => _searchQueryActions = value),
          filterContent: Center(child: _buildFilterToggles()),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // USER ACTIONS SECTION
                _buildUserActionsSection(),

                const SizedBox(height: 32),

                // SYSTEM WORKFLOWS SECTION
                _buildSystemWorkflowsSection(),
              ],
            ),
          ),
        ),
      ],
    );
    if (isWide(context)) {
      return Row(
        children: [
          SizedBox(width: kMasterPaneWidth, child: master),
          const VerticalDivider(width: 1),
          const SizedBox(width: 4),
          Expanded(child: _buildActionsDetailPane()),
        ],
      );
    }
    return master;
  }

  Widget _buildUserActionsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Content
        if (_isLoadingUser)
          const Center(child: Padding(
            padding: EdgeInsets.all(32),
            child: CircularProgressIndicator(),
          )),
        
        if (_errorMessageUser != null)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.3),
              border: Border.all(color: AppColors.error),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Row(
              children: [
                const Icon(Icons.error, color: AppColors.error),
                const SizedBox(width: 8),
                Expanded(child: Text(_errorMessageUser!, style: const TextStyle(color: AppColors.error))),
                TextButton(
                  onPressed: _loadUserActions,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingUser && _errorMessageUser == null && _userActions.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            alignment: Alignment.center,
            child: Column(
              children: [
                Icon(Icons.add_circle_outline, size: 64, color: AppColors.gray600),
                const SizedBox(height: 16),
                Text(
                  'No user actions yet',
                  style: TextStyle(fontSize: 18, color: AppColors.gray500),
                ),
                const SizedBox(height: 8),
                Text(
                  'Create your first custom action to get started',
                  style: TextStyle(fontSize: 14, color: AppColors.gray600),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingUser && _errorMessageUser == null && _userActions.isNotEmpty)
          _buildUserActionsCards(),
      ],
    );
  }

  Widget _buildSystemWorkflowsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Content
        if (_isLoadingSystem)
          const Center(child: Padding(
            padding: EdgeInsets.all(32),
            child: CircularProgressIndicator(),
          )),
        
        if (_errorMessageSystem != null)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.3),
              border: Border.all(color: AppColors.error),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Row(
              children: [
                const Icon(Icons.error, color: AppColors.error),
                const SizedBox(width: 8),
                Expanded(child: Text(_errorMessageSystem!, style: const TextStyle(color: AppColors.error))),
                TextButton(
                  onPressed: _loadSystemWorkflows,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingSystem && _errorMessageSystem == null && _systemWorkflows.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            alignment: Alignment.center,
            child: Column(
              children: [
                Icon(Icons.inbox_outlined, size: 64, color: AppColors.gray600),
                const SizedBox(height: 16),
                Text(
                  'No system workflows found',
                  style: TextStyle(fontSize: 18, color: AppColors.gray500),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingSystem && _errorMessageSystem == null && _systemWorkflows.isNotEmpty)
          _buildSystemWorkflowsCards(),
      ],
    );
  }

  // ─────────────────────────────────────────────────
  // User action cards
  // ─────────────────────────────────────────────────

  /// Status filter toggles (All / Active / Inactive) for the shared action bar.
  Widget _buildFilterToggles() {
    const values = <bool?>[null, true, false];
    const labels = <String>['All', 'Active', 'Inactive'];

    return ToggleButtons(
      constraints: const BoxConstraints(minHeight: 32),
      borderRadius: BorderRadius.circular(AppRadius.sm),
      isSelected: [for (final v in values) v == _filterIsActiveUser],
      onPressed: (index) {
        setState(() => _filterIsActiveUser = values[index]);
        _loadUserActions();
      },
      selectedColor: AppColors.accent,
      fillColor: AppColors.accent.withValues(alpha: 0.1),
      borderColor: AppColors.gray700,
      selectedBorderColor: AppColors.accent.withValues(alpha: 0.4),
      children: [
        for (final label in labels)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  label == 'All' ? Icons.dashboard_outlined : AppIcons.active,
                  size: AppIconSize.sm,
                ),
                const SizedBox(width: AppSpacing.xs),
                Text(label, style: AppTextStyles.caption),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildActionsDetailPane() {
    final action = _selectedAction;
    if (action == null) {
      return ContentPane(
        title: 'Action',
        subtitle: 'Select a user action to inspect it',
        child: const Center(
          child: Text('Select a user action from the list'),
        ),
      );
    }
    return ContentPane(
      title: action.name,
      subtitle: action.actionTypeDisplay,
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Status',
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    UnifiedToggle(
                      value: action.isActive,
                      label: action.isActive ? 'Active' : 'Inactive',
                      onToggle: (next) => _unifiedToggleUserAction(action),
                    ),
                    const SizedBox(height: 12),
                    _actionsDetailRow('Type', action.actionTypeDisplay),
                    if (action.description != null &&
                        action.description!.isNotEmpty)
                      _actionsDetailRow('Description', action.description!),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => setState(() => _editingAction = true),
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Edit'),
                ),
                OutlinedButton.icon(
                  onPressed: () => _deleteUserAction(action),
                  icon: const Icon(Icons.delete_outline),
                  style: OutlinedButton.styleFrom(foregroundColor: AppColors.error),
                  label: const Text('Delete'),
                ),
              ],
            ),
            if (_editingAction) ...[
              const SizedBox(height: 12),
              _UserActionDialog(
                action: action,
                onSave: () async {
                  await _loadUserActions();
                  if (!mounted) return;
                  setState(() {
                    if (action.uuid != null) {
                      _selectedAction = _userActions.firstWhere(
                        (a) => a.uuid == action.uuid,
                        orElse: () => action,
                      );
                    }
                    _editingAction = false;
                  });
                },
                userActionService: _userActionService,
                authService: _authService,
                embedded: true,
                onCancel: () => setState(() => _editingAction = false),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _actionsDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: AppColors.gray500),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }

  Widget _buildUserActionsCards() {
    return LayoutBuilder(builder: (context, constraints) {
      final crossAxisCount = constraints.maxWidth > 1200
          ? 3
          : constraints.maxWidth > 700
              ? 2
              : 1;
      final cardWidth = (constraints.maxWidth - (crossAxisCount - 1) * 12) / crossAxisCount;
      final q = _searchQueryActions.trim().toLowerCase();
      final visible = q.isEmpty
          ? _userActions
          : _userActions
                .where((a) => (a.name ?? '').toLowerCase().contains(q))
                .toList();

      if (crossAxisCount == 1) {
        return ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: visible.length,
          itemBuilder: (context, index) => SizedBox(
            width: cardWidth,
            child: _buildUserActionCard(visible[index]),
          ),
        );
      }

      return SingleChildScrollView(
        physics: const NeverScrollableScrollPhysics(),
        child: Wrap(
          spacing: 12,
          runSpacing: 12,
          children: visible.map((action) => SizedBox(
            width: cardWidth,
            child: _buildUserActionCard(action),
          )).toList(),
        ),
      );
    });
  }

  Widget _buildUserActionCard(UserActionModel action) {
    final typeColor = action.actionTypeColor;
    final typeIcon = action.actionTypeIcon;
    final configSummary = _actionConfigSummary(action);

    return ListableCard(
      isSelected: _selectedAction?.uuid == action.uuid,
      onTap: () {
        if (isWide(context)) {
          setState(() {
            _selectedAction = action;
            _editingAction = false;
          });
        } else {
          _showCreateEditUserActionDialog(action: action);
        }
      },
      leadingIcon: Container(
        width: 48, height: 48,
        decoration: BoxDecoration(
          color: AppColors.secondary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Icon(typeIcon, color: AppColors.secondary, size: AppIconSize.xl),
      ),
      title: Text(action.name, style: AppTextStyles.bodyLarge.copyWith(fontWeight: FontWeight.normal),
        maxLines: 1, overflow: TextOverflow.ellipsis),
      titleBadge: Container(
        padding: EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: AppColors.secondary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppRadius.xs),
          border: Border.all(color: AppColors.secondary.withValues(alpha: 0.3), width: 1),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(typeIcon, size: 12, color: AppColors.secondary),
          SizedBox(width: AppSpacing.xs),
          Flexible(child: Text(action.actionTypeDisplay, style: AppTextStyles.caption.copyWith(color: AppColors.secondary, fontWeight: FontWeight.w500),
            overflow: TextOverflow.ellipsis, maxLines: 1)),
        ]),
      ),
      statusBadge: Container(
        padding: EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: AppSpacing.xs),
        decoration: BoxDecoration(
          color: action.isActive ? AppColors.success.withValues(alpha: 0.1) : AppColors.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppRadius.xs),
          border: Border.all(color: action.isActive ? AppColors.success.withValues(alpha: 0.3) : AppColors.error.withValues(alpha: 0.3), width: 1),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(action.isActive ? Icons.check_circle : Icons.remove_circle, size: 10, color: action.isActive ? AppColors.success : AppColors.error),
          SizedBox(width: AppSpacing.xs),
          Flexible(child: Text(action.isActive ? 'Active' : 'Inactive', style: AppTextStyles.caption.copyWith(color: action.isActive ? AppColors.success : AppColors.error, fontWeight: FontWeight.w500),
            overflow: TextOverflow.ellipsis)),
        ]),
      ),
      body: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if ((action.description ?? '').isNotEmpty)
          _actionInfoRow(icon: Icons.notes_outlined, text: action.description!),
        if (configSummary != null) ...[
          SizedBox(height: AppSpacing.xs),
          _actionInfoRow(icon: Icons.tune_outlined, text: configSummary, color: AppColors.textTertiary),
        ],
      ]),
    );
  }

  /// Returns a short human-readable summary of the action config, or null.
  String? _actionConfigSummary(UserActionModel action) {
    if (action.actionConfig == null || action.actionConfig!.isEmpty) return null;
    try {
      final cfg = jsonDecode(action.actionConfig!) as Map<String, dynamic>;
      switch (action.actionType) {
        case 'alert':
          final msg = cfg['message']?.toString() ?? '';
          return msg.isEmpty ? null : msg;
        case 'email':
          final to = cfg['to']?.toString() ?? '';
          return to.isEmpty ? null : 'To: $to';
        case 'webhook':
          final url = cfg['url']?.toString() ?? '';
          return url.isEmpty ? null : url;
        case 'log':
          final msg = cfg['message']?.toString() ?? '';
          final level = cfg['level']?.toString() ?? cfg['severity']?.toString() ?? '';
          if (msg.isEmpty) return null;
          return level.isEmpty ? msg : '[$level] $msg';
        case 'digital_signage':
          final count = (cfg['device_ids'] as List?)?.length ?? 0;
          return '$count device${count == 1 ? '' : 's'}';
        case 'messaging_app':
          final platform = cfg['platform']?.toString() ?? '';
          return platform.isEmpty ? null : platform[0].toUpperCase() + platform.substring(1);
        default:
          return null;
      }
    } catch (_) {
      return null;
    }
  }

  Widget _actionInfoRow({
    required IconData icon,
    required String text,
    Color? color,
  }) {
    return AppInfoRowStyle.build(icon: icon, text: text, color: color);
  }

  // ─────────────────────────────────────────────────
  // System workflow cards (read-only)
  // ─────────────────────────────────────────────────

  Widget _buildSystemWorkflowsCards() {
    return LayoutBuilder(builder: (context, constraints) {
      final crossAxisCount = constraints.maxWidth > 1200
          ? 3
          : constraints.maxWidth > 700
              ? 2
              : 1;
      final cardWidth = (constraints.maxWidth - (crossAxisCount - 1) * 12) / crossAxisCount;

      if (crossAxisCount == 1) {
        return ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _systemWorkflows.length,
          itemBuilder: (context, index) => SizedBox(
            width: cardWidth,
            child: _buildSystemWorkflowCard(_systemWorkflows[index]),
          ),
        );
      }

      return SingleChildScrollView(
        physics: const NeverScrollableScrollPhysics(),
        child: Wrap(
          spacing: 12,
          runSpacing: 12,
          children: _systemWorkflows.map((workflow) => SizedBox(
            width: cardWidth,
            child: _buildSystemWorkflowCard(workflow),
          )).toList(),
        ),
      );
    });
  }

  Widget _buildSystemWorkflowCard(WorkflowAction workflow) {
    const typeColor = AppColors.gray500;
    return Card(
      color: AppColors.gray900,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(color: AppColors.gray700, width: 1),
      ),
      child: Padding(
        padding: AppSpacing.cardInset,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ──────────────────────────────
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: AppColors.gray500.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(AppRadius.chip),
                  ),
                  child: const Icon(Icons.settings_outlined,
                      color: typeColor, size: 16),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    workflow.name,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: AppColors.white,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 4),
                  decoration: BoxDecoration(
                    color: workflow.isActive
                        ? AppColors.success.withValues(alpha: 0.14)
                        : AppColors.error.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                  ),
                  child: Text(
                    workflow.isActive ? 'Active' : 'Inactive',
                    style: TextStyle(
                      color: workflow.isActive
                          ? AppColors.success
                          : AppColors.error,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),

            // Type pill
            Container(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.gray500.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(AppRadius.chipBadge),
              ),
              child: Text(
                workflow.workflowType.replaceAll('_', ' ').toUpperCase(),
                style: TextStyle(
                    color: AppColors.gray400,
                    fontSize: 10,
                    fontWeight: FontWeight.w600),
              ),
            ),

            const SizedBox(height: AppSpacing.sm),
            const Divider(height: 1, thickness: 1),
            const SizedBox(height: AppSpacing.sm),

            // ── Body ────────────────────────────────
            Expanded(
              child: Text(
                workflow.description,
                style:
                    TextStyle(fontSize: 11.5, color: AppColors.gray400),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),

            // Read-only label in footer
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Read-only',
                style: TextStyle(
                    fontSize: 10,
                    color: AppColors.gray600,
                    fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ),
      ),
    );
  }



  // _buildSystemWorkflowsCardList removed — superseded by _buildSystemWorkflowsCards()
  // ignore: unused_element
  Widget _buildSystemWorkflowsCardList_REMOVED() {
    return Column(
      children: _systemWorkflows.map((workflow) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: AppColors.gray900,
            border: Border.all(color: AppColors.gray700),
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header: name + status badge
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        workflow.name,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: workflow.isActive ? AppColors.success : AppColors.gray800,
                        border: Border.all(
                          color: workflow.isActive ? AppColors.success : AppColors.gray600,
                        ),
                        borderRadius: BorderRadius.circular(AppRadius.chipBadge),
                      ),
                      child: Text(
                        workflow.isActive ? 'Active' : 'Inactive',
                        style: TextStyle(
                          color: workflow.isActive ? AppColors.success : AppColors.gray400,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                // Detail rows
                _buildDetailRow('Description', workflow.description ?? '-'),
                _buildDetailRow('Type', workflow.workflowType.replaceAll('_', ' ').toUpperCase()),
                _buildDetailRow('Created', workflow.createdAt ?? '-'),
                const SizedBox(height: 16),
                // Disabled action buttons (read-only)
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      onPressed: null, // Disabled for system workflows
                      icon: const Icon(Icons.edit, size: 16),
                      label: const Text('Edit'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.gray700,
                        side: BorderSide(color: AppColors.gray700),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton.icon(
                      onPressed: null, // Disabled for system workflows
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.gray700,
                        side: BorderSide(color: AppColors.gray700),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: TextStyle(
                color: AppColors.gray400,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: AppColors.white),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}

/// Dialog for creating/editing user actions
class _UserActionDialog extends StatefulWidget {
  final UserActionModel? action;
  final Function() onSave;
  final UserActionService userActionService;
  final AuthService authService;

  /// When false (default) the editor renders as a modal AlertDialog; when true
  /// it renders inline (embedded in the settings pane) without a dialog route.
  final bool embedded;

  /// Called instead of popping the route when [embedded] is true.
  final VoidCallback? onCancel;

  const _UserActionDialog({
    this.action,
    required this.onSave,
    required this.userActionService,
    required this.authService,
    this.embedded = false,
    this.onCancel,
  });

  @override
  State<_UserActionDialog> createState() => _UserActionDialogState();
}

class _UserActionDialogState extends State<_UserActionDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  late TextEditingController _configController;
  late String _selectedActionType;
  late bool _isActive;
  bool _isSaving = false;
  
  // Digital Signage specific fields
  List<SignageDevice> _availableDevices = [];
  List<VideoList> _availablePlaylists = [];
  List<String> _selectedDeviceIds = [];
  String? _selectedPlaylistId;
  String _transitionMode = 'immediate';
  int _fadeDuration = 1000;
  bool _isLoadingSignageData = false;
  
  // Email action specific fields
  late TextEditingController _emailToController;
  late TextEditingController _emailCcController;
  late TextEditingController _emailSubjectController;
  late TextEditingController _emailBodyController;
  
  // Webhook action specific fields
  late TextEditingController _webhookUrlController;
  String _webhookMethod = 'POST';
  late TextEditingController _webhookHeadersController;
  late TextEditingController _webhookPayloadController;
  
  // Log action specific fields
  late TextEditingController _logMessageController;
  String _logLevel = 'info';
  
  // Alert action specific fields
  late TextEditingController _alertMessageController;
  String _alertSeverity = 'warning';
  int _alertDuration = 30;

  // Messaging app action specific fields
  late TextEditingController _messagingWebhookUrlController;
  late TextEditingController _messagingMessageController;
  late TextEditingController _messagingTitleController;
  late TextEditingController _messagingMentionController;
  String _messagingPlatform = 'slack';

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.action?.name ?? '');
    _descriptionController = TextEditingController(text: widget.action?.description ?? '');
    _configController = TextEditingController(text: widget.action?.actionConfig ?? '');
    _selectedActionType = widget.action?.actionType ?? 'alert';
    _isActive = widget.action?.isActive ?? true;
    
    // Initialize email fields
    _emailToController = TextEditingController();
    _emailCcController = TextEditingController();
    _emailSubjectController = TextEditingController();
    _emailBodyController = TextEditingController();
    
    // Initialize webhook fields
    _webhookUrlController = TextEditingController();
    _webhookHeadersController = TextEditingController();
    _webhookPayloadController = TextEditingController();
    
    // Initialize log fields
    _logMessageController = TextEditingController();
    
    // Initialize alert fields
    _alertMessageController = TextEditingController();
    
    // Initialize messaging app fields
    _messagingWebhookUrlController = TextEditingController();
    _messagingMessageController = TextEditingController();
    _messagingTitleController = TextEditingController();
    _messagingMentionController = TextEditingController();
    
    // Parse existing config if editing
    if (widget.action?.actionConfig != null) {
      try {
        final config = jsonDecode(widget.action!.actionConfig!);
        
        if (widget.action!.actionType == 'digital_signage') {
          _selectedDeviceIds = List<String>.from(config['device_ids'] ?? []);
          _selectedPlaylistId = config['playlist_id'];
          _transitionMode = config['transition_mode'] ?? 'immediate';
          _fadeDuration = config['fade_duration_ms'] ?? 1000;
        } else if (widget.action!.actionType == 'email') {
          _emailToController.text = config['to'] ?? '';
          _emailCcController.text = (config['cc'] as List<dynamic>?)?.join(', ') ?? '';
          _emailSubjectController.text = config['subject'] ?? '';
          _emailBodyController.text = config['body'] ?? '';
        } else if (widget.action!.actionType == 'webhook') {
          _webhookUrlController.text = config['url'] ?? '';
          _webhookMethod = config['method'] ?? 'POST';
          _webhookHeadersController.text = config['headers'] != null 
              ? jsonEncode(config['headers']) 
              : '';
          _webhookPayloadController.text = config['payload'] != null 
              ? jsonEncode(config['payload']) 
              : '';
        } else if (widget.action!.actionType == 'log') {
          _logMessageController.text = config['message'] ?? '';
          _logLevel = config['level'] ?? 'info';
        } else if (widget.action!.actionType == 'alert') {
          _alertMessageController.text = config['message'] ?? '';
          _alertSeverity = config['severity'] ?? 'warning';
          _alertDuration = config['duration_seconds'] ?? 30;
        } else if (widget.action!.actionType == 'messaging_app') {
          _messagingPlatform = config['platform'] ?? 'slack';
          _messagingWebhookUrlController.text = config['webhook_url'] ?? '';
          _messagingMessageController.text = config['message_template'] ?? '';
          _messagingTitleController.text = config['title'] ?? '';
          _messagingMentionController.text = config['mention'] ?? '';
        }
      } catch (e) {
        print('Error parsing action config: $e');
      }
    }
    
    // Load signage data if action type is digital_signage
    if (_selectedActionType == 'digital_signage') {
      _loadSignageData();
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _configController.dispose();
    _emailToController.dispose();
    _emailCcController.dispose();
    _emailSubjectController.dispose();
    _emailBodyController.dispose();
    _webhookUrlController.dispose();
    _webhookHeadersController.dispose();
    _webhookPayloadController.dispose();
    _logMessageController.dispose();
    _alertMessageController.dispose();
    _messagingWebhookUrlController.dispose();
    _messagingMessageController.dispose();
    _messagingTitleController.dispose();
    _messagingMentionController.dispose();
    super.dispose();
  }

  Future<void> _loadSignageData() async {
    setState(() => _isLoadingSignageData = true);
    
    try {
      // Get auth token and create authenticated client
      final token = await widget.authService.getStoredToken();
      final apiClient = ApiClient(AppConfig.instance);
      if (token != null) {
        apiClient.setAuthToken(token);
      }
      
      final discoveryClient = DiscoveryServiceClient();
      final signageClient = SignageApiClient(apiClient, discoveryClient);
      
      // Load devices and playlists in parallel
      final results = await Future.wait([
        signageClient.getSignageDevices(),
        signageClient.getVideoLists(limit: 100),
      ]);
      
      setState(() {
        _availableDevices = results[0] as List<SignageDevice>;
        _availablePlaylists = (results[1] as VideoListsResponse).results;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load signage data: $e'),
            backgroundColor: AppColors.warning,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoadingSignageData = false);
      }
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSaving = true);

    try {
      String? actionConfig;
      
      // Build config based on action type
      if (_selectedActionType == 'digital_signage') {
        // Validate digital signage config
        if (_selectedDeviceIds.isEmpty) {
          throw Exception('Please select at least one device');
        }
        if (_selectedPlaylistId == null || _selectedPlaylistId!.isEmpty) {
          throw Exception('Please select a playlist');
        }
        
        // Build digital signage config JSON
        actionConfig = jsonEncode({
          'device_ids': _selectedDeviceIds,
          'playlist_id': _selectedPlaylistId,
          'transition_mode': _transitionMode,
          'fade_duration_ms': _fadeDuration,
        });
      } else if (_selectedActionType == 'email') {
        // Validate email config
        if (_emailToController.text.isEmpty) {
          throw Exception('Email recipient is required');
        }
        if (_emailSubjectController.text.isEmpty) {
          throw Exception('Email subject is required');
        }
        
        // Build email config JSON
        final emailConfig = <String, dynamic>{
          'to': _emailToController.text,
          'subject': _emailSubjectController.text,
          'body': _emailBodyController.text,
        };
        if (_emailCcController.text.isNotEmpty) {
          emailConfig['cc'] = _emailCcController.text
              .split(',')
              .map((e) => e.trim())
              .where((e) => e.isNotEmpty)
              .toList();
        }
        actionConfig = jsonEncode(emailConfig);
      } else if (_selectedActionType == 'webhook') {
        // Validate webhook config
        if (_webhookUrlController.text.isEmpty) {
          throw Exception('Webhook URL is required');
        }
        
        // Build webhook config JSON
        final webhookConfig = <String, dynamic>{
          'url': _webhookUrlController.text,
          'method': _webhookMethod,
        };
        
        // Parse headers if provided
        if (_webhookHeadersController.text.isNotEmpty) {
          try {
            webhookConfig['headers'] = jsonDecode(_webhookHeadersController.text);
          } catch (e) {
            throw Exception('Invalid JSON in headers field');
          }
        }
        
        // Parse payload if provided
        if (_webhookPayloadController.text.isNotEmpty) {
          try {
            webhookConfig['payload'] = jsonDecode(_webhookPayloadController.text);
          } catch (e) {
            throw Exception('Invalid JSON in payload field');
          }
        }
        
        actionConfig = jsonEncode(webhookConfig);
      } else if (_selectedActionType == 'log') {
        // Validate log config
        if (_logMessageController.text.isEmpty) {
          throw Exception('Log message is required');
        }
        
        // Build log config JSON
        actionConfig = jsonEncode({
          'message': _logMessageController.text,
          'level': _logLevel,
        });
      } else if (_selectedActionType == 'alert') {
        // Validate alert config
        if (_alertMessageController.text.isEmpty) {
          throw Exception('Alert message is required');
        }
        
        // Build alert config JSON
        actionConfig = jsonEncode({
          'message': _alertMessageController.text,
          'severity': _alertSeverity,
          'duration_seconds': _alertDuration,
        });
      } else if (_selectedActionType == 'messaging_app') {
        if (_messagingWebhookUrlController.text.isEmpty) {
          throw Exception('Webhook URL is required');
        }
        if (_messagingMessageController.text.isEmpty) {
          throw Exception('Message template is required');
        }

        final messagingConfig = <String, dynamic>{
          'platform': _messagingPlatform,
          'webhook_url': _messagingWebhookUrlController.text,
          'message_template': _messagingMessageController.text,
        };
        if (_messagingTitleController.text.isNotEmpty) {
          messagingConfig['title'] = _messagingTitleController.text;
        }
        if (_messagingPlatform == 'slack' && _messagingMentionController.text.isNotEmpty) {
          messagingConfig['mention'] = _messagingMentionController.text;
        }
        actionConfig = jsonEncode(messagingConfig);
      } else {
        // Use the raw config controller for other action types
        actionConfig = _configController.text.isEmpty ? null : _configController.text;
      }
      
      final request = UserActionCreateRequest(
        name: _nameController.text,
        description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
        actionType: _selectedActionType,
        actionConfig: actionConfig,
        isActive: _isActive,
      );

      if (widget.action == null) {
        await widget.userActionService.createUserAction(request);
      } else {
        await widget.userActionService.updateUserAction(widget.action!.uuid, request);
      }

      widget.onSave();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Widget _buildDigitalSignageConfig() {
    if (_isLoadingSignageData) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Device selection
        Text(
          'Target Devices *',
          style: TextStyle(
            fontSize: 12,
            color: AppColors.gray400,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.gray700),
            borderRadius: BorderRadius.circular(AppRadius.chipBadge),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_availableDevices.isEmpty && _selectedDeviceIds.isEmpty)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'No devices discovered from signage service',
                      style: TextStyle(color: AppColors.warning, fontSize: 14),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Make sure signage devices are running and registered with discovery service',
                      style: TextStyle(color: AppColors.gray500, fontSize: 12),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      onPressed: _loadSignageData,
                      icon: const Icon(Icons.refresh, size: 16),
                      label: const Text('Retry'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                    ),
                  ],
                )
              else ...[
                // Show available devices
                ..._availableDevices.map((device) {
                  final isSelected = _selectedDeviceIds.contains(device.id);
                  return CheckboxListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(device.name),
                    subtitle: Text(
                      '${device.host}:${device.port} - ${device.isOnline ? "Online" : "Offline"}',
                      style: TextStyle(
                        color: device.isOnline ? AppColors.success : AppColors.error,
                        fontSize: 12,
                      ),
                    ),
                    value: isSelected,
                    onChanged: (selected) {
                      setState(() {
                        if (selected == true) {
                          _selectedDeviceIds.add(device.id);
                        } else {
                          _selectedDeviceIds.remove(device.id);
                        }
                      });
                    },
                  );
                }).toList(),
                // Show previously selected devices that are not in available list (offline/disconnected)
                ..._selectedDeviceIds.where((id) => !_availableDevices.any((d) => d.id == id)).map((deviceId) {
                  return CheckboxListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text('Device: $deviceId'),
                    subtitle: Text(
                      'Currently unavailable (offline or removed)',
                      style: TextStyle(
                        color: AppColors.warning,
                        fontSize: 12,
                      ),
                    ),
                    value: true,
                    onChanged: (selected) {
                      setState(() {
                        if (selected == false) {
                          _selectedDeviceIds.remove(deviceId);
                        }
                      });
                    },
                  );
                }).toList(),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        
        // Playlist selection
        DropdownButtonFormField<String>(
          value: _availablePlaylists.any((p) => p.id == _selectedPlaylistId)
              ? _selectedPlaylistId
              : null,
          decoration: const InputDecoration(
            labelText: 'Playlist *',
            hintText: 'Select a playlist',
          ),
          items: _availablePlaylists.map((playlist) {
            return DropdownMenuItem(
              value: playlist.id,
              child: Text('${playlist.name} (${playlist.videoCount ?? 0} videos)'),
            );
          }).toList(),
          onChanged: (value) => setState(() => _selectedPlaylistId = value),
          validator: (value) => value == null ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        
        // Transition mode
        DropdownButtonFormField<String>(
          value: _transitionMode,
          decoration: const InputDecoration(
            labelText: 'Transition Mode',
          ),
          items: const [
            DropdownMenuItem(value: 'immediate', child: Text('Immediate')),
            DropdownMenuItem(value: 'after_current', child: Text('After Current Video')),
            DropdownMenuItem(value: 'fade', child: Text('Fade Transition')),
          ],
          onChanged: (value) => setState(() => _transitionMode = value!),
        ),
        const SizedBox(height: 16),
        
        // Fade duration (only show if fade mode)
        if (_transitionMode == 'fade')
          TextFormField(
            initialValue: _fadeDuration.toString(),
            decoration: const InputDecoration(
              labelText: 'Fade Duration (ms)',
              hintText: '1000',
            ),
            keyboardType: TextInputType.number,
            onChanged: (value) {
              final parsed = int.tryParse(value);
              if (parsed != null) {
                _fadeDuration = parsed;
              }
            },
          ),
      ],
    );
  }
  
  Widget _buildEmailConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _emailToController,
          decoration: const InputDecoration(
            labelText: 'Recipient Email *',
            hintText: 'user@example.com',
            prefixIcon: Icon(Icons.email),
          ),
          keyboardType: TextInputType.emailAddress,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _emailCcController,
          decoration: const InputDecoration(
            labelText: 'CC (Optional)',
            hintText: 'user1@example.com, user2@example.com',
            prefixIcon: Icon(Icons.people),
            helperText: 'Separate multiple emails with commas',
          ),
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _emailSubjectController,
          decoration: const InputDecoration(
            labelText: 'Subject *',
            hintText: 'Alert: *{trigger_name}* - {match_reason}',
            helperText: 'Variables: {trigger_name}, {reason}, {match_reason}, {matched_member_uuid}, {matched_member_name}, {group_member_number}, {similarity_score}',
          ),
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _emailBodyController,
          decoration: const InputDecoration(
            labelText: 'Email Body',
            hintText: 'Trigger {trigger_name} was fired at {timestamp}',
            alignLabelWithHint: true,
          ),
          maxLines: 5,
        ),
      ],
    );
  }
  
  Widget _buildWebhookConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _webhookUrlController,
          decoration: const InputDecoration(
            labelText: 'Webhook URL *',
            hintText: 'https://your-server.com/api/webhook',
            prefixIcon: Icon(Icons.link),
          ),
          keyboardType: TextInputType.url,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _webhookMethod,
          decoration: const InputDecoration(
            labelText: 'HTTP Method',
            prefixIcon: Icon(Icons.http),
          ),
          items: const [
            DropdownMenuItem(value: 'GET', child: Text('GET')),
            DropdownMenuItem(value: 'POST', child: Text('POST')),
            DropdownMenuItem(value: 'PUT', child: Text('PUT')),
            DropdownMenuItem(value: 'PATCH', child: Text('PATCH')),
          ],
          onChanged: (value) => setState(() => _webhookMethod = value!),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _webhookHeadersController,
          decoration: const InputDecoration(
            labelText: 'Headers (Optional JSON)',
            hintText: '{"Authorization": "Bearer token"}',
            helperText: 'Custom HTTP headers as JSON object',
            alignLabelWithHint: true,
          ),
          maxLines: 3,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _webhookPayloadController,
          decoration: const InputDecoration(
            labelText: 'Payload (Optional JSON)',
            hintText: '{"event": "trigger_fired", "data": {...}}',
            helperText: 'Request body as JSON object',
            alignLabelWithHint: true,
          ),
          maxLines: 5,
        ),
      ],
    );
  }
  
  Widget _buildLogConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _logMessageController,
          decoration: const InputDecoration(
            labelText: 'Log Message *',
            hintText: 'Trigger {trigger_name} fired at {timestamp}',
            helperText: 'Available variables: {trigger_name}, {timestamp}',
            prefixIcon: Icon(Icons.message),
            alignLabelWithHint: true,
          ),
          maxLines: 3,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _logLevel,
          decoration: const InputDecoration(
            labelText: 'Log Level',
            prefixIcon: Icon(Icons.priority_high),
          ),
          items: const [
            DropdownMenuItem(value: 'debug', child: Text('Debug')),
            DropdownMenuItem(value: 'info', child: Text('Info')),
            DropdownMenuItem(value: 'warning', child: Text('Warning')),
            DropdownMenuItem(value: 'error', child: Text('Error')),
          ],
          onChanged: (value) => setState(() => _logLevel = value!),
        ),
      ],
    );
  }
  
  Widget _buildMessagingAppConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Platform selector
        DropdownButtonFormField<String>(
          value: _messagingPlatform,
          decoration: const InputDecoration(
            labelText: 'Platform *',
            prefixIcon: Icon(Icons.chat_bubble),
          ),
          items: const [
            DropdownMenuItem(value: 'slack', child: Text('Slack')),
            DropdownMenuItem(value: 'teams', child: Text('Microsoft Teams')),
          ],
          onChanged: (value) => setState(() => _messagingPlatform = value!),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _messagingWebhookUrlController,
          decoration: InputDecoration(
            labelText: 'Webhook URL *',
            hintText: _messagingPlatform == 'slack'
                ? 'https://hooks.slack.com/services/T.../B.../...'
                : 'https://prod-xx.logic.azure.com/workflows/...',
            prefixIcon: const Icon(Icons.link),
            helperText: _messagingPlatform == 'slack'
                ? 'From Slack App → Incoming Webhooks'
                : 'From Teams channel → Apps → Workflows',
          ),
          keyboardType: TextInputType.url,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _messagingMessageController,
          decoration: const InputDecoration(
            labelText: 'Message Template *',
            hintText: '\ud83d\udd14 *{trigger_name}* fired\n>{reason}\nScore: {similarity_score}',
            helperText:
                'Variables: {trigger_name}, {reason}, {match_reason}, {similarity_score}, {matched_member_name}',
            alignLabelWithHint: true,
          ),
          maxLines: 4,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _messagingTitleController,
          decoration: InputDecoration(
            labelText: _messagingPlatform == 'teams'
                ? 'Card Title (Optional)'
                : 'Title (Optional)',
            hintText: 'Detection Alert',
            helperText: _messagingPlatform == 'teams'
                ? 'When set, message is sent as an Adaptive Card with this title'
                : 'Not used for Slack — title is part of the message template',
            prefixIcon: const Icon(Icons.title),
          ),
        ),
        if (_messagingPlatform == 'slack') ...[
          const SizedBox(height: 16),
          TextFormField(
            controller: _messagingMentionController,
            decoration: const InputDecoration(
              labelText: 'Mention (Optional)',
              hintText: '@channel or @here',
              helperText: 'Prepended to the message to notify channel members',
              prefixIcon: Icon(Icons.alternate_email),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildAlertConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _alertMessageController,
          decoration: const InputDecoration(
            labelText: 'Alert Message *',
            hintText: 'High traffic detected!',
            helperText: 'Message displayed in the on-screen alert',
            prefixIcon: Icon(Icons.notifications_active),
            alignLabelWithHint: true,
          ),
          maxLines: 3,
          validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _alertSeverity,
          decoration: const InputDecoration(
            labelText: 'Severity',
            prefixIcon: Icon(Icons.warning),
            helperText: 'Alert severity level',
          ),
          items: const [
            DropdownMenuItem(value: 'info', child: Text('Info')),
            DropdownMenuItem(value: 'warning', child: Text('Warning')),
            DropdownMenuItem(value: 'error', child: Text('Error')),
            DropdownMenuItem(value: 'critical', child: Text('Critical')),
          ],
          onChanged: (value) => setState(() => _alertSeverity = value!),
        ),
        const SizedBox(height: 16),
        TextFormField(
          initialValue: _alertDuration.toString(),
          decoration: const InputDecoration(
            labelText: 'Duration (seconds)',
            hintText: '30',
            helperText: 'How long the alert should be displayed',
            prefixIcon: Icon(Icons.timer),
          ),
          keyboardType: TextInputType.number,
          onChanged: (value) {
            final parsed = int.tryParse(value);
            if (parsed != null && parsed > 0) {
              _alertDuration = parsed;
            }
          },
          validator: (value) {
            if (value == null || value.isEmpty) return 'Required';
            final parsed = int.tryParse(value);
            if (parsed == null || parsed <= 0) {
              return 'Must be a positive number';
            }
            return null;
          },
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final form = SingleChildScrollView(
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Name',
                hintText: 'Alert on High Traffic',
              ),
              validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (Optional)',
                hintText: 'Shows alert when threshold is met',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _selectedActionType,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Action Type'),
              items: const [
                DropdownMenuItem(value: 'alert', child: Text('Alert (On-Screen)')),
                DropdownMenuItem(value: 'email', child: Text('Email')),
                DropdownMenuItem(value: 'webhook', child: Text('Webhook')),
                DropdownMenuItem(value: 'log', child: Text('Log')),
                DropdownMenuItem(value: 'digital_signage', child: Text('Digital Signage')),
                DropdownMenuItem(value: 'messaging_app', child: Text('Messaging App (Slack / Teams)')),
              ],
              selectedItemBuilder: (context) => const [
                Text('Alert (On-Screen)', overflow: TextOverflow.ellipsis),
                Text('Email', overflow: TextOverflow.ellipsis),
                Text('Webhook', overflow: TextOverflow.ellipsis),
                Text('Log', overflow: TextOverflow.ellipsis),
                Text('Digital Signage', overflow: TextOverflow.ellipsis),
                Text('Messaging App (Slack / Teams)', overflow: TextOverflow.ellipsis),
              ],
              onChanged: (value) {
                setState(() => _selectedActionType = value!);
                if (value == 'digital_signage' && _availableDevices.isEmpty && _availablePlaylists.isEmpty) {
                  _loadSignageData();
                }
              },
            ),
            const SizedBox(height: 16),

            // Show different config UI based on action type
            if (_selectedActionType == 'digital_signage')
              _buildDigitalSignageConfig()
            else if (_selectedActionType == 'email')
              _buildEmailConfig()
            else if (_selectedActionType == 'webhook')
              _buildWebhookConfig()
            else if (_selectedActionType == 'log')
              _buildLogConfig()
            else if (_selectedActionType == 'alert')
              _buildAlertConfig()
            else if (_selectedActionType == 'messaging_app')
              _buildMessagingAppConfig()
            else
              TextFormField(
                controller: _configController,
                decoration: const InputDecoration(
                  labelText: 'Configuration (Optional JSON)',
                  hintText: '{"message": "High traffic detected!"}',
                ),
                maxLines: 3,
              ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Active'),
              value: _isActive,
              onChanged: (value) => setState(() => _isActive = value),
            ),
          ],
        ),
      ),
    );

    final cancelButton = TextButton(
      onPressed: _isSaving
          ? null
          : (widget.embedded
              ? widget.onCancel ?? () => Navigator.pop(context)
              : () => Navigator.pop(context)),
      child: const Text('Cancel'),
    );
    final saveButton = ElevatedButton(
      onPressed: _isSaving ? null : _save,
      child: _isSaving
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Text(widget.action == null ? 'Create' : 'Update'),
    );

    if (widget.embedded) {
      return Card(
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.action == null
                    ? 'Create User Action'
                    : 'Edit User Action',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 12),
              form,
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [cancelButton, const SizedBox(width: 8), saveButton],
              ),
            ],
          ),
        ),
      );
    }

    return AlertDialog(
      title: Text(
        widget.action == null ? 'Create User Action' : 'Edit User Action',
      ),
      content: form,
      actions: [cancelButton, saveButton],
    );
  }
}
