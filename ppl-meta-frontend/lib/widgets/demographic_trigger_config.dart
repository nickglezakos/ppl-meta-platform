import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/signage_models.dart';

/// Widget for configuring demographic triggers and signage actions
class DemographicTriggerConfig extends StatefulWidget {
  final bool enableDemographic;
  final List<Map<String, dynamic>> demographicConditions;
  final List<String> selectedDeviceIds;
  final String? selectedPlaylistId;
  final String transitionMode;
  final int fadeDurationMs;
  final int cooldownSeconds;
  final List<DatabaseSignageDevice> availableDevices;
  final List<VideoList> availablePlaylists;
  final ValueChanged<bool> onEnableChanged;
  final ValueChanged<List<Map<String, dynamic>>> onConditionsChanged;
  final ValueChanged<List<String>> onDevicesChanged;
  final ValueChanged<String?> onPlaylistChanged;
  final ValueChanged<String> onTransitionModeChanged;
  final ValueChanged<int> onFadeDurationChanged;
  final ValueChanged<int> onCooldownChanged;

  const DemographicTriggerConfig({
    Key? key,
    required this.enableDemographic,
    required this.demographicConditions,
    required this.selectedDeviceIds,
    required this.selectedPlaylistId,
    required this.transitionMode,
    required this.fadeDurationMs,
    required this.cooldownSeconds,
    required this.availableDevices,
    required this.availablePlaylists,
    required this.onEnableChanged,
    required this.onConditionsChanged,
    required this.onDevicesChanged,
    required this.onPlaylistChanged,
    required this.onTransitionModeChanged,
    required this.onFadeDurationChanged,
    required this.onCooldownChanged,
  }) : super(key: key);

  @override
  State<DemographicTriggerConfig> createState() => _DemographicTriggerConfigState();
}

class _DemographicTriggerConfigState extends State<DemographicTriggerConfig> {
  final Map<String, String> _fieldLabels = {
    'people_count': 'People Count',
    'percent_male': 'Male %',
    'percent_female': 'Female %',
    'age_count_0_12': 'Age 0-12 Count',
    'age_count_13_17': 'Age 13-17 Count',
    'age_count_18_24': 'Age 18-24 Count',
    'age_count_25_34': 'Age 25-34 Count',
    'age_count_35_44': 'Age 35-44 Count',
    'age_count_45_54': 'Age 45-54 Count',
    'age_count_55_64': 'Age 55-64 Count',
    'age_count_65_plus': 'Age 65+ Count',
    // Backward compatibility for older stored trigger conditions.
    'percent_age_0_12': 'Age 0-12 Count',
    'percent_age_13_17': 'Age 13-17 Count',
    'percent_age_18_24': 'Age 18-24 Count',
    'percent_age_25_34': 'Age 25-34 Count',
    'percent_age_35_44': 'Age 35-44 Count',
    'percent_age_45_54': 'Age 45-54 Count',
    'percent_age_55_64': 'Age 55-64 Count',
    'percent_age_65_plus': 'Age 65+ Count',
  };

  final Map<String, String> _operatorLabels = {
    'gt': '>',
    'gte': '≥',
    'lt': '<',
    'lte': '≤',
    'eq': '=',
  };

  void _addCondition() {
    final newConditions = List<Map<String, dynamic>>.from(widget.demographicConditions);
    newConditions.add({
      'field': 'people_count',
      'operator': 'gte',
      'value': 1,
    });
    widget.onConditionsChanged(newConditions);
  }

  void _removeCondition(int index) {
    final newConditions = List<Map<String, dynamic>>.from(widget.demographicConditions);
    newConditions.removeAt(index);
    widget.onConditionsChanged(newConditions);
  }

