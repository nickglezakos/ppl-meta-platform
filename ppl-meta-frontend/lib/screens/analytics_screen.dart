import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../widgets/analytics_dashboard.dart';

/// Analytics screen showing usage metrics and insights
class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  DateTime? _startDate;
  DateTime? _endDate;
  String? _selectedUserId;
  String? _selectedCollectionId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics'),
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: _showFilterDialog,
            icon: const Icon(Icons.filter_list),
            tooltip: 'Filter data',
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter summary bar
          if (_hasActiveFilters()) _buildFilterSummary(),
          
          // Analytics dashboard
          Expanded(
            child: AnalyticsDashboard(
              userId: _selectedUserId,
              collectionId: _selectedCollectionId,
              startDate: _startDate,
              endDate: _endDate,
            ),
          ),
        ],
      ),
    );
  }

  /// Check if any filters are active
  bool _hasActiveFilters() {
    return _startDate != null ||
           _endDate != null ||
           _selectedUserId != null ||
           _selectedCollectionId != null;
  }

  /// Build filter summary bar
  Widget _buildFilterSummary() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: const BoxDecoration(
        color: AppColors.surfaceVariant,
        border: Border(
          bottom: BorderSide(color: AppColors.border),
        ),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.filter_list,
            size: 16,
            color: AppColors.textSecondary,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Wrap(
              spacing: AppSpacing.sm,
              children: [
                if (_startDate != null || _endDate != null)
                  _FilterChip(
                    label: _getDateRangeText(),
                    onRemove: () {
                      setState(() {
                        _startDate = null;
                        _endDate = null;
                      });
                    },
                  ),
                if (_selectedUserId != null)
                  _FilterChip(
                    label: 'User: $_selectedUserId',
                    onRemove: () {
                      setState(() {
                        _selectedUserId = null;
                      });
                    },
                  ),
                if (_selectedCollectionId != null)
                  _FilterChip(
                    label: 'Collection: $_selectedCollectionId',
                    onRemove: () {
                      setState(() {
                        _selectedCollectionId = null;
                      });
                    },
                  ),
              ],
            ),
          ),
          TextButton(
            onPressed: _clearAllFilters,
            child: const Text('Clear All'),
          ),
        ],
      ),
    );
  }

  /// Get date range text for display
  String _getDateRangeText() {
    if (_startDate != null && _endDate != null) {
      return '${_formatDate(_startDate!)} - ${_formatDate(_endDate!)}';
    } else if (_startDate != null) {
      return 'From ${_formatDate(_startDate!)}';
    } else if (_endDate != null) {
      return 'Until ${_formatDate(_endDate!)}';
    }
    return '';
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }

  /// Show filter dialog
  Future<void> _showFilterDialog() async {
    await showDialog(
      context: context,
      builder: (context) => _FilterDialog(
        startDate: _startDate,
        endDate: _endDate,
        selectedUserId: _selectedUserId,
        selectedCollectionId: _selectedCollectionId,
        onApply: (startDate, endDate, userId, collectionId) {
          setState(() {
            _startDate = startDate;
            _endDate = endDate;
            _selectedUserId = userId;
            _selectedCollectionId = collectionId;
          });
        },
      ),
    );
  }

  /// Clear all filters
  void _clearAllFilters() {
    setState(() {
      _startDate = null;
      _endDate = null;
      _selectedUserId = null;
      _selectedCollectionId = null;
    });
  }
}

/// Filter chip widget
class _FilterChip extends StatelessWidget {
  final String label;
  final VoidCallback onRemove;

  const _FilterChip({
    required this.label,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(
        label,
        style: AppTextStyles.bodySmall,
      ),
      deleteIcon: const Icon(Icons.close, size: 16),
      onDeleted: onRemove,
      backgroundColor: AppColors.primary.withOpacity(0.1),
      deleteIconColor: AppColors.primary,
    );
  }
}

