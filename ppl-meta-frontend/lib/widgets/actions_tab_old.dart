import 'package:flutter/material.dart';
import '../models/workflow_action_model.dart';
import '../services/workflow_action_service.dart';
import '../services/auth_service.dart';

/// Actions tab for managing orchestrator workflows that can be triggered
/// 
/// Actions wrap orchestrator workflows and can be fired from triggers
class ActionsTab extends StatefulWidget {
  const ActionsTab({Key? key}) : super(key: key);

  @override
  State<ActionsTab> createState() => _ActionsTabState();
}

class _ActionsTabState extends State<ActionsTab> {
  bool _isLoading = false;
  String? _errorMessage;
  List<WorkflowAction> _actions = [];
  final WorkflowActionService _workflowService = WorkflowActionService();
  final AuthService _authService = AuthService();
  
  int _currentPage = 1;
  int _totalPages = 1;
  bool? _filterIsActive;

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
    // Get auth token if available
    final token = await _authService.getStoredToken();
    if (token != null) {
      _workflowService.setAuthToken(token);
    }
    await _loadActions();
  }

  Future<void> _loadActions() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final workflows = await _workflowService.getWorkflows(
        isActive: _filterIsActive,
      );
      
      setState(() {
        _actions = workflows;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load workflows: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleAction(WorkflowAction action) async {
    // Note: Currently workflows registry is read-only
    // In future, implement API to toggle workflow active status
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Workflow status toggling not yet implemented'),
        duration: Duration(seconds: 2),
      ),
    );
    
    /*
    setState(() {
      final index = _actions.indexWhere((a) => a.id == action.id);
      if (index != -1) {
        _actions[index] = action.copyWith(isActive: !action.isActive);
      }
    });
    */
  }

  Future<void> _deleteAction(WorkflowAction action) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Workflow'),
        content: Text(
          'Are you sure you want to delete this workflow?\n${action.name}\n\nNote: This action is not yet implemented in the API.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      // Note: Workflow deletion not yet implemented in API
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Workflow deletion not yet implemented'),
          duration: Duration(seconds: 2),
        ),
      );
      
      /*
      setState(() {
        _actions.removeWhere((a) => a.id == action.id);
      });
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Workflow deleted successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
      */
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with filter
          Row(
            children: [
              const Icon(Icons.play_circle_outline, color: Colors.blue),
              const SizedBox(width: 8),
              Text(
                'Workflow Actions',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              // Filter dropdown
              DropdownButton<bool?>(
                value: _filterIsActive,
                dropdownColor: Colors.grey.shade900,
                items: const [
                  DropdownMenuItem(value: null, child: Text('All')),
                  DropdownMenuItem(value: true, child: Text('Active')),
                  DropdownMenuItem(value: false, child: Text('Inactive')),
                ],
                onChanged: (value) {
                  setState(() {
                    _filterIsActive = value;
                    _currentPage = 1;
                  });
                  _loadActions();
                },
              ),
              const SizedBox(width: 16),
              // Add button
              ElevatedButton.icon(
                onPressed: () {
                  // TODO: Show create action dialog
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Create dialog coming soon')),
                  );
                },
                icon: const Icon(Icons.add),
                label: const Text('Create Action'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Loading state
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(),
              ),
            ),
          
          // Error state
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.red.shade900.withOpacity(0.3),
                border: Border.all(color: Colors.red),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                  TextButton(
                    onPressed: _loadActions,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          
          // Empty state
          if (!_isLoading && _errorMessage == null && _actions.isEmpty)
            Container(
              padding: const EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Column(
                children: [
                  Icon(
                    Icons.smart_toy_outlined,
                    size: 64,
                    color: Colors.grey.shade600,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No actions found',
                    style: TextStyle(
                      fontSize: 18,
                      color: Colors.grey.shade500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Create your first workflow action to get started',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),
          
          // Data table (responsive)
          if (!_isLoading && _errorMessage == null && _actions.isNotEmpty)
            LayoutBuilder(
              builder: (context, constraints) {
                final isWideScreen = constraints.maxWidth > 900;
                
                if (isWideScreen) {
                  return _buildDataTable(constraints);
                } else {
                  return _buildCardList();
                }
              },
            ),
        ],
      ),
    );
  }

  Widget _buildDataTable(BoxConstraints constraints) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: Colors.grey.shade900,
            border: Border.all(color: Colors.grey.shade700),
            borderRadius: BorderRadius.circular(8),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: constraints.maxWidth),
              child: DataTable(
                columnSpacing: 16,
                horizontalMargin: 16,
                headingRowColor: MaterialStateProperty.all(Colors.grey.shade800),
                dataRowColor: MaterialStateProperty.all(Colors.grey.shade900),
                columns: const [
                  DataColumn(label: Text('Name', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Description', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Type', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Executions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Success Rate', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                  DataColumn(label: Text('Actions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
                ],
                rows: _actions.map((action) {
                  return DataRow(cells: [
                    DataCell(Text(action.name, style: const TextStyle(color: Colors.white70))),
                    DataCell(
                      SizedBox(
                        width: 200,
                        child: Text(
                          action.description,
                          style: const TextStyle(color: Colors.white70),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    DataCell(Text(action.workflowType.toUpperCase(), style: const TextStyle(color: Colors.white70))),
                    DataCell(Text(action.executionCount.toString(), style: const TextStyle(color: Colors.white70))),
                    DataCell(Text('${action.successRate.toStringAsFixed(1)}%', style: const TextStyle(color: Colors.white70))),
                    DataCell(
                      InkWell(
                        onTap: () => _toggleAction(action),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: action.isActive
                                ? Colors.green.shade900
                                : Colors.red.shade900,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            action.isActive ? 'Active' : 'Inactive',
                            style: TextStyle(
                              color: action.isActive
                                  ? Colors.green.shade300
                                  : Colors.red.shade300,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ),
                    DataCell(
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit, color: Colors.blue, size: 20),
                            onPressed: () {
                              // TODO: Show edit dialog
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Edit dialog coming soon')),
                              );
                            },
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete, color: Colors.red, size: 20),
                            onPressed: () => _deleteAction(action),
                          ),
                        ],
                      ),
                    ),
                  ]);
                }).toList(),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildCardList() {
    return Column(
      children: _actions.map((action) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.grey.shade900,
            border: Border.all(color: Colors.grey.shade700),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header with status badge
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        action.name,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () => _toggleAction(action),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: action.isActive
                              ? Colors.green.shade900
                              : Colors.red.shade900,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          action.isActive ? 'Active' : 'Inactive',
                          style: TextStyle(
                            color: action.isActive
                                ? Colors.green.shade300
                                : Colors.red.shade300,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                
                // Details
                _buildDetailRow('Description', action.description),
                _buildDetailRow('Type', action.workflowType.toUpperCase()),
                _buildDetailRow('Category', action.category.toUpperCase()),
                _buildDetailRow('Executions', action.executionCount.toString()),
                _buildDetailRow('Success Rate', '${action.successRate.toStringAsFixed(1)}%'),
                if (action.averageDurationSeconds != null)
                  _buildDetailRow('Avg Duration', '${action.averageDurationSeconds!.toStringAsFixed(1)}s'),
                
                const SizedBox(height: 16),
                
                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () {
                        // TODO: Show edit dialog
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Edit dialog coming soon')),
                        );
                      },
                      icon: const Icon(Icons.edit, size: 16),
                      label: const Text('Edit'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.blue,
                        side: const BorderSide(color: Colors.blue),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton.icon(
                      onPressed: () => _deleteAction(action),
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red,
                        side: const BorderSide(color: Colors.red),
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
                color: Colors.grey.shade400,
                fontSize: 14,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
