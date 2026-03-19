import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Collections Search Dialog with Date/Time filtering
/// 
/// Simplified search interface for collections screen that allows filtering
/// by date and time range (with minute precision).
class CollectionsSearchDialog extends StatefulWidget {
  final DateTime? initialStartDate;
  final DateTime? initialEndDate;
  final Function(DateTime?, DateTime?) onApply;

  const CollectionsSearchDialog({
    super.key,
    this.initialStartDate,
    this.initialEndDate,
    required this.onApply,
  });

  @override
  State<CollectionsSearchDialog> createState() => _CollectionsSearchDialogState();
}

class _CollectionsSearchDialogState extends State<CollectionsSearchDialog> {
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _startDate = widget.initialStartDate;
    _endDate = widget.initialEndDate;
  }

  /// Select date and time for start or end
  Future<void> _selectDateTime(bool isStart) async {
    final now = DateTime.now();
    final initialDateTime = isStart ? (_startDate ?? now) : (_endDate ?? now);
    
    // First, show date picker
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: initialDateTime,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );

    if (selectedDate == null) return;

    // Then, show time picker
    final selectedTime = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initialDateTime),
    );

    if (selectedTime == null) return;

    // Combine date and time
    final combined = DateTime(
      selectedDate.year,
      selectedDate.month,
      selectedDate.day,
      selectedTime.hour,
      selectedTime.minute,
    );

    setState(() {
      if (isStart) {
        _startDate = combined;
      } else {
        _endDate = combined;
      }
    });
  }

  /// Set quick date range (last N days)
  void _setQuickDateRange(int days) {
    final now = DateTime.now();
    setState(() {
      _startDate = now.subtract(Duration(days: days));
      _endDate = now;
    });
  }

  /// Clear all filters
  void _clearFilters() {
    setState(() {
      _startDate = null;
      _endDate = null;
    });
  }

  /// Format date/time for display
  String _formatDateTime(DateTime? dateTime) {
    if (dateTime == null) return 'Not set';
    return '${dateTime.month}/${dateTime.day}/${dateTime.year} '
           '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Filter Collections by Date/Time'),
      content: SizedBox(
        width: 450,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Date/Time Range Section
            Text(
              'Date & Time Range',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            
            // Start Date/Time
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _selectDateTime(true),
                    icon: const Icon(Icons.calendar_today, size: 18),
                    label: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Start Date & Time',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                        Text(
                          _formatDateTime(_startDate),
                          style: AppTextStyles.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            
            // End Date/Time
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _selectDateTime(false),
                    icon: const Icon(Icons.calendar_today, size: 18),
                    label: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'End Date & Time',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                        Text(
                          _formatDateTime(_endDate),
                          style: AppTextStyles.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            
            // Quick Filters
            Text(
              'Quick Filters',
              style: AppTextStyles.labelLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                ActionChip(
                  label: const Text('Last 24 hours'),
                  onPressed: () => _setQuickDateRange(1),
                ),
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
          ],
        ),
      ),
      actions: [
        // Clear Button
        TextButton(
          onPressed: () {
            _clearFilters();
          },
          child: const Text('Clear'),
        ),
        
        // Cancel Button
        TextButton(
          onPressed: () {
            Navigator.of(context).pop();
          },
          child: const Text('Cancel'),
        ),
        
        // Apply Button
        FilledButton(
          onPressed: () {
            widget.onApply(_startDate, _endDate);
            Navigator.of(context).pop();
          },
          child: const Text('Apply'),
        ),
      ],
    );
  }
}
