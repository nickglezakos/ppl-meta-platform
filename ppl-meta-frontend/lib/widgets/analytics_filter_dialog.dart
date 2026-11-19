import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../core/theme/app_theme.dart';

/// Reusable filter dialog used by Analytics and People-profile search.
///
/// Visibility flags hide sections for restricted entry points (e.g. people
/// search shows data source + time + cameras only).
class AnalyticsFilterDialog extends StatefulWidget {
  final String currentTimeFilter;
  final List<String> selectedCollectionIds;
  final List<String> selectedGenders;
  final List<String> selectedAgeGroups;
  final String dataSource;
  final String detectionModality;
  final bool autoRefresh;
  final List<Map<String, dynamic>> cameras;
  final DateTime? startDate;
  final DateTime? endDate;

  final bool showDataSource;
  final bool allowBothDataSources;
  final bool showDetectionModality;
  final bool showDemographics;
  final bool showAgeGroups;
  final bool showAutoRefresh;
  final String selectionLabel;
  final String title;

  const AnalyticsFilterDialog({
    super.key,
    required this.currentTimeFilter,
    required this.selectedCollectionIds,
    required this.selectedGenders,
    required this.selectedAgeGroups,
    this.dataSource = 'recording',
    this.detectionModality = 'face',
    required this.autoRefresh,
    required this.cameras,
    this.startDate,
    this.endDate,
    this.showDataSource = true,
    this.allowBothDataSources = false,
    this.showDetectionModality = true,
    this.showDemographics = true,
    this.showAgeGroups = true,
    this.showAutoRefresh = true,
    this.selectionLabel = 'Collections',
    this.title = 'Filter Analytics',
  });

  @override
  State<AnalyticsFilterDialog> createState() => _AnalyticsFilterDialogState();
}

