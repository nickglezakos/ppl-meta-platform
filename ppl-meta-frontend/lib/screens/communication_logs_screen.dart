import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:convert';
import 'package:csv/csv.dart';
import 'package:intl/intl.dart';
import '../models/communication_log_model.dart';
import '../services/communications_api_client.dart';
import '../services/auth_service.dart';
import '../utils/platform_file_download.dart';
import '../widgets/custom_app_bar.dart';

/// Screen for viewing communication logs from Communications Service
class CommunicationLogsScreen extends StatefulWidget {
  const CommunicationLogsScreen({Key? key}) : super(key: key);

  @override
  State<CommunicationLogsScreen> createState() => _CommunicationLogsScreenState();
}

class _CommunicationLogsScreenState extends State<CommunicationLogsScreen> {
  final CommunicationsApiClient _apiClient = CommunicationsApiClient();
  final AuthService _authService = AuthService();
  
  bool _isLoading = false;
  bool _isLoadingMore = false;
  bool _isDownloading = false;
  String? _errorMessage;
  List<CommunicationLog> _logs = [];
  int _currentPage = 1;
  int _totalPages = 1;
  int _total = 0;
  bool _hasMore = true;
  
  // Filters
  String? _filterType;
  String? _filterStatus;
  final TextEditingController _filterTriggerIdController = TextEditingController();
  final TextEditingController _filterTenantNameController = TextEditingController();
  List<String> _filterCameraIds = [];
  List<String> _availableCameraIds = [];
  DateTime? _filterStartDate;
  DateTime? _filterEndDate;
  
  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }
  
  @override
  void dispose() {
    _filterTriggerIdController.dispose();
    _filterTenantNameController.dispose();
    super.dispose();
  }

  Future<void> _initializeAndLoad() async {
    final token = await _authService.getStoredToken();
    if (token != null) {
      _apiClient.setAuthToken(token);
    }
    await _loadLogs();
  }

  Future<void> _loadLogs({bool loadMore = false}) async {
    if (loadMore) {
      setState(() => _isLoadingMore = true);
    } else {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
        _currentPage = 1;
        _logs = [];
      });
    }

    try {
      final response = await _apiClient.fetchLogs(
        page: _currentPage,
        pageSize: 20,
        type: _filterType,
        status: _filterStatus,
        triggerId: _filterTriggerIdController.text.isEmpty ? null : _filterTriggerIdController.text,
        tenantName: _filterTenantNameController.text.isEmpty ? null : _filterTenantNameController.text,
        startDate: _filterStartDate,
        endDate: _filterEndDate,
      );
      
      // Extract available camera IDs from all logs
      final cameraIds = <String>{};
      for (final log in response.logs) {
        final cameraId = log.payload?['camera_id']?.toString();
        if (cameraId != null && cameraId.isNotEmpty) {
          cameraIds.add(cameraId);
        }
      }
      
      // Filter by camera IDs on the frontend (since it's in payload)
      var filteredLogs = response.logs;
      if (_filterCameraIds.isNotEmpty) {
        filteredLogs = filteredLogs.where((log) {
          final cameraId = log.payload?['camera_id']?.toString() ?? '';
          return _filterCameraIds.contains(cameraId);
        }).toList();
      }
      
      setState(() {
        // Update available cameras list (merge with existing to keep all options)
        _availableCameraIds = {..._availableCameraIds, ...cameraIds}.toList()..sort();
        
        if (loadMore) {
          _logs.addAll(filteredLogs);
          _isLoadingMore = false;
        } else {
          _logs = filteredLogs;
          _isLoading = false;
        }
        _total = response.total;
        _totalPages = response.totalPages;
        _hasMore = _currentPage < _totalPages;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load logs: $e';
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  Future<void> _downloadAllLogs() async {
    setState(() => _isDownloading = true);

    try {
      // Fetch all logs in batches (backend limit is 500 per page)
      final List<CommunicationLog> allLogs = [];
      int currentPage = 1;
      bool hasMore = true;
      const int pageSize = 500;

      while (hasMore) {
        final response = await _apiClient.fetchLogs(
          page: currentPage,
          pageSize: pageSize,
          type: _filterType,
          status: _filterStatus,
          triggerId: _filterTriggerIdController.text.isEmpty ? null : _filterTriggerIdController.text,
          tenantName: _filterTenantNameController.text.isEmpty ? null : _filterTenantNameController.text,
          startDate: _filterStartDate,
          endDate: _filterEndDate,
        );

        allLogs.addAll(response.logs);
        
        // Check if there are more pages
        if (currentPage >= response.totalPages) {
          hasMore = false;
        } else {
          currentPage++;
        }
      }

      // Generate CSV
      final List<List<dynamic>> rows = [
        // Header row
        [
          'UUID',
          'Type',
          'Status',
          'Recipient',
          'Subject',
          'Content',
          'Triggered By',
          'Trigger Type',
          'Trigger ID',
          'Camera ID',
          'People Count',
          'Detection Timestamp',
          'Young',
          'Adult',
          'Senior',
          'Male',
          'Female',
          'Installation ID',
          'Tenant Name',
          'Attempts',
          'Last Attempt At',
          'Delivered At',
          'Failed At',
          'Error Message',
          'Response Status Code',
          'Created At',
          'Updated At',
        ],
      ];

      // Data rows
      for (final log in allLogs) {
        // Extract demographics data from payload
        final payload = log.payload ?? {};
        final cameraId = payload['camera_id']?.toString() ?? '';
        final peopleCount = payload['people_count']?.toString() ?? '';
        final detectionTimestamp = payload['detection_timestamp']?.toString() ?? payload['timestamp']?.toString() ?? '';
        
        // Extract individual demographic values
        String young = '';
        String adult = '';
        String senior = '';
        String male = '';
        String female = '';
        
        if (payload['demographics'] != null) {
          try {
            final demographics = payload['demographics'] as Map<String, dynamic>;
            
            // Check for total_ prefixed keys (actual structure)
            young = demographics['total_young']?.toString() ?? '';
            adult = demographics['total_adult']?.toString() ?? '';
            senior = demographics['total_senior']?.toString() ?? '';
            male = demographics['total_male']?.toString() ?? '';
            female = demographics['total_female']?.toString() ?? '';
            
            // Fallback: Check age_group nested structure
            if (young.isEmpty && demographics['age_group'] != null) {
              final ageGroup = demographics['age_group'] as Map<String, dynamic>;
              young = ageGroup['young']?.toString() ?? '';
              adult = ageGroup['adult']?.toString() ?? '';
              senior = ageGroup['senior']?.toString() ?? '';
            }
            
            // Fallback: Check gender nested structure
            if (male.isEmpty && demographics['gender'] != null) {
              final gender = demographics['gender'] as Map<String, dynamic>;
              male = gender['male']?.toString() ?? '';
              female = gender['female']?.toString() ?? '';
            }
          } catch (e) {
            // If parsing fails, leave empty
          }
        }
        
        rows.add([
          log.uuid,
          log.communicationType,
          log.status,
          log.recipient,
          log.subjectLine ?? '',
          log.content ?? '',
          log.triggeredBy ?? '',
          log.triggerType ?? '',
          log.triggerId ?? '',
          cameraId,
          peopleCount,
          detectionTimestamp,
          young,
          adult,
          senior,
          male,
          female,
          log.installationId ?? '',
          log.tenantName ?? '',
          log.attempts.toString(),
          log.lastAttemptAt ?? '',
          log.deliveredAt ?? '',
          log.failedAt ?? '',
          log.errorMessage ?? '',
          log.responseStatusCode?.toString() ?? '',
          log.createdAt,
          log.updatedAt,
        ]);
      }

      // Convert to CSV string
      final csvData = const ListToCsvConverter().convert(rows);

      // Create filename with timestamp
      final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
      final filename = 'communication_logs_$timestamp.csv';

      // Download file (platform-aware)
      final bytes = utf8.encode(csvData);
      final savedPath = await downloadFileBytes(
        bytes: bytes,
        filename: filename,
        mimeType: 'text/csv',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Downloaded ${allLogs.length} logs to ${savedPath ?? filename}'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to download logs: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isDownloading = false);
      }
    }
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Filter Logs'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<String?>(
                  value: _filterType,
                  decoration: const InputDecoration(labelText: 'Communication Type'),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Types')),
                    DropdownMenuItem(value: 'email', child: Text('Email')),
                    DropdownMenuItem(value: 'webhook', child: Text('Webhook')),
                    DropdownMenuItem(value: 'audit_log', child: Text('Audit')),
                    DropdownMenuItem(value: 'push_notification', child: Text('Push Notification')),
                    DropdownMenuItem(value: 'sms', child: Text('SMS')),
                  ],
                  onChanged: (value) {
                    setState(() => _filterType = value);
                    setDialogState(() {});
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String?>(
                  value: _filterStatus,
                  decoration: const InputDecoration(labelText: 'Status'),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Statuses')),
                    DropdownMenuItem(value: 'sent', child: Text('Sent')),
                    DropdownMenuItem(value: 'delivered', child: Text('Delivered')),
                    DropdownMenuItem(value: 'pending', child: Text('Pending')),
                    DropdownMenuItem(value: 'failed', child: Text('Failed')),
                  ],
                  onChanged: (value) {
                    setState(() => _filterStatus = value);
                    setDialogState(() {});
                  },
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _filterTriggerIdController,
                  decoration: const InputDecoration(
                    labelText: 'Trigger UUID',
                    hintText: 'Filter by trigger ID',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _filterTenantNameController,
                  decoration: const InputDecoration(
                    labelText: 'Tenant Name',
                    hintText: 'Filter by tenant',
                  ),
                ),
                const SizedBox(height: 16),
                // Camera multi-select
                if (_availableCameraIds.isNotEmpty) ...[
                  const Text('Camera(s)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
                  const SizedBox(height: 8),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey.shade700),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Column(
                      children: _availableCameraIds.map((cameraId) {
                        return CheckboxListTile(
                          dense: true,
                          title: Text(cameraId, style: const TextStyle(fontSize: 13)),
                          value: _filterCameraIds.contains(cameraId),
                          onChanged: (bool? checked) {
                            setState(() {
                              if (checked == true) {
                                _filterCameraIds.add(cameraId);
                              } else {
                                _filterCameraIds.remove(cameraId);
                              }
                            });
                            setDialogState(() {});
                          },
                        );
                      }).toList(),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                const Text('Date & Time Range', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
                const SizedBox(height: 8),
                // Start Date/Time
                OutlinedButton.icon(
                  onPressed: () async {
                    final pickedDate = await showDatePicker(
                      context: context,
                      initialDate: _filterStartDate ?? DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (pickedDate != null) {
                      final pickedTime = await showTimePicker(
                        context: context,
                        initialTime: TimeOfDay.fromDateTime(_filterStartDate ?? DateTime.now()),
                      );
                      if (pickedTime != null) {
                        setState(() {
                          _filterStartDate = DateTime(
                            pickedDate.year,
                            pickedDate.month,
                            pickedDate.day,
                            pickedTime.hour,
                            pickedTime.minute,
                          );
                        });
                        setDialogState(() {});
                      }
                    }
                  },
                  icon: const Icon(Icons.event, size: 16),
                  label: Text(
                    _filterStartDate != null
                        ? '${_filterStartDate!.year}-${_filterStartDate!.month.toString().padLeft(2, '0')}-${_filterStartDate!.day.toString().padLeft(2, '0')} ${_filterStartDate!.hour.toString().padLeft(2, '0')}:${_filterStartDate!.minute.toString().padLeft(2, '0')}'
                        : 'Start Date & Time',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
                const SizedBox(height: 8),
                // End Date/Time
                OutlinedButton.icon(
                  onPressed: () async {
                    final pickedDate = await showDatePicker(
                      context: context,
                      initialDate: _filterEndDate ?? DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (pickedDate != null) {
                      final pickedTime = await showTimePicker(
                        context: context,
                        initialTime: TimeOfDay.fromDateTime(_filterEndDate ?? DateTime.now()),
                      );
                      if (pickedTime != null) {
                        setState(() {
                          _filterEndDate = DateTime(
                            pickedDate.year,
                            pickedDate.month,
                            pickedDate.day,
                            pickedTime.hour,
                            pickedTime.minute,
                          );
                        });
                        setDialogState(() {});
                      }
                    }
                  },
                  icon: const Icon(Icons.event, size: 16),
                  label: Text(
                    _filterEndDate != null
                        ? '${_filterEndDate!.year}-${_filterEndDate!.month.toString().padLeft(2, '0')}-${_filterEndDate!.day.toString().padLeft(2, '0')} ${_filterEndDate!.hour.toString().padLeft(2, '0')}:${_filterEndDate!.minute.toString().padLeft(2, '0')}'
                        : 'End Date & Time',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        actions: [
          TextButton(
            onPressed: () {
              setState(() {
                _filterType = null;
                _filterStatus = null;
                _filterTriggerIdController.clear();
                _filterTenantNameController.clear();
                _filterCameraIds.clear();
                _filterStartDate = null;
                _filterEndDate = null;
              });
              Navigator.pop(context);
            },
            child: const Text('Clear Filters'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _currentPage = 1;
              _loadLogs();
            },
            child: const Text('Apply'),
          ),
        ],
        ),
      ),
    );
  }

  void _showLogDetails(CommunicationLog log) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Log Details: ${log.communicationType.toUpperCase()}'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildDetailRow('UUID', log.uuid, copyable: true),
              _buildDetailRow('Type', log.communicationType),
              _buildDetailRow('Status', log.status),
              _buildDetailRow('Recipient', log.recipient, copyable: true),
              if (log.subjectLine != null) 
                _buildDetailRow('Subject', log.subjectLine!),
              if (log.content != null) 
                _buildDetailRow('Content', log.content!, expandable: true),
              if (log.triggeredBy != null) 
                _buildDetailRow('Triggered By', log.triggeredBy!),
              if (log.triggerType != null) 
                _buildDetailRow('Trigger Type', log.triggerType!),
              if (log.triggerId != null) 
                _buildDetailRow('Trigger ID', log.triggerId!, copyable: true),
              if (log.payload != null && log.payload!.containsKey('trigger_name'))
                _buildDetailRow('Trigger Name', log.payload!['trigger_name'].toString()),
              if (log.payload != null && log.payload!.containsKey('action_name'))
                _buildDetailRow('Action Name', log.payload!['action_name'].toString()),
              if (log.payload != null && log.payload!.containsKey('camera_id'))
                _buildDetailRow('Camera ID', log.payload!['camera_id'].toString(), copyable: true),
              if (log.payload != null && log.payload!.containsKey('people_count'))
                _buildDetailRow('People Count', log.payload!['people_count'].toString()),
              if (log.payload != null && (log.payload!.containsKey('detection_timestamp') || log.payload!.containsKey('timestamp')))
                _buildDetailRow('Detection Time', log.payload!['detection_timestamp']?.toString() ?? log.payload!['timestamp']?.toString() ?? ''),
              if (log.payload != null && log.payload!.containsKey('demographics'))
                ..._buildDemographicsRows(log.payload!['demographics']),
              if (log.responseStatusCode != null) 
                _buildDetailRow('Response Status', log.responseStatusCode.toString()),
              if (log.errorMessage != null) 
                _buildDetailRow('Error', log.errorMessage!, isError: true),
              _buildDetailRow('Attempts', log.attempts.toString()),
              if (log.installationId != null) 
                _buildDetailRow('Installation ID', log.installationId!, copyable: true),
              if (log.tenantName != null) 
                _buildDetailRow('Tenant', log.tenantName!),
              if (log.payload != null && log.payload!.isNotEmpty)
                _buildDetailRow('Full Payload', jsonEncode(log.payload), expandable: true),
              _buildDetailRow('Created At', _formatDateTimeString(log.createdAt)),
              _buildDetailRow('Updated At', _formatDateTimeString(log.updatedAt)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {bool copyable = false, bool isError = false, bool expandable = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade400,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  value,
                  style: TextStyle(
                    fontSize: 14,
                    color: isError ? Colors.red.shade300 : Colors.white,
                  ),
                  maxLines: expandable ? null : 3,
                  overflow: expandable ? null : TextOverflow.ellipsis,
                ),
              ),
              if (copyable)
                IconButton(
                  icon: const Icon(Icons.copy, size: 16),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: value));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Copied to clipboard'),
                        duration: Duration(seconds: 1),
                      ),
                    );
                  },
                  tooltip: 'Copy',
                ),
            ],
          ),
          const Divider(height: 16),
        ],
      ),
    );
  }

  List<Widget> _buildDemographicsRows(dynamic demographicsData) {
    if (demographicsData == null) return [];
    
    List<Widget> rows = [];
    
    try {
      final demographics = demographicsData as Map<String, dynamic>;
      
      // Debug: print structure
      print('Demographics structure: $demographics');
      
      // Check for total_ prefixed keys (actual structure from backend)
      if (demographics['total_young'] != null && demographics['total_young'] != 0) {
        rows.add(_buildDetailRow('Young', demographics['total_young'].toString()));
      }
      if (demographics['total_adult'] != null && demographics['total_adult'] != 0) {
        rows.add(_buildDetailRow('Adult', demographics['total_adult'].toString()));
      }
      if (demographics['total_senior'] != null && demographics['total_senior'] != 0) {
        rows.add(_buildDetailRow('Senior', demographics['total_senior'].toString()));
      }
      if (demographics['total_male'] != null && demographics['total_male'] != 0) {
        rows.add(_buildDetailRow('Male', demographics['total_male'].toString()));
      }
      if (demographics['total_female'] != null && demographics['total_female'] != 0) {
        rows.add(_buildDetailRow('Female', demographics['total_female'].toString()));
      }
      
      // Fallback: Check nested age_group structure
      if (rows.isEmpty && demographics['age_group'] != null) {
        final ageGroup = demographics['age_group'] as Map<String, dynamic>;
        if (ageGroup['young'] != null && ageGroup['young'] != 0) {
          rows.add(_buildDetailRow('Young', ageGroup['young'].toString()));
        }
        if (ageGroup['adult'] != null && ageGroup['adult'] != 0) {
          rows.add(_buildDetailRow('Adult', ageGroup['adult'].toString()));
        }
        if (ageGroup['senior'] != null && ageGroup['senior'] != 0) {
          rows.add(_buildDetailRow('Senior', ageGroup['senior'].toString()));
        }
      }
      
      // Fallback: Check nested gender structure
      if (rows.isEmpty && demographics['gender'] != null) {
        final gender = demographics['gender'] as Map<String, dynamic>;
        if (gender['male'] != null && gender['male'] != 0) {
          rows.add(_buildDetailRow('Male', gender['male'].toString()));
        }
        if (gender['female'] != null && gender['female'] != 0) {
          rows.add(_buildDetailRow('Female', gender['female'].toString()));
        }
      }
      
    } catch (e) {
      print('Error parsing demographics: $e');
    }
    
    return rows;
  }

  Map<String, int> _calculateTotals() {
    int totalPeopleCount = 0;
    int totalYoung = 0;
    int totalAdult = 0;
    int totalSenior = 0;
    int totalMale = 0;
    int totalFemale = 0;

    for (final log in _logs) {
      final payload = log.payload;
      if (payload != null) {
        // Add people count
        final peopleCount = payload['people_count'];
        if (peopleCount != null) {
          totalPeopleCount += (peopleCount is int ? peopleCount : int.tryParse(peopleCount.toString()) ?? 0);
        }

        // Add demographics
        final demographics = payload['demographics'];
        if (demographics != null && demographics is Map<String, dynamic>) {
          totalYoung += (demographics['total_young'] ?? 0) as int;
          totalAdult += (demographics['total_adult'] ?? 0) as int;
          totalSenior += (demographics['total_senior'] ?? 0) as int;
          totalMale += (demographics['total_male'] ?? 0) as int;
          totalFemale += (demographics['total_female'] ?? 0) as int;
        }
      }
    }

    return {
      'people_count': totalPeopleCount,
      'young': totalYoung,
      'adult': totalAdult,
      'senior': totalSenior,
      'male': totalMale,
      'female': totalFemale,
    };
  }

  Widget _buildTotalChip(String label, int value) {
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label:',
            style: TextStyle(
              fontSize: 13,
              color: Colors.grey.shade400,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            value.toString(),
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Communication Logs',
        showBackButton: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filter',
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loadLogs,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red.shade400),
            const SizedBox(height: 16),
            Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadLogs,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_logs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.inbox, size: 64, color: Colors.grey.shade600),
            const SizedBox(height: 16),
            Text(
              'No communication logs found',
              style: TextStyle(fontSize: 16, color: Colors.grey.shade400),
            ),
            if (_filterType != null || _filterStatus != null || _filterStartDate != null || _filterEndDate != null || _filterCameraIds.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: TextButton(
                  onPressed: () {
                    setState(() {
                      _filterType = null;
                      _filterStatus = null;
                      _filterTriggerIdController.clear();
                      _filterTenantNameController.clear();
                      _filterCameraIds.clear();
                      _filterStartDate = null;
                      _filterEndDate = null;
                      _currentPage = 1;
                    });
                    _loadLogs();
                  },
                  child: const Text('Clear Filters'),
                ),
              ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Header with stats
        Container(
          padding: const EdgeInsets.all(16),
          color: Colors.grey.shade900,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Total Logs: $_total',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  Row(
                    children: [
                      // Download button
                      IconButton(
                        onPressed: _isDownloading ? null : _downloadAllLogs,
                        icon: _isDownloading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.download),
                        tooltip: 'Download all filtered logs as CSV',
                        color: Colors.green.shade300,
                      ),
                      const SizedBox(width: 8),
                      if (_filterType != null || _filterStatus != null || _filterStartDate != null || _filterEndDate != null || _filterTriggerIdController.text.isNotEmpty || _filterTenantNameController.text.isNotEmpty || _filterCameraIds.isNotEmpty)
                        TextButton.icon(
                          onPressed: () {
                            setState(() {
                              _filterType = null;
                              _filterStatus = null;
                              _filterTriggerIdController.clear();
                              _filterTenantNameController.clear();
                              _filterCameraIds.clear();
                              _filterStartDate = null;
                              _filterEndDate = null;
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                          icon: const Icon(Icons.clear, size: 16),
                          label: const Text('Clear All Filters'),
                          style: TextButton.styleFrom(
                            foregroundColor: Colors.orange.shade300,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              // Active filters display
              if (_filterType != null || _filterStatus != null || _filterStartDate != null || _filterEndDate != null || _filterTriggerIdController.text.isNotEmpty || _filterTenantNameController.text.isNotEmpty || _filterCameraIds.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (_filterType != null)
                        Chip(
                          label: Text('Type: ${_filterType!.toUpperCase()}'),
                          backgroundColor: Colors.blue.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterType = null;
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      if (_filterStatus != null)
                        Chip(
                          label: Text('Status: ${_filterStatus!.toUpperCase()}'),
                          backgroundColor: Colors.green.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterStatus = null;
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      if (_filterTriggerIdController.text.isNotEmpty)
                        Chip(
                          label: Text('Trigger: ${_filterTriggerIdController.text.substring(0, _filterTriggerIdController.text.length > 8 ? 8 : _filterTriggerIdController.text.length)}...'),
                          backgroundColor: Colors.purple.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterTriggerIdController.clear();
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      if (_filterTenantNameController.text.isNotEmpty)
                        Chip(
                          label: Text('Tenant: ${_filterTenantNameController.text}'),
                          backgroundColor: Colors.teal.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterTenantNameController.clear();
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      // Multiple camera chips
                      for (final cameraId in _filterCameraIds)
                        Chip(
                          label: Text('Camera: $cameraId'),
                          backgroundColor: Colors.cyan.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterCameraIds.remove(cameraId);
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      if (_filterStartDate != null)
                        Chip(
                          label: Text('From: ${_filterStartDate!.year}-${_filterStartDate!.month.toString().padLeft(2, '0')}-${_filterStartDate!.day.toString().padLeft(2, '0')} ${_filterStartDate!.hour.toString().padLeft(2, '0')}:${_filterStartDate!.minute.toString().padLeft(2, '0')}'),
                          backgroundColor: Colors.orange.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterStartDate = null;
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                      if (_filterEndDate != null)
                        Chip(
                          label: Text('To: ${_filterEndDate!.year}-${_filterEndDate!.month.toString().padLeft(2, '0')}-${_filterEndDate!.day.toString().padLeft(2, '0')} ${_filterEndDate!.hour.toString().padLeft(2, '0')}:${_filterEndDate!.minute.toString().padLeft(2, '0')}'),
                          backgroundColor: Colors.orange.shade900,
                          deleteIcon: const Icon(Icons.close, size: 14),
                          onDeleted: () {
                            setState(() {
                              _filterEndDate = null;
                              _currentPage = 1;
                            });
                            _loadLogs();
                          },
                        ),
                    ],
                  ),
                ),
              // Demographics totals display
              Builder(
                builder: (context) {
                  final totals = _calculateTotals();
                  final hasDemographics = totals['people_count']! > 0;
                  
                  if (!hasDemographics) return const SizedBox.shrink();
                  
                  return Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade900.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue.shade700, width: 1),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.people, size: 16, color: Colors.blue),
                          const SizedBox(width: 8),
                          Text(
                            'Totals:',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.blue.shade300,
                            ),
                          ),
                          const SizedBox(width: 16),
                          _buildTotalChip('People', totals['people_count']!),
                          if (totals['young']! > 0) _buildTotalChip('Young', totals['young']!),
                          if (totals['adult']! > 0) _buildTotalChip('Adult', totals['adult']!),
                          if (totals['senior']! > 0) _buildTotalChip('Senior', totals['senior']!),
                          if (totals['male']! > 0) _buildTotalChip('Male', totals['male']!),
                          if (totals['female']! > 0) _buildTotalChip('Female', totals['female']!),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        
        // Logs list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _logs.length + (_hasMore ? 1 : 0),
            itemBuilder: (context, index) {
              if (index == _logs.length) {
                // Load More button
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: _isLoadingMore
                        ? const CircularProgressIndicator()
                        : ElevatedButton.icon(
                            onPressed: () {
                              setState(() => _currentPage++);
                              _loadLogs(loadMore: true);
                            },
                            icon: const Icon(Icons.expand_more),
                            label: const Text('Load More'),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                            ),
                          ),
                  ),
                );
              }
              return _buildLogCard(_logs[index]);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildLogCard(CommunicationLog log) {
    Color statusColor = _getStatusColor(log.status);
    Color typeColor = _getTypeColor(log.communicationType);
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: Colors.grey.shade900,
      child: InkWell(
        onTap: () => _showLogDetails(log),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  // Type badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: typeColor.withOpacity(0.2),
                      border: Border.all(color: typeColor),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      log.communicationType.toUpperCase(),
                      style: TextStyle(
                        color: typeColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Status badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.2),
                      border: Border.all(color: statusColor),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      log.status.toUpperCase(),
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const Spacer(),
                  Text(
                    _formatDateTimeString(log.createdAt),
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              
              // Content
              if (log.triggeredBy != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    'Triggered by: ${log.triggeredBy}',
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                ),
              if (log.recipient != null)
                Text(
                  'To: ${log.recipient}',
                  style: TextStyle(color: Colors.grey.shade300, fontSize: 14),
                ),
              if (log.subjectLine != null)
                Text(
                  'Subject: ${log.subjectLine}',
                  style: TextStyle(color: Colors.grey.shade300, fontSize: 14),
                ),
              // Display message for audit logs
              if (log.payload != null && log.payload!.containsKey('message'))
                Text(
                  'Message: ${log.payload!['message']}',
                  style: TextStyle(color: Colors.grey.shade300, fontSize: 14),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              if (log.payload != null && log.payload!.containsKey('url'))
                Text(
                  '${log.payload!['method'] ?? 'POST'} ${log.payload!['url']}',
                  style: TextStyle(color: Colors.grey.shade300, fontSize: 14),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              if (log.errorMessage != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Error: ${log.errorMessage}',
                    style: TextStyle(color: Colors.red.shade300, fontSize: 12),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              if (log.attempts > 1)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    'Attempts: ${log.attempts}',
                    style: TextStyle(color: Colors.orange.shade300, fontSize: 12),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }



  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'sent':
      case 'delivered':
        return Colors.green;
      case 'pending':
        return Colors.orange;
      case 'failed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Color _getTypeColor(String type) {
    switch (type.toLowerCase()) {
      case 'email':
        return Colors.green;
      case 'webhook':
        return Colors.blue;
      case 'audit':
      case 'audit_log':
        return Colors.orange;
      case 'push_notification':
        return Colors.purple;
      case 'sms':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  String _formatDateTime(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
        '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }

  String _formatDateTimeString(String isoString) {
    try {
      final dt = DateTime.parse(isoString);
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return isoString;
    }
  }
}
