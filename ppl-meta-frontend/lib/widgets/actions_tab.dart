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
import '../core/config/app_config.dart';
import '../screens/communication_logs_screen.dart';
import '../screens/communication_logs_screen.dart';

/// Actions tab with User Actions (CRUD-able) and System Workflows (read-only)
class ActionsTab extends StatefulWidget {
  const ActionsTab({Key? key}) : super(key: key);

  @override
  State<ActionsTab> createState() => _ActionsTabState();
}

class _ActionsTabState extends State<ActionsTab> {
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
    setState(() {
      _isLoadingUser = true;
      _errorMessageUser = null;
    });

    try {
      final response = await _userActionService.fetchUserActions(
        isActive: _filterIsActiveUser,
      );
      
      setState(() {
        _userActions = response.actions;
        _isLoadingUser = false;
      });
    } catch (e) {
      setState(() {
        _errorMessageUser = 'Failed to load user actions: $e';
        _isLoadingUser = false;
      });
    }
  }

  Future<void> _loadSystemWorkflows() async {
    setState(() {
      _isLoadingSystem = true;
      _errorMessageSystem = null;
    });

    try {
      final workflows = await _workflowService.getWorkflows(
        isActive: _filterIsActiveSystem,
      );
      
      setState(() {
        _systemWorkflows = workflows;
        _isLoadingSystem = false;
      });
    } catch (e) {
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
            style: TextButton.styleFrom(foregroundColor: Colors.red),
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
              backgroundColor: Colors.green,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to delete: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  Future<void> _toggleUserAction(UserActionModel action) async {
    try {
      await _userActionService.toggleUserAction(action.uuid);
      await _loadUserActions();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to toggle: $e')),
        );
      }
    }
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
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
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
    );
  }

  Widget _buildUserActionsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            const Icon(Icons.person, color: Colors.blue),
            const SizedBox(width: 8),
            Text(
              'User Actions',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const Spacer(),
            // Filter
            DropdownButton<bool?>(
              value: _filterIsActiveUser,
              dropdownColor: Colors.grey.shade900,
              items: const [
                DropdownMenuItem(value: null, child: Text('All')),
                DropdownMenuItem(value: true, child: Text('Active')),
                DropdownMenuItem(value: false, child: Text('Inactive')),
              ],
              onChanged: (value) {
                setState(() => _filterIsActiveUser = value);
                _loadUserActions();
              },
            ),
            const SizedBox(width: 16),
            // Create button
            ElevatedButton.icon(
              onPressed: () => _showCreateEditUserActionDialog(),
              icon: const Icon(Icons.add),
              label: const Text('Create Action'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
              ),
            ),
            const SizedBox(width: 12),
            // View Communication Logs button
            OutlinedButton.icon(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const CommunicationLogsScreen(),
                  ),
                );
              },
              icon: const Icon(Icons.history, size: 20),
              label: const Text('View Logs'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.green.shade300,
                side: BorderSide(color: Colors.green.shade700),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        
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
              color: Colors.red.shade900.withOpacity(0.3),
              border: Border.all(color: Colors.red),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.error, color: Colors.red),
                const SizedBox(width: 8),
                Expanded(child: Text(_errorMessageUser!, style: const TextStyle(color: Colors.red))),
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
                Icon(Icons.add_circle_outline, size: 64, color: Colors.grey.shade600),
                const SizedBox(height: 16),
                Text(
                  'No user actions yet',
                  style: TextStyle(fontSize: 18, color: Colors.grey.shade500),
                ),
                const SizedBox(height: 8),
                Text(
                  'Create your first custom action to get started',
                  style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingUser && _errorMessageUser == null && _userActions.isNotEmpty)
          LayoutBuilder(
            builder: (context, constraints) {
              final isWideScreen = constraints.maxWidth > 900;
              
              if (isWideScreen) {
                return _buildUserActionsTable();
              } else {
                return _buildUserActionsCardList();
              }
            },
          ),
      ],
    );
  }

  Widget _buildSystemWorkflowsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        Row(
          children: [
            const Icon(Icons.settings, color: Colors.grey),
            const SizedBox(width: 8),
            Text(
              'System Workflows',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(width: 8),
            Chip(
              label: const Text('Read-only', style: TextStyle(fontSize: 12)),
              backgroundColor: Colors.grey.shade800,
            ),
            const Spacer(),
            // Filter
            DropdownButton<bool?>(
              value: _filterIsActiveSystem,
              dropdownColor: Colors.grey.shade900,
              items: const [
                DropdownMenuItem(value: null, child: Text('All')),
                DropdownMenuItem(value: true, child: Text('Active')),
                DropdownMenuItem(value: false, child: Text('Inactive')),
              ],
              onChanged: (value) {
                setState(() => _filterIsActiveSystem = value);
                _loadSystemWorkflows();
              },
            ),
          ],
        ),
        const SizedBox(height: 16),
        
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
              color: Colors.red.shade900.withOpacity(0.3),
              border: Border.all(color: Colors.red),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.error, color: Colors.red),
                const SizedBox(width: 8),
                Expanded(child: Text(_errorMessageSystem!, style: const TextStyle(color: Colors.red))),
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
                Icon(Icons.inbox_outlined, size: 64, color: Colors.grey.shade600),
                const SizedBox(height: 16),
                Text(
                  'No system workflows found',
                  style: TextStyle(fontSize: 18, color: Colors.grey.shade500),
                ),
              ],
            ),
          ),
        
        if (!_isLoadingSystem && _errorMessageSystem == null && _systemWorkflows.isNotEmpty)
          LayoutBuilder(
            builder: (context, constraints) {
              final isWideScreen = constraints.maxWidth > 900;
              
              if (isWideScreen) {
                return _buildSystemWorkflowsTable();
              } else {
                return _buildSystemWorkflowsCardList();
              }
            },
          ),
      ],
    );
  }

  Widget _buildUserActionsTable() {
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
            DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Actions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
          ],
          rows: _userActions.map((action) {
            return DataRow(cells: [
              DataCell(Text(action.name, style: const TextStyle(color: Colors.white70))),
              DataCell(
                SizedBox(
                  width: 200,
                  child: Text(
                    action.description ?? '-',
                    style: const TextStyle(color: Colors.white70),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              DataCell(Text(action.actionTypeDisplay, style: const TextStyle(color: Colors.white70))),
              DataCell(
                InkWell(
                  onTap: () => _toggleUserAction(action),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: action.isActive ? Colors.green.shade900 : Colors.red.shade900,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      action.isActive ? 'Active' : 'Inactive',
                      style: TextStyle(
                        color: action.isActive ? Colors.green.shade300 : Colors.red.shade300,
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
                      onPressed: () => _showCreateEditUserActionDialog(action: action),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete, color: Colors.red, size: 20),
                      onPressed: () => _deleteUserAction(action),
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

  Widget _buildSystemWorkflowsTable() {
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
            DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
            DataColumn(label: Text('Actions', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70))),
          ],
          rows: _systemWorkflows.map((workflow) {
            return DataRow(cells: [
              DataCell(Text(workflow.name, style: const TextStyle(color: Colors.white70))),
              DataCell(
                SizedBox(
                  width: 200,
                  child: Text(
                    workflow.description,
                    style: const TextStyle(color: Colors.white70),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              DataCell(Text(workflow.workflowType.toUpperCase(), style: const TextStyle(color: Colors.white70))),
              DataCell(
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: workflow.isActive ? Colors.green.shade900 : Colors.red.shade900,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    workflow.isActive ? 'Active' : 'Inactive',
                    style: TextStyle(
                      color: workflow.isActive ? Colors.green.shade300 : Colors.red.shade300,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
              DataCell(
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: Icon(Icons.edit, color: Colors.grey.shade700, size: 20),
                      onPressed: null, // Disabled
                    ),
                    IconButton(
                      icon: Icon(Icons.delete, color: Colors.grey.shade700, size: 20),
                      onPressed: null, // Disabled
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

  Widget _buildUserActionsCardList() {
    return Column(
      children: _userActions.map((action) {
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
                // Header: name + status badge
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        action.name,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () => _toggleUserAction(action),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: action.isActive ? Colors.green.shade900 : Colors.grey.shade800,
                          border: Border.all(
                            color: action.isActive ? Colors.green.shade700 : Colors.grey.shade600,
                          ),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          action.isActive ? 'Active' : 'Inactive',
                          style: TextStyle(
                            color: action.isActive ? Colors.green.shade300 : Colors.grey.shade400,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),
                // Detail rows
                _buildDetailRow('Description', action.description ?? '-'),
                _buildDetailRow('Type', action.actionTypeDisplay),
                _buildDetailRow('Created', _formatDate(action.createdAt)),
                const SizedBox(height: 16),
                // Action buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _showCreateEditUserActionDialog(action: action),
                      icon: const Icon(Icons.edit, size: 16),
                      label: const Text('Edit'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.blue.shade300,
                        side: BorderSide(color: Colors.blue.shade700),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton.icon(
                      onPressed: () => _deleteUserAction(action),
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red.shade300,
                        side: BorderSide(color: Colors.red.shade700),
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

  Widget _buildSystemWorkflowsCardList() {
    return Column(
      children: _systemWorkflows.map((workflow) {
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
                        color: workflow.isActive ? Colors.green.shade900 : Colors.grey.shade800,
                        border: Border.all(
                          color: workflow.isActive ? Colors.green.shade700 : Colors.grey.shade600,
                        ),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        workflow.isActive ? 'Active' : 'Inactive',
                        style: TextStyle(
                          color: workflow.isActive ? Colors.green.shade300 : Colors.grey.shade400,
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
                        foregroundColor: Colors.grey.shade700,
                        side: BorderSide(color: Colors.grey.shade700),
                      ),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton.icon(
                      onPressed: null, // Disabled for system workflows
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.grey.shade700,
                        side: BorderSide(color: Colors.grey.shade700),
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
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.white),
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

  const _UserActionDialog({
    this.action,
    required this.onSave,
    required this.userActionService,
    required this.authService,
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
            backgroundColor: Colors.orange,
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
            backgroundColor: Colors.red,
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
            color: Colors.grey.shade400,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade700),
            borderRadius: BorderRadius.circular(4),
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
                      style: TextStyle(color: Colors.orange.shade400, fontSize: 14),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Make sure signage devices are running and registered with discovery service',
                      style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      onPressed: _loadSignageData,
                      icon: const Icon(Icons.refresh, size: 16),
                      label: const Text('Retry'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue.shade800,
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
                        color: device.isOnline ? Colors.green.shade300 : Colors.red.shade300,
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
                        color: Colors.orange.shade300,
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
          value: _selectedPlaylistId,
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
            hintText: 'Trigger Alert: {trigger_name}',
            helperText: 'Available variables: {trigger_name}, {timestamp}',
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
    return AlertDialog(
      title: Text(widget.action == null ? 'Create User Action' : 'Edit User Action'),
      content: SingleChildScrollView(
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
                decoration: const InputDecoration(labelText: 'Action Type'),
                items: const [
                  DropdownMenuItem(value: 'alert', child: Text('Alert (On-Screen)')),
                  DropdownMenuItem(value: 'email', child: Text('Email')),
                  DropdownMenuItem(value: 'webhook', child: Text('Webhook')),
                  DropdownMenuItem(value: 'log', child: Text('Log')),
                  DropdownMenuItem(value: 'digital_signage', child: Text('Digital Signage')),
                ],
                onChanged: (value) {
                  setState(() => _selectedActionType = value!);
                  // Load signage data when switching to digital_signage
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
      ),
      actions: [
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _isSaving ? null : _save,
          child: _isSaving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.action == null ? 'Create' : 'Update'),
        ),
      ],
    );
  }
}