  void _updateCondition(int index, String key, dynamic value) {
    final newConditions = List<Map<String, dynamic>>.from(widget.demographicConditions);
    newConditions[index] = Map<String, dynamic>.from(newConditions[index]);
    newConditions[index][key] = value;
    widget.onConditionsChanged(newConditions);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Enable/disable switch
        Card(
          color: widget.enableDemographic ? Colors.blue.shade900.withOpacity(0.3) : Colors.grey.shade900,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Icon(
                  Icons.psychology,
                  color: widget.enableDemographic ? Colors.blue : Colors.grey,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Intelligent Signage (Demographic Triggers)',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        widget.enableDemographic
                            ? 'Switch playlists based on real-time demographics'
                            : 'Enable to use camera demographics for signage control',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: widget.enableDemographic,
                  onChanged: widget.onEnableChanged,
                  activeColor: Colors.blue,
                ),
              ],
            ),
          ),
        ),
        
        if (widget.enableDemographic) ...[
          const SizedBox(height: 16),
          
          // Demographic conditions
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.tune, color: Colors.blue, size: 20),
                      const SizedBox(width: 8),
                      const Text(
                        'Demographic Conditions (All must match)',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.add_circle, color: Colors.blue),
                        onPressed: _addCondition,
                        tooltip: 'Add condition',
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  
                  if (widget.demographicConditions.isEmpty)
                    const Text(
                      'No conditions defined. Click + to add a condition.',
                      style: TextStyle(color: Colors.grey),
                    )
                  else
                    ...List.generate(widget.demographicConditions.length, (index) {
                      final condition = widget.demographicConditions[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          children: [
                            // Field selector
                            Expanded(
                              flex: 3,
                              child: DropdownButtonFormField<String>(
                                value: condition['field'],
                                decoration: const InputDecoration(
                                  labelText: 'Field',
                                  border: OutlineInputBorder(),
                                  isDense: true,
                                ),
                                items: _fieldLabels.entries.map((entry) {
                                  return DropdownMenuItem(
                                    value: entry.key,
                                    child: Text(entry.value, style: const TextStyle(fontSize: 12)),
                                  );
                                }).toList(),
                                onChanged: (value) => _updateCondition(index, 'field', value),
                              ),
                            ),
                            const SizedBox(width: 8),
                            
                            // Operator selector
                            Expanded(
                              flex: 2,
                              child: DropdownButtonFormField<String>(
                                value: condition['operator'],
                                decoration: const InputDecoration(
                                  labelText: 'Op',
                                  border: OutlineInputBorder(),
                                  isDense: true,
                                ),
                                items: _operatorLabels.entries.map((entry) {
                                  return DropdownMenuItem(
                                    value: entry.key,
                                    child: Text(entry.value, style: const TextStyle(fontSize: 14)),
                                  );
                                }).toList(),
                                onChanged: (value) => _updateCondition(index, 'operator', value),
                              ),
                            ),
                            const SizedBox(width: 8),
                            
                            // Value input
                            Expanded(
                              flex: 2,
                              child: TextFormField(
                                initialValue: condition['value'].toString(),
                                decoration: const InputDecoration(
                                  labelText: 'Value',
                                  border: OutlineInputBorder(),
                                  isDense: true,
                                ),
                                keyboardType: TextInputType.number,
                                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                                onChanged: (value) {
                                  final intValue = int.tryParse(value);
                                  if (intValue != null) {
                                    _updateCondition(index, 'value', intValue);
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: 8),
                            
                            // Remove button
                            IconButton(
                              icon: const Icon(Icons.remove_circle, color: Colors.red),
                              onPressed: () => _removeCondition(index),
                              tooltip: 'Remove condition',
                            ),
                          ],
                        ),
                      );
                    }),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // Signage device selection
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.devices, color: Colors.orange, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Target Signage Devices *',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  
                  if (widget.availableDevices.isEmpty)
                    const Text(
                      'No signage devices available. Register devices first.',
                      style: TextStyle(color: Colors.red),
                    )
                  else
                    ...widget.availableDevices.map((device) {
                      final isSelected = widget.selectedDeviceIds.contains(device.id);
                      return CheckboxListTile(
                        title: Text(device.name),
                        subtitle: Text('ID: ${device.id}', style: const TextStyle(fontSize: 10)),
                        value: isSelected,
                        dense: true,
                        onChanged: (selected) {
                          final newDeviceIds = List<String>.from(widget.selectedDeviceIds);
                          if (selected == true) {
                            newDeviceIds.add(device.id);
                          } else {
                            newDeviceIds.remove(device.id);
                          }
                          widget.onDevicesChanged(newDeviceIds);
                        },
                      );
                    }).toList(),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // Playlist selection
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.playlist_play, color: Colors.green, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Playlist to Play *',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  
                  if (widget.availablePlaylists.isEmpty)
                    const Text(
                      'No playlists available. Create a video list first.',
                      style: TextStyle(color: Colors.red),
                    )
                  else
                    DropdownButtonFormField<String>(
                      value: widget.selectedPlaylistId,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        hintText: 'Select a playlist',
                      ),
                      items: widget.availablePlaylists.map((playlist) {
                        return DropdownMenuItem(
                          value: playlist.id,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(playlist.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                              if (playlist.description != null)
                                Text(
                                  playlist.description!,
                                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                            ],
                          ),
                        );
                      }).toList(),
                      onChanged: widget.onPlaylistChanged,
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // Playback configuration
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.settings, color: Colors.purple, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Playback Configuration',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  
                  // Transition mode
                  DropdownButtonFormField<String>(
                    value: widget.transitionMode,
                    decoration: const InputDecoration(
                      labelText: 'Transition Mode',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'immediate', child: Text('Immediate')),
                      DropdownMenuItem(value: 'after_current', child: Text('After Current Video')),
                      DropdownMenuItem(value: 'fade', child: Text('Fade Transition')),
                    ],
                    onChanged: (value) => widget.onTransitionModeChanged(value!),
                  ),
                  const SizedBox(height: 12),
                  
                  // Fade duration (only if fade mode)
                  if (widget.transitionMode == 'fade')
                    TextFormField(
                      initialValue: widget.fadeDurationMs.toString(),
                      decoration: const InputDecoration(
                        labelText: 'Fade Duration (ms)',
                        border: OutlineInputBorder(),
                        helperText: 'Duration of fade effect in milliseconds',
                      ),
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      onChanged: (value) {
                        final intValue = int.tryParse(value);
                        if (intValue != null) {
                          widget.onFadeDurationChanged(intValue);
                        }
                      },
                    ),
                  const SizedBox(height: 12),
                  
                  // Cooldown
                  TextFormField(
                    initialValue: widget.cooldownSeconds.toString(),
                    decoration: const InputDecoration(
                      labelText: 'Cooldown (seconds)',
                      border: OutlineInputBorder(),
                      helperText: 'Minimum time between playlist switches',
                    ),
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    onChanged: (value) {
                      final intValue = int.tryParse(value);
                      if (intValue != null) {
                        widget.onCooldownChanged(intValue);
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
