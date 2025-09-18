import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../models/face_detection_models.dart';

/// Widget for managing workflow automation rules
/// Allows users to set up automatic processing, notifications, and actions
class WorkflowAutomationRulesWidget extends ConsumerStatefulWidget {
  const WorkflowAutomationRulesWidget({super.key});

  @override
  ConsumerState<WorkflowAutomationRulesWidget> createState() => 
      _WorkflowAutomationRulesWidgetState();
}

class _WorkflowAutomationRulesWidgetState extends ConsumerState<WorkflowAutomationRulesWidget> {
  final List<AutomationRule> _rules = [
    AutomationRule(
      id: '1',
      name: 'Auto-process new sessions',
      description: 'Automatically start face detection on new recording sessions',
      isEnabled: true,
      trigger: 'session_created',
      actions: ['start_face_detection'],
    ),
    AutomationRule(
      id: '2',
      name: 'Optimize completed videos',
      description: 'Automatically optimize videos when face detection completes',
      isEnabled: true,
      trigger: 'face_detection_completed',
      actions: ['optimize_video'],
    ),
    AutomationRule(
      id: '3',
      name: 'Cleanup old sessions',
      description: 'Automatically archive sessions older than 30 days',
      isEnabled: false,
      trigger: 'scheduled_daily',
      actions: ['archive_old_sessions'],
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildHeader(),
        _buildQuickActions(),
        Expanded(child: _buildRulesList()),
        _buildCreateRuleButton(),
      ],
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: AppColors.surface,
      child: Row(
        children: [
          Icon(
            Icons.auto_mode,
            color: AppColors.primary,
            size: 24,
          ),
          const SizedBox(width: 12),
          Text(
            'Automation Rules',
            style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
          ),
          const Spacer(),
          Text(
            '${_rules.where((r) => r.isEnabled).length}/${_rules.length} active',
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.surfaceVariant,
      child: Row(
        children: [
          ElevatedButton.icon(
            onPressed: _enableAllRules,
            icon: const Icon(Icons.play_arrow, size: 16),
            label: const Text('Enable All'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(width: 12),
          ElevatedButton.icon(
            onPressed: _disableAllRules,
            icon: const Icon(Icons.pause, size: 16),
            label: const Text('Disable All'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warning,
              foregroundColor: Colors.white,
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            onPressed: _importRules,
            icon: const Icon(Icons.upload, size: 16),
            label: const Text('Import'),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            onPressed: _exportRules,
            icon: const Icon(Icons.download, size: 16),
            label: const Text('Export'),
          ),
        ],
      ),
    );
  }

  Widget _buildRulesList() {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _rules.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) => _buildRuleCard(_rules[index]),
    );
  }

  Widget _buildRuleCard(AutomationRule rule) {
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Switch(
                  value: rule.isEnabled,
                  onChanged: (value) => _toggleRule(rule.id, value),
                  activeColor: AppColors.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        rule.name,
                        style: AppTextStyles.subtitle1.copyWith(
                          color: AppColors.textPrimary,
                        ),
                      ),
                      Text(
                        rule.description,
                        style: AppTextStyles.bodyMedium.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                PopupMenuButton<String>(
                  onSelected: (action) => _handleRuleAction(rule.id, action),
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit, size: 16),
                          SizedBox(width: 8),
                          Text('Edit'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'duplicate',
                      child: Row(
                        children: [
                          Icon(Icons.copy, size: 16),
                          SizedBox(width: 8),
                          Text('Duplicate'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete, size: 16, color: AppColors.error),
                          SizedBox(width: 8),
                          Text('Delete', style: TextStyle(color: AppColors.error)),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildRuleDetails(rule),
          ],
        ),
      ),
    );
  }

  Widget _buildRuleDetails(AutomationRule rule) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _buildDetailChip('Trigger', rule.trigger, AppColors.info),
              const SizedBox(width: 8),
              _buildDetailChip('Actions', '${rule.actions.length}', AppColors.success),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 4,
            runSpacing: 4,
            children: rule.actions.map((action) => 
              Chip(
                label: Text(
                  action.replaceAll('_', ' ').toUpperCase(),
                  style: const TextStyle(fontSize: 10),
                ),
                backgroundColor: AppColors.primary.withOpacity(0.1),
                labelStyle: TextStyle(color: AppColors.primary),
              )
            ).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 10,
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 10,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCreateRuleButton() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: _createNewRule,
          icon: const Icon(Icons.add),
          label: const Text('Create New Rule'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ),
    );
  }

  void _toggleRule(String ruleId, bool isEnabled) {
    setState(() {
      final ruleIndex = _rules.indexWhere((r) => r.id == ruleId);
      if (ruleIndex != -1) {
        _rules[ruleIndex] = _rules[ruleIndex].copyWith(isEnabled: isEnabled);
      }
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Rule ${isEnabled ? 'enabled' : 'disabled'}'),
        backgroundColor: isEnabled ? AppColors.success : AppColors.warning,
      ),
    );
  }

  void _enableAllRules() {
    setState(() {
      for (int i = 0; i < _rules.length; i++) {
        _rules[i] = _rules[i].copyWith(isEnabled: true);
      }
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('All rules enabled'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  void _disableAllRules() {
    setState(() {
      for (int i = 0; i < _rules.length; i++) {
        _rules[i] = _rules[i].copyWith(isEnabled: false);
      }
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('All rules disabled'),
        backgroundColor: AppColors.warning,
      ),
    );
  }

  void _handleRuleAction(String ruleId, String action) {
    switch (action) {
      case 'edit':
        _editRule(ruleId);
        break;
      case 'duplicate':
        _duplicateRule(ruleId);
        break;
      case 'delete':
        _deleteRule(ruleId);
        break;
    }
  }

  void _editRule(String ruleId) {
    // TODO: Implement rule editing
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Rule editing feature coming soon'),
        backgroundColor: AppColors.info,
      ),
    );
  }

  void _duplicateRule(String ruleId) {
    final rule = _rules.firstWhere((r) => r.id == ruleId);
    setState(() {
      _rules.add(
        rule.copyWith(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          name: '${rule.name} (Copy)',
          isEnabled: false,
        ),
      );
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Rule duplicated'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  void _deleteRule(String ruleId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(
          'Delete Rule',
          style: AppTextStyles.h6.copyWith(color: AppColors.textPrimary),
        ),
        content: const Text(
          'Are you sure you want to delete this automation rule? This action cannot be undone.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              setState(() {
                _rules.removeWhere((r) => r.id == ruleId);
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Rule deleted'),
                  backgroundColor: AppColors.error,
                ),
              );
            },
            style: TextButton.styleFrom(foregroundColor: AppColors.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _createNewRule() {
    // TODO: Implement rule creation wizard
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Rule creation wizard coming soon'),
        backgroundColor: AppColors.info,
      ),
    );
  }

  void _importRules() {
    // TODO: Implement rule import
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Rule import feature coming soon'),
        backgroundColor: AppColors.info,
      ),
    );
  }

  void _exportRules() {
    // TODO: Implement rule export
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Exporting automation rules...'),
        backgroundColor: AppColors.primary,
      ),
    );
  }
}

/// Model for automation rules
class AutomationRule {
  final String id;
  final String name;
  final String description;
  final bool isEnabled;
  final String trigger;
  final List<String> actions;

  const AutomationRule({
    required this.id,
    required this.name,
    required this.description,
    required this.isEnabled,
    required this.trigger,
    required this.actions,
  });

  AutomationRule copyWith({
    String? id,
    String? name,
    String? description,
    bool? isEnabled,
    String? trigger,
    List<String>? actions,
  }) {
    return AutomationRule(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      isEnabled: isEnabled ?? this.isEnabled,
      trigger: trigger ?? this.trigger,
      actions: actions ?? this.actions,
    );
  }
}