class _AnalyticsFilterDialogState extends State<AnalyticsFilterDialog> {
  late String _timeFilter;
  late List<String> _selectedCollectionIds;
  late List<String> _selectedGenders;
  late List<String> _selectedAgeGroups;
  late String _dataSource;
  late String _detectionModality;
  late bool _autoRefresh;
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _timeFilter = widget.currentTimeFilter;
    _selectedCollectionIds = List.from(widget.selectedCollectionIds);
    _selectedGenders = List.from(widget.selectedGenders);
    _selectedAgeGroups = List.from(widget.selectedAgeGroups);
    _dataSource = widget.dataSource;
    _detectionModality = widget.detectionModality;
    _autoRefresh = widget.autoRefresh;
    _startDate = widget.startDate;
    _endDate = widget.endDate;
  }

  Future<void> _pickDateTime({required bool isStart}) async {
    final now = DateTime.now();
    final initialDate = isStart
        ? (_startDate ?? now.subtract(const Duration(days: 7)))
        : (_endDate ?? now);

    final date = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(2020),
      lastDate: now,
    );
    if (date == null) return;

    if (!mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initialDate),
    );
    if (time == null) return;

    final picked =
        DateTime(date.year, date.month, date.day, time.hour, time.minute);
    setState(() {
      if (isStart) {
        _startDate = picked;
      } else {
        _endDate = picked;
      }
    });
  }

  String get _dataSourceHint {
    switch (_dataSource) {
      case 'instant_detection':
        return 'Analytics from real-time instant detection sessions';
      case 'both':
        return 'Search both video recording and instant detection data';
      default:
        return 'Analytics from video recording sessions (default)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final labelLower = widget.selectionLabel.toLowerCase();
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 500,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (widget.showDataSource) ...[
                const Text(
                  'Data Source',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('Video Recording'),
                      selected: _dataSource == 'recording',
                      onSelected: (_) =>
                          setState(() => _dataSource = 'recording'),
                      selectedColor: Colors.blue.shade100,
                      avatar: _dataSource == 'recording'
                          ? const Icon(Icons.videocam, size: 18)
                          : const Icon(Icons.videocam_outlined, size: 18),
                    ),
                    ChoiceChip(
                      label: const Text('Instant Detection'),
                      selected: _dataSource == 'instant_detection',
                      onSelected: (_) =>
                          setState(() => _dataSource = 'instant_detection'),
                      selectedColor: Colors.orange.shade100,
                      avatar: _dataSource == 'instant_detection'
                          ? const Icon(Icons.visibility, size: 18)
                          : const Icon(Icons.visibility_outlined, size: 18),
                    ),
                    if (widget.allowBothDataSources)
                      ChoiceChip(
                        label: const Text('Both'),
                        selected: _dataSource == 'both',
                        onSelected: (_) =>
                            setState(() => _dataSource = 'both'),
                        selectedColor: Colors.purple.shade100,
                        avatar: _dataSource == 'both'
                            ? const Icon(Icons.merge_type, size: 18)
                            : const Icon(Icons.merge_type_outlined, size: 18),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  _dataSourceHint,
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),
                const SizedBox(height: 20),
              ],
              if (widget.showDetectionModality) ...[
                const Text(
                  'Detection Modality',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('Face'),
                      selected: _detectionModality == 'face',
                      onSelected: (_) =>
                          setState(() => _detectionModality = 'face'),
                      selectedColor: Colors.teal.shade100,
                    ),
                    ChoiceChip(
                      label: const Text('Body'),
                      selected: _detectionModality == 'body',
                      onSelected: (_) =>
                          setState(() => _detectionModality = 'body'),
                      selectedColor: Colors.teal.shade100,
                    ),
                    ChoiceChip(
                      label: const Text('Both'),
                      selected: _detectionModality == 'both',
                      onSelected: (_) =>
                          setState(() => _detectionModality = 'both'),
                      selectedColor: Colors.teal.shade100,
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  _detectionModality == 'face'
                      ? 'Count face MVR people only (default)'
                      : _detectionModality == 'body'
                          ? 'Count body MVR people only'
                          : 'Merge overlapping face and body tracks into one person',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),
                const SizedBox(height: 20),
              ],
              const Text(
                'Time Range',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildFilterChip('Today', 'today'),
                  _buildFilterChip('Last Hour', 'last_hour'),
                  _buildFilterChip('Last 3 Hours', 'last_3_hours'),
                  _buildFilterChip('Last Week', 'last_week'),
                  _buildFilterChip('Last Month', 'last_month'),
                  _buildFilterChip('Custom Range', 'custom'),
                ],
              ),
              if (_timeFilter == 'custom') ...[
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDateTime(isStart: true),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _startDate != null
                              ? DateFormat('MMM d, yyyy HH:mm')
                                  .format(_startDate!)
                              : 'Start Date',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Icon(Icons.arrow_forward,
                          size: 16, color: Colors.grey),
                    ),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickDateTime(isStart: false),
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _endDate != null
                              ? DateFormat('MMM d, yyyy HH:mm')
                                  .format(_endDate!)
                              : 'End Date',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                  ],
                ),
                if (_startDate == null || _endDate == null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      'Please select both start and end dates',
                      style: TextStyle(
                          fontSize: 12, color: Colors.orange.shade700),
                    ),
                  ),
              ],
              const SizedBox(height: 24),
              Row(
                children: [
                  Text(
                    widget.selectionLabel,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _selectedCollectionIds.clear();
                      });
                    },
                    child: const Text('Clear'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                _selectedCollectionIds.isEmpty
                    ? 'All $labelLower (${widget.cameras.length})'
                    : '${_selectedCollectionIds.length} selected',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 12),
              Container(
                constraints: const BoxConstraints(maxHeight: 200),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ListView(
                  shrinkWrap: true,
                  children: widget.cameras.map((camera) {
                    final id = (camera['id'] ??
                                camera['collection_name'] ??
                                camera['name'] ??
                                camera['uuid'] ??
                                camera['device_id'] ??
                                camera['camera_device_id'])
                            ?.toString() ??
                        '';
                    final name = (camera['name'] ??
                            camera['collection_name'] ??
                            camera['device_id'] ??
                            camera['camera_device_id'] ??
                            id)
                        .toString();
                    final isSelected = _selectedCollectionIds.contains(id);

                    return CheckboxListTile(
                      dense: true,
                      title: Text(name),
                      value: isSelected,
                      onChanged: (checked) {
                        setState(() {
                          if (checked == true) {
                            if (!_selectedCollectionIds.contains(id)) {
                              _selectedCollectionIds.add(id);
                            }
                          } else {
                            _selectedCollectionIds.remove(id);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ),
              if (widget.showDemographics || widget.showAgeGroups) ...[
                const SizedBox(height: 24),
                const Text(
                  'Demographics',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                if (widget.showDemographics) ...[
                  const Text(
                    'Gender',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _buildDemographicChip('Male', 'male', _selectedGenders),
                      _buildDemographicChip(
                          'Female', 'female', _selectedGenders),
                    ],
                  ),
                ],
                if (widget.showAgeGroups) ...[
                  if (widget.showDemographics) const SizedBox(height: 16),
                  const Text(
                    'Age Group',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _buildDemographicChip(
                          'Young (0-25)', 'young', _selectedAgeGroups),
                      _buildDemographicChip(
                          'Adult (26-65)', 'adult', _selectedAgeGroups),
                      _buildDemographicChip(
                          'Elderly (65+)', 'elderly', _selectedAgeGroups),
                    ],
                  ),
                ],
              ],
              if (widget.showAutoRefresh) ...[
                const SizedBox(height: 24),
                SwitchListTile(
                  title: const Text('Auto-refresh (10 min)'),
                  subtitle: const Text('Automatically update data'),
                  value: _autoRefresh,
                  onChanged: (value) {
                    setState(() {
                      _autoRefresh = value;
                    });
                  },
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            if (_timeFilter == 'custom' &&
                (_startDate == null || _endDate == null)) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text(
                        'Please select both start and end dates for custom range')),
              );
              return;
            }
            Navigator.pop(context, {
              'timeFilter': _timeFilter,
              'collectionIds': _selectedCollectionIds,
              'genders': _selectedGenders,
              'ageGroups': _selectedAgeGroups,
              'dataSource': _dataSource,
              'detectionModality': _detectionModality,
              'autoRefresh': _autoRefresh,
              'startDate': _timeFilter == 'custom' ? _startDate : null,
              'endDate': _timeFilter == 'custom' ? _endDate : null,
            });
          },
          child: const Text('Apply'),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _timeFilter == value;
    return ChoiceChip(
      label: Text(
        label,
        style: TextStyle(
          color: isSelected ? AppColors.primary : Colors.grey.shade700,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _timeFilter = value;
          });
        }
      },
      selectedColor: AppColors.primary.withOpacity(0.1),
      backgroundColor: Colors.grey.shade200,
    );
  }

  Widget _buildDemographicChip(
      String label, String value, List<String> selectedList) {
    final isSelected = selectedList.contains(value);
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        setState(() {
          if (selected) {
            selectedList.add(value);
          } else {
            selectedList.remove(value);
          }
        });
      },
      selectedColor: AppColors.primary.withOpacity(0.2),
      backgroundColor: Colors.grey.shade200,
      checkmarkColor: AppColors.primary,
    );
  }
}
