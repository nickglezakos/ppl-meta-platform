import 'package:flutter/material.dart';

/// Widget for streaming quality and settings controls
class StreamingControls extends StatefulWidget {
  final String quality;
  final int fps;
  final String resolution;
  final ValueChanged<Map<String, dynamic>> onSettingsChanged;
  final bool isEnabled;

  const StreamingControls({
    super.key,
    required this.quality,
    required this.fps,
    required this.resolution,
    required this.onSettingsChanged,
    this.isEnabled = true,
  });

  @override
  State<StreamingControls> createState() => _StreamingControlsState();
}

class _StreamingControlsState extends State<StreamingControls> {
  late String _quality;
  late int _fps;
  late String _resolution;

  static const List<String> _qualityOptions = ['low', 'medium', 'high'];
  static const List<int> _fpsOptions = [15, 30, 60];
  static const List<String> _resolutionOptions = [
    '640x480',
    '1280x720',
    '1920x1080',
  ];

  @override
  void initState() {
    super.initState();
    _quality = widget.quality;
    _fps = widget.fps;
    _resolution = widget.resolution;
  }

  @override
  void didUpdateWidget(StreamingControls oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.quality != widget.quality ||
        oldWidget.fps != widget.fps ||
        oldWidget.resolution != widget.resolution) {
      _quality = widget.quality;
      _fps = widget.fps;
      _resolution = widget.resolution;
    }
  }

  void _notifySettingsChanged() {
    widget.onSettingsChanged({
      'quality': _quality,
      'fps': _fps,
      'resolution': _resolution,
    });
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.tune,
                  color: colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Stream Settings',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Quality Control
            _SettingRow(
              label: 'Quality',
              child: SegmentedButton<String>(
                segments: _qualityOptions.map((quality) {
                  return ButtonSegment<String>(
                    value: quality,
                    label: Text(quality.toUpperCase()),
                    icon: Icon(_getQualityIcon(quality), size: 16),
                  );
                }).toList(),
                selected: {_quality},
                onSelectionChanged: widget.isEnabled ? (selection) {
                  setState(() {
                    _quality = selection.first;
                  });
                  _notifySettingsChanged();
                } : null,
                style: SegmentedButton.styleFrom(
                  selectedBackgroundColor: colorScheme.primary.withValues(alpha: 0.1),
                  selectedForegroundColor: colorScheme.primary,
                ),
              ),
            ),

            const SizedBox(height: 12),

            // FPS Control
            _SettingRow(
              label: 'FPS',
              child: SegmentedButton<int>(
                segments: _fpsOptions.map((fps) {
                  return ButtonSegment<int>(
                    value: fps,
                    label: Text('$fps'),
                  );
                }).toList(),
                selected: {_fps},
                onSelectionChanged: widget.isEnabled ? (selection) {
                  setState(() {
                    _fps = selection.first;
                  });
                  _notifySettingsChanged();
                } : null,
                style: SegmentedButton.styleFrom(
                  selectedBackgroundColor: colorScheme.primary.withValues(alpha: 0.1),
                  selectedForegroundColor: colorScheme.primary,
                ),
              ),
            ),

            const SizedBox(height: 12),

            // Resolution Control
            _SettingRow(
              label: 'Resolution',
              child: DropdownButtonFormField<String>(
                value: _resolution,
                decoration: InputDecoration(
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                ),
                items: _resolutionOptions.map((resolution) {
                  return DropdownMenuItem(
                    value: resolution,
                    child: Text(resolution),
                  );
                }).toList(),
                onChanged: widget.isEnabled ? (value) {
                  if (value != null) {
                    setState(() {
                      _resolution = value;
                    });
                    _notifySettingsChanged();
                  }
                } : null,
              ),
            ),

            const SizedBox(height: 16),

            // Quality Description
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: colorScheme.outline.withValues(alpha: 0.2),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.info_outline,
                    size: 16,
                    color: colorScheme.outline,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _getQualityDescription(_quality),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colorScheme.outline,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getQualityIcon(String quality) {
    switch (quality) {
      case 'low':
        return Icons.signal_cellular_alt_1_bar;
      case 'medium':
        return Icons.signal_cellular_alt_2_bar;
      case 'high':
        return Icons.signal_cellular_4_bar;
      default:
        return Icons.signal_cellular_alt;
    }
  }

  String _getQualityDescription(String quality) {
    switch (quality) {
      case 'low':
        return 'Lower quality, reduced bandwidth usage. Best for slow connections.';
      case 'medium':
        return 'Balanced quality and performance. Good for most use cases.';
      case 'high':
        return 'High quality video, requires good internet connection.';
      default:
        return 'Standard streaming quality.';
    }
  }
}

class _SettingRow extends StatelessWidget {
  final String label;
  final Widget child;

  const _SettingRow({
    required this.label,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        child,
      ],
    );
  }
}
