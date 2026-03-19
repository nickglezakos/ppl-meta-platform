/// Camera Search Dialog for Individual Groups
/// Allows users to search for group members within specific camera footage
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/collection_models.dart' show MediaCollection;
import '../../core/providers/camera_providers.dart';

class CameraSearchDialog extends ConsumerStatefulWidget {
  final String groupId;
  final String groupName;
  final int memberCount;

  const CameraSearchDialog({
    super.key,
    required this.groupId,
    required this.groupName,
    required this.memberCount,
  });

  @override
  ConsumerState<CameraSearchDialog> createState() =>
      _CameraSearchDialogState();
}

class _CameraSearchDialogState extends ConsumerState<CameraSearchDialog> {
  List<MediaCollection> _cameraCollections = [];
  bool _isLoadingCollections = true;
  Set<String> _selectedCollectionIds = {};
  DateTime? _startTime;
  DateTime? _endTime;
  bool _isSearching = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    // Delay provider modification until after widget tree is built
    Future(() => _loadCameraCollections());
    _endTime = DateTime.now();
    _startTime = _endTime!.subtract(const Duration(hours: 24));
  }

  Future<void> _loadCameraCollections() async {
    setState(() {
      _isLoadingCollections = true;
      _errorMessage = null;
    });

    try {
      await ref.read(cameraCollectionProvider.notifier).loadCollectionsAndMappings();
      
      final collectionState = ref.read(cameraCollectionProvider);
      final cameraCollections = collectionState.collections.where((collection) {
        final metadata = collection.metadata;
        if (metadata != null) {
          return metadata['collection_type'] == 'camera_snapshots' ||
                 metadata['camera_id'] != null;
        }
        final nameLower = collection.name.toLowerCase();
        return nameLower.contains('camera') ||
               nameLower.contains('usb_') ||
               nameLower.contains('rtsp') ||
               nameLower.endsWith(' collection');
      }).toList();
      
      cameraCollections.sort((a, b) {
        final aDate = a.createdAt ?? DateTime(1970);
        final bDate = b.createdAt ?? DateTime(1970);
        return bDate.compareTo(aDate);
      });
      
      setState(() {
        _cameraCollections = cameraCollections;
        _isLoadingCollections = false;
        _selectedCollectionIds = {};
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Error loading camera collections: $e';
        _isLoadingCollections = false;
      });
    }
  }

  String _formatDateTime(DateTime? dateTime) {
    if (dateTime == null) return 'Not set';
    return '${dateTime.month}/${dateTime.day}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  void _setQuickTimeRange(String range) {
    final now = DateTime.now();
    setState(() {
      _endTime = now;
      switch (range) {
        case 'last_hour':
          _startTime = now.subtract(const Duration(hours: 1));
          break;
        case 'last_6_hours':
          _startTime = now.subtract(const Duration(hours: 6));
          break;
        case 'today':
          _startTime = DateTime(now.year, now.month, now.day);
          break;
        case 'yesterday':
          final yesterday = now.subtract(const Duration(days: 1));
          _startTime = DateTime(yesterday.year, yesterday.month, yesterday.day);
          _endTime = DateTime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59);
          break;
        case 'last_7_days':
          _startTime = now.subtract(const Duration(days: 7));
          break;
      }
    });
  }

  Future<void> _pickDateTime(bool isStartTime) async {
    final currentValue = isStartTime ? _startTime : _endTime;
    
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: currentValue ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );

    if (selectedDate != null && mounted) {
      final selectedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(currentValue ?? DateTime.now()),
      );

      if (selectedTime != null && mounted) {
        final dateTime = DateTime(
          selectedDate.year,
          selectedDate.month,
          selectedDate.day,
          selectedTime.hour,
          selectedTime.minute,
        );
        
        setState(() {
          if (isStartTime) {
            _startTime = dateTime;
            print('📅 Start Time Updated: ${_startTime!.month}/${_startTime!.day}/${_startTime!.year} ${_startTime!.hour}:${_startTime!.minute}');
          } else {
            _endTime = dateTime;
            print('📅 End Time Updated: ${_endTime!.month}/${_endTime!.day}/${_endTime!.year} ${_endTime!.hour}:${_endTime!.minute}');
          }
        });
      }
    }
  }

  Future<void> _executeSearch() async {
    if (_selectedCollectionIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select at least one camera collection'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (_startTime == null || _endTime == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select a time range'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (_endTime!.isBefore(_startTime!)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('End time must be after start time'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final selectedCollections = _cameraCollections
        .where((c) => _selectedCollectionIds.contains(c.id))
        .toList();
    
    final cameraIds = selectedCollections.map((c) => c.name).toList();
    final cameraNames = selectedCollections.map((c) => c.name).toList();
    
    // Convert to UTC and format as ISO8601 with timezone
    final startTimeStr = _startTime!.toUtc().toIso8601String();
    final endTimeStr = _endTime!.toUtc().toIso8601String();
    
    // Debug logging
    print('🔍 Camera Search - Start Time (Local): ${_startTime!.toIso8601String()}');
    print('🔍 Camera Search - Start Time (UTC): $startTimeStr');
    print('🔍 Camera Search - End Time (Local): ${_endTime!.toIso8601String()}');
    print('🔍 Camera Search - End Time (UTC): $endTimeStr');
    print('🔍 Camera Search - Collections: ${cameraIds.join(", ")}');
    
    Navigator.of(context).pop({
      'camera_ids': cameraIds,
      'camera_names': cameraNames,
      'start_time': startTimeStr,
      'end_time': endTimeStr,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 500,
        constraints: const BoxConstraints(maxHeight: 600),
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.video_camera_front,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Search for ${widget.groupName} Members',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text(
                          'Find which members appeared in camera footage',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                              ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                '📷 Select Camera Collection',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              if (_isLoadingCollections)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: Colors.red),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                )
              else if (_cameraCollections.isEmpty)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.warning_amber, color: Colors.orange),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'No camera collections found. Make sure cameras are properly configured.',
                          style: TextStyle(color: Colors.orange),
                        ),
                      ),
                    ],
                  ),
                )
              else
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline,
                              size: 20, color: Colors.blue),
                          const SizedBox(width: 8),
                          Text(
                            '${_selectedCollectionIds.length} of ${_cameraCollections.length} selected',
                            style: const TextStyle(color: Colors.blue),
                          ),
                          const Spacer(),
                          TextButton.icon(
                            onPressed: () {
                              setState(() {
                                if (_selectedCollectionIds.length ==
                                    _cameraCollections.length) {
                                  _selectedCollectionIds.clear();
                                } else {
                                  _selectedCollectionIds =
                                      _cameraCollections.map((c) => c.id).toSet();
                                }
                              });
                            },
                            icon: Icon(
                              _selectedCollectionIds.length ==
                                      _cameraCollections.length
                                  ? Icons.deselect
                                  : Icons.select_all,
                              size: 18,
                            ),
                            label: const Text('Toggle All'),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      constraints: const BoxConstraints(maxHeight: 200),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey.shade300),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: _cameraCollections.length,
                        itemBuilder: (context, index) {
                          final collection = _cameraCollections[index];
                          final isSelected =
                              _selectedCollectionIds.contains(collection.id);

                          return CheckboxListTile(
                            value: isSelected,
                            onChanged: (value) {
                              setState(() {
                                if (value == true) {
                                  _selectedCollectionIds.add(collection.id);
                                } else {
                                  _selectedCollectionIds.remove(collection.id);
                                }
                              });
                            },
                            title: Text(collection.name),
                            subtitle: Text(
                              'Created: ${_formatDateTime(collection.createdAt)}',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[600],
                              ),
                            ),
                            secondary: Icon(
                              Icons.videocam,
                              color: isSelected
                                  ? Theme.of(context).colorScheme.primary
                                  : Colors.grey,
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 24),
              Text(
                '🕐 Time Range',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Column(
                children: [
                  // Start Time Field
                  InkWell(
                    onTap: () => _pickDateTime(true),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
                        ),
                        borderRadius: BorderRadius.circular(8),
                        color: Theme.of(context).colorScheme.surface,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Start Time',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Icon(
                                Icons.calendar_today,
                                size: 18,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _startTime != null
                                      ? '${_startTime!.month}/${_startTime!.day}/${_startTime!.year} ${_startTime!.hour}:${_startTime!.minute.toString().padLeft(2, '0')}'
                                      : 'Select start date and time',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: _startTime != null 
                                        ? Theme.of(context).colorScheme.onSurface
                                        : Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                                    fontWeight: _startTime != null ? FontWeight.w600 : FontWeight.normal,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  // End Time Field
                  InkWell(
                    onTap: () => _pickDateTime(false),
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
                        ),
                        borderRadius: BorderRadius.circular(8),
                        color: Theme.of(context).colorScheme.surface,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'End Time',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Icon(
                                Icons.calendar_today,
                                size: 18,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _endTime != null
                                      ? '${_endTime!.month}/${_endTime!.day}/${_endTime!.year} ${_endTime!.hour}:${_endTime!.minute.toString().padLeft(2, '0')}'
                                      : 'Select end date and time',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: _endTime != null 
                                        ? Theme.of(context).colorScheme.onSurface
                                        : Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                                    fontWeight: _endTime != null ? FontWeight.w600 : FontWeight.normal,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _QuickRangeButton('Last Hour', 'last_hour', _setQuickTimeRange),
                  _QuickRangeButton('Last 6 Hours', 'last_6_hours', _setQuickTimeRange),
                  _QuickRangeButton('Today', 'today', _setQuickTimeRange),
                  _QuickRangeButton('Yesterday', 'yesterday', _setQuickTimeRange),
                  _QuickRangeButton('Last 7 Days', 'last_7_days', _setQuickTimeRange),
                ],
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.people, color: Colors.green),
                    const SizedBox(width: 12),
                    Text(
                      'Searching ${widget.memberCount} group ${widget.memberCount == 1 ? 'member' : 'members'}',
                      style: const TextStyle(color: Colors.green),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: _isSearching ? null : _executeSearch,
                    icon: _isSearching
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                            ),
                          )
                        : const Icon(Icons.search),
                    label: Text(_isSearching ? 'Searching...' : 'Search'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TimePickerField extends StatelessWidget {
  final String label;
  final DateTime? value;
  final VoidCallback onTap;

  const _TimePickerField({
    super.key,
    required this.label,
    required this.value,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(
                  Icons.access_time,
                  size: 16,
                  color: Colors.grey[600],
                ),
                const SizedBox(width: 8),
                Text(
                  value == null
                      ? 'Select $label'
                      : _formatDateTime(value!),
                  style: TextStyle(
                    color: value == null ? Colors.grey[600] : Colors.black,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.month}/${dateTime.day}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}

class _QuickRangeButton extends StatelessWidget {
  final String label;
  final String range;
  final Function(String) onPressed;

  const _QuickRangeButton(this.label, this.range, this.onPressed);

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: () => onPressed(range),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      child: Text(label),
    );
  }
}