/// Filter dialog
class _FilterDialog extends StatefulWidget {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? selectedUserId;
  final String? selectedCollectionId;
  final Function(DateTime?, DateTime?, String?, String?) onApply;

  const _FilterDialog({
    this.startDate,
    this.endDate,
    this.selectedUserId,
    this.selectedCollectionId,
    required this.onApply,
  });

  @override
  State<_FilterDialog> createState() => _FilterDialogState();
}

class _FilterDialogState extends State<_FilterDialog> {
  DateTime? _startDate;
  DateTime? _endDate;
  String? _selectedUserId;
  String? _selectedCollectionId;

  @override
  void initState() {
    super.initState();
    _startDate = widget.startDate;
    _endDate = widget.endDate;
    _selectedUserId = widget.selectedUserId;
    _selectedCollectionId = widget.selectedCollectionId;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Filter Analytics'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Date range
            Text(
              'Date Range',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _selectDate(true),
                    child: Text(
                      _startDate != null
                          ? 'From: ${_formatDate(_startDate!)}'
                          : 'Start Date',
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _selectDate(false),
                    child: Text(
                      _endDate != null
                          ? 'To: ${_formatDate(_endDate!)}'
                          : 'End Date',
                    ),
                  ),
                ),
              ],
            ),
            
            // Quick date filters
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              children: [
                ActionChip(
                  label: const Text('Last 7 days'),
                  onPressed: () => _setQuickDateRange(7),
                ),
                ActionChip(
                  label: const Text('Last 30 days'),
                  onPressed: () => _setQuickDateRange(30),
                ),
                ActionChip(
                  label: const Text('Last 90 days'),
                  onPressed: () => _setQuickDateRange(90),
                ),
              ],
            ),
            
            const SizedBox(height: AppSpacing.lg),
            
            // User filter
            Text(
              'User',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            DropdownButtonFormField<String>(
              value: _selectedUserId,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Select user',
              ),
              items: const [
                DropdownMenuItem(
                  value: null,
                  child: Text('All users'),
                ),
                DropdownMenuItem(
                  value: 'user1',
                  child: Text('John Doe'),
                ),
                DropdownMenuItem(
                  value: 'user2',
                  child: Text('Jane Smith'),
                ),
                DropdownMenuItem(
                  value: 'user3',
                  child: Text('Bob Johnson'),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedUserId = value;
                });
              },
            ),
            
            const SizedBox(height: AppSpacing.lg),
            
            // Collection filter
            Text(
              'Collection',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            DropdownButtonFormField<String>(
              value: _selectedCollectionId,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Select collection',
              ),
              items: const [
                DropdownMenuItem(
                  value: null,
                  child: Text('All collections'),
                ),
                DropdownMenuItem(
                  value: 'collection1',
                  child: Text('Work Documents'),
                ),
                DropdownMenuItem(
                  value: 'collection2',
                  child: Text('Family Photos'),
                ),
                DropdownMenuItem(
                  value: 'collection3',
                  child: Text('Project Assets'),
                ),
              ],
              onChanged: (value) {
                setState(() {
                  _selectedCollectionId = value;
                });
              },
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            widget.onApply(
              _startDate,
              _endDate,
              _selectedUserId,
              _selectedCollectionId,
            );
            Navigator.pop(context);
          },
          child: const Text('Apply'),
        ),
      ],
    );
  }

  /// Select date
  Future<void> _selectDate(bool isStartDate) async {
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: isStartDate
          ? (_startDate ?? DateTime.now())
          : (_endDate ?? DateTime.now()),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );

    if (selectedDate != null) {
      setState(() {
        if (isStartDate) {
          _startDate = selectedDate;
        } else {
          _endDate = selectedDate;
        }
      });
    }
  }

  /// Set quick date range
  void _setQuickDateRange(int days) {
    final now = DateTime.now();
    setState(() {
      _startDate = now.subtract(Duration(days: days));
      _endDate = now;
    });
  }

  /// Format date for display
  String _formatDate(DateTime date) {
    return '${date.month}/${date.day}/${date.year}';
  }
}
