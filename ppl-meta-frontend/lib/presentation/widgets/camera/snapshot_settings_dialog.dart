import 'package:flutter/material.dart';
import '../../../core/models/snapshot_settings.dart';

/// Dialog for configuring enhanced snapshot settings
class SnapshotSettingsDialog extends StatefulWidget {
  final CameraCapabilities capabilities;
  final SnapshotSettings initialSettings;
  final VoidCallback? onCapture;

  const SnapshotSettingsDialog({
    super.key,
    required this.capabilities,
    required this.initialSettings,
    this.onCapture,
  });

  @override
  State<SnapshotSettingsDialog> createState() => _SnapshotSettingsDialogState();
}

class _SnapshotSettingsDialogState extends State<SnapshotSettingsDialog> {
  late SnapshotSettings _settings;
  bool _isCapturing = false;

  @override
  void initState() {
    super.initState();
    _settings = widget.initialSettings;
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 500,
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.camera_alt, size: 24),
                const SizedBox(width: 12),
                const Text(
                  'Enhanced Snapshot Settings',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Resolution Selection
            _buildResolutionSection(),
            const SizedBox(height: 24),

            // Quality Settings
            _buildQualitySection(),
            const SizedBox(height: 24),

            // Format Selection
            _buildFormatSection(),
            const SizedBox(height: 24),

            // Preview Information
            _buildPreviewSection(),
            const SizedBox(height: 32),

            // Action Buttons
            _buildActionButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildResolutionSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Snapshot Resolution',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Choose snapshot resolution independent of streaming quality',
          style: TextStyle(color: Colors.grey),
        ),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(8),
          ),
          child: DropdownButtonFormField<String>(
            value: _settings.resolution,
            decoration: const InputDecoration(
              border: InputBorder.none,
              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
            items: widget.capabilities.availableResolutions.map((resolution) {
              return DropdownMenuItem(
                value: resolution,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.capabilities.getResolutionDisplayName(resolution)),
                    if (resolution == 'max') ...[
                      Text(
                        '📸 Best quality for archival',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.green.shade600,
                        ),
                      ),
                    ] else if (resolution == 'stream') ...[
                      Text(
                        '⚡ Same as streaming quality',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.blue.shade600,
                        ),
                      ),
                    ],
                  ],
                ),
              );
            }).toList(),
            onChanged: (value) {
              if (value != null) {
                setState(() {
                  _settings = _settings.copyWith(resolution: value);
                });
              }
            },
          ),
        ),
      ],
    );
  }

  Widget _buildQualitySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Image Quality',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const Spacer(),
            Text(
              '${_settings.quality}%',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.blue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          '${_settings.qualityDescription} • ${_settings.fileSizeImpact}',
          style: const TextStyle(color: Colors.grey),
        ),
        const SizedBox(height: 12),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
            overlayShape: const RoundSliderOverlayShape(overlayRadius: 16),
          ),
          child: Slider(
            value: _settings.quality.toDouble(),
            min: 70,
            max: 100,
            divisions: 6,
            label: '${_settings.quality}%',
            onChanged: (value) {
              setState(() {
                _settings = _settings.copyWith(quality: value.round());
              });
            },
          ),
        ),
        // Quality indicators
        Row(
          children: [
            _buildQualityIndicator('Standard\n70%', _settings.quality >= 70),
            const Spacer(),
            _buildQualityIndicator('Good\n80%', _settings.quality >= 80),
            const Spacer(),
            _buildQualityIndicator('High\n90%', _settings.quality >= 90),
            const Spacer(),
            _buildQualityIndicator('Maximum\n100%', _settings.quality >= 100),
          ],
        ),
      ],
    );
  }

  Widget _buildQualityIndicator(String label, bool isActive) {
    return Column(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: isActive ? Colors.blue : Colors.grey.shade300,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: isActive ? Colors.blue : Colors.grey,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildFormatSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Image Format',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildFormatOption('JPEG', 'Recommended'),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildFormatOption('PNG', 'Lossless'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFormatOption(String format, String description) {
    final isSelected = _settings.format == format;
    return GestureDetector(
      onTap: () {
        setState(() {
          _settings = _settings.copyWith(format: format);
        });
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(
            color: isSelected ? Colors.blue : Colors.grey.shade300,
            width: isSelected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(8),
          color: isSelected ? Colors.blue.shade50 : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  format,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: isSelected ? Colors.blue.shade700 : null,
                  ),
                ),
                const Spacer(),
                if (isSelected)
                  Icon(
                    Icons.check_circle,
                    color: Colors.blue.shade700,
                    size: 20,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              description,
              style: TextStyle(
                fontSize: 12,
                color: isSelected ? Colors.blue.shade600 : Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _settings.formatDescription,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreviewSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.info_outline, size: 20, color: Colors.blue),
              SizedBox(width: 8),
              Text(
                'Snapshot Preview',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Colors.blue,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildPreviewRow('Resolution:', _getResolutionPreview()),
          _buildPreviewRow('Quality:', '${_settings.quality}% (${_settings.qualityDescription})'),
          _buildPreviewRow('Format:', '${_settings.format} (${_settings.formatDescription})'),
          _buildPreviewRow('Estimated Size:', _getEstimatedSize()),
        ],
      ),
    );
  }

  Widget _buildPreviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 13,
                color: Colors.grey,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getResolutionPreview() {
    if (_settings.resolution == 'max') {
      final res = widget.capabilities.maxResolution;
      final mp = res.megapixels;
      return '${res.width}x${res.height} (${mp.toStringAsFixed(1)}MP)';
    } else if (_settings.resolution == 'stream') {
      final res = widget.capabilities.currentStreamResolution;
      if (res != null) {
        final mp = res.megapixels;
        return '${res.width}x${res.height} (${mp.toStringAsFixed(1)}MP)';
      }
      return 'Stream quality';
    } else {
      return _settings.resolution;
    }
  }

  String _getEstimatedSize() {
    // Rough estimation based on resolution and quality
    double baseSize = 0.5; // MB for basic resolution
    
    if (_settings.resolution == 'max') {
      final res = widget.capabilities.maxResolution;
      baseSize = (res.width * res.height) / 1000000 * 0.3; // ~0.3MB per MP
    }
    
    // Adjust for quality
    final qualityFactor = _settings.quality / 100.0;
    final finalSize = baseSize * qualityFactor;
    
    if (_settings.format == 'PNG') {
      return '${(finalSize * 2).toStringAsFixed(1)} MB (lossless)';
    } else {
      return '${finalSize.toStringAsFixed(1)} MB';
    }
  }

  Widget _buildActionButtons() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: _isCapturing ? null : () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: ElevatedButton(
            onPressed: _isCapturing ? null : _captureSnapshot,
            child: _isCapturing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Capture Snapshot'),
          ),
        ),
      ],
    );
  }

  void _captureSnapshot() {
    setState(() {
      _isCapturing = true;
    });

    // Return the settings and trigger capture
    Navigator.of(context).pop(_settings);
    widget.onCapture?.call();
  }
}

/// Static method to show the snapshot settings dialog
Future<SnapshotSettings?> showSnapshotSettingsDialog(
  BuildContext context, {
  required CameraCapabilities capabilities,
  SnapshotSettings? initialSettings,
  VoidCallback? onCapture,
}) {
  return showDialog<SnapshotSettings>(
    context: context,
    builder: (context) => SnapshotSettingsDialog(
      capabilities: capabilities,
      initialSettings: initialSettings ?? const SnapshotSettings(),
      onCapture: onCapture,
    ),
  );
}
