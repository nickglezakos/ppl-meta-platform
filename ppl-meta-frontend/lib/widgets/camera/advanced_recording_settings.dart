import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/camera_providers.dart';

/// Advanced recording settings widget with comprehensive configuration options
/// Provides UI for resolution, frame rate, quality, format, and storage settings
class AdvancedRecordingSettings extends ConsumerStatefulWidget {
  final String? deviceId;
  final Function(RecordingConfiguration)? onConfigurationChanged;

  const AdvancedRecordingSettings({
    Key? key,
    this.deviceId,
    this.onConfigurationChanged,
  }) : super(key: key);

  @override
  ConsumerState<AdvancedRecordingSettings> createState() => _AdvancedRecordingSettingsState();
}

class _AdvancedRecordingSettingsState extends ConsumerState<AdvancedRecordingSettings> {
  @override
  Widget build(BuildContext context) {
    final recordingConfig = ref.watch(recordingConfigurationProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Recording Settings',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              IconButton(
                onPressed: () => _resetToDefaults(),
                icon: const Icon(Icons.restore),
                tooltip: 'Reset to defaults',
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Video Quality Section
          _buildSection(
            title: 'Video Quality',
            icon: Icons.high_quality,
            children: [
              _buildResolutionSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildFrameRateSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildQualityPresetSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildBitrateSlider(recordingConfig),
            ],
          ),

          const SizedBox(height: 24),

          // Format & Encoding Section
          _buildSection(
            title: 'Format & Encoding',
            icon: Icons.video_settings,
            children: [
              _buildFormatSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildCodecSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildCompressionSettings(recordingConfig),
            ],
          ),

          const SizedBox(height: 24),

          // Storage & Organization Section
          _buildSection(
            title: 'Storage & Organization',
            icon: Icons.storage,
            children: [
              _buildStorageLocationSelector(recordingConfig),
              const SizedBox(height: 16),
              _buildFileNamingSettings(recordingConfig),
              const SizedBox(height: 16),
              _buildAutoDeleteSettings(recordingConfig),
            ],
          ),

          const SizedBox(height: 24),

          // Recording Behavior Section
          _buildSection(
            title: 'Recording Behavior',
            icon: Icons.play_circle,
            children: [
              _buildMaxDurationSetting(recordingConfig),
              const SizedBox(height: 16),
              _buildSplitSettings(recordingConfig),
              const SizedBox(height: 16),
              _buildBufferSettings(recordingConfig),
            ],
          ),

          const SizedBox(height: 24),

          // Advanced Options Section
          _buildSection(
            title: 'Advanced Options',
            icon: Icons.tune,
            children: [
              _buildWatermarkSettings(recordingConfig),
              const SizedBox(height: 16),
              _buildTimestampSettings(recordingConfig),
              const SizedBox(height: 16),
              _buildMetadataSettings(recordingConfig),
            ],
          ),

          const SizedBox(height: 32),

          // Action Buttons
          _buildActionButtons(recordingConfig),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildResolutionSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Resolution',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: VideoResolution.values.map((resolution) {
            final isSelected = config.resolution == resolution;
            return FilterChip(
              label: Text(resolution.displayName),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) {
                  _updateConfiguration(config.copyWith(resolution: resolution));
                }
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildFrameRateSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Frame Rate',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [15, 24, 30, 60].map((fps) {
            final isSelected = config.frameRate == fps;
            return FilterChip(
              label: Text('${fps} FPS'),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) {
                  _updateConfiguration(config.copyWith(frameRate: fps));
                }
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildQualityPresetSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quality Preset',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<QualityPreset>(
          value: config.qualityPreset,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          items: QualityPreset.values.map((preset) {
            return DropdownMenuItem(
              value: preset,
              child: Text(preset.displayName),
            );
          }).toList(),
          onChanged: (preset) {
            if (preset != null) {
              _updateConfiguration(config.copyWith(qualityPreset: preset));
            }
          },
        ),
      ],
    );
  }

  Widget _buildBitrateSlider(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Bitrate',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Text(
              '${config.bitrate} kbps',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Slider(
          value: config.bitrate.toDouble(),
          min: 500,
          max: 10000,
          divisions: 19,
          label: '${config.bitrate} kbps',
          onChanged: (value) {
            _updateConfiguration(config.copyWith(bitrate: value.round()));
          },
        ),
      ],
    );
  }

  Widget _buildFormatSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Video Format',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<VideoFormat>(
          value: config.format,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          items: VideoFormat.values.map((format) {
            return DropdownMenuItem(
              value: format,
              child: Row(
                children: [
                  Text(format.extension.toUpperCase()),
                  const SizedBox(width: 8),
                  Text(
                    '(${format.description})',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            );
          }).toList(),
          onChanged: (format) {
            if (format != null) {
              _updateConfiguration(config.copyWith(format: format));
            }
          },
        ),
      ],
    );
  }

  Widget _buildCodecSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Video Codec',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<VideoCodec>(
          value: config.codec,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          items: VideoCodec.values.map((codec) {
            return DropdownMenuItem(
              value: codec,
              child: Row(
                children: [
                  Text(codec.name.toUpperCase()),
                  const SizedBox(width: 8),
                  Text(
                    codec.description,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            );
          }).toList(),
          onChanged: (codec) {
            if (codec != null) {
              _updateConfiguration(config.copyWith(codec: codec));
            }
          },
        ),
      ],
    );
  }

  Widget _buildCompressionSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Compression Level',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Text(
              '${config.compressionLevel}%',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 8),
        Slider(
          value: config.compressionLevel.toDouble(),
          min: 0,
          max: 100,
          divisions: 20,
          label: '${config.compressionLevel}%',
          onChanged: (value) {
            _updateConfiguration(config.copyWith(compressionLevel: value.round()));
          },
        ),
        Text(
          'Higher compression = smaller file size, lower quality',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.outline,
          ),
        ),
      ],
    );
  }

  Widget _buildStorageLocationSelector(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Storage Location',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        InkWell(
          onTap: () => _selectStorageLocation(),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: Theme.of(context).colorScheme.outline),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              children: [
                const Icon(Icons.folder),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    config.storageLocation ?? 'Select folder...',
                    style: TextStyle(
                      color: config.storageLocation != null 
                          ? null 
                          : Theme.of(context).colorScheme.outline,
                    ),
                  ),
                ),
                const Icon(Icons.chevron_right),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFileNamingSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'File Naming',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        TextFormField(
          initialValue: config.fileNamePattern,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'e.g., camera_{device}_{timestamp}',
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          onChanged: (value) {
            _updateConfiguration(config.copyWith(fileNamePattern: value));
          },
        ),
        const SizedBox(height: 4),
        Text(
          'Available variables: {device}, {timestamp}, {date}, {time}',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.outline,
          ),
        ),
      ],
    );
  }

  Widget _buildAutoDeleteSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Auto-delete old recordings',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Switch(
              value: config.autoDeleteEnabled,
              onChanged: (value) {
                _updateConfiguration(config.copyWith(autoDeleteEnabled: value));
              },
            ),
          ],
        ),
        if (config.autoDeleteEnabled) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Delete after'),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: config.autoDeleteDays,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: [7, 14, 30, 60, 90].map((days) {
                    return DropdownMenuItem(
                      value: days,
                      child: Text('$days days'),
                    );
                  }).toList(),
                  onChanged: (days) {
                    if (days != null) {
                      _updateConfiguration(config.copyWith(autoDeleteDays: days));
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildMaxDurationSetting(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Limit recording duration',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Switch(
              value: config.maxDurationEnabled,
              onChanged: (value) {
                _updateConfiguration(config.copyWith(maxDurationEnabled: value));
              },
            ),
          ],
        ),
        if (config.maxDurationEnabled) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Maximum'),
              const SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  initialValue: config.maxDurationMinutes.toString(),
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    suffix: Text('minutes'),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  onChanged: (value) {
                    final minutes = int.tryParse(value) ?? config.maxDurationMinutes;
                    _updateConfiguration(config.copyWith(maxDurationMinutes: minutes));
                  },
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildSplitSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Split large recordings',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Switch(
              value: config.splitLargeFiles,
              onChanged: (value) {
                _updateConfiguration(config.copyWith(splitLargeFiles: value));
              },
            ),
          ],
        ),
        if (config.splitLargeFiles) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Split every'),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: config.splitSizeMB,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: [100, 250, 500, 1000, 2000].map((mb) {
                    return DropdownMenuItem(
                      value: mb,
                      child: Text('${mb} MB'),
                    );
                  }).toList(),
                  onChanged: (mb) {
                    if (mb != null) {
                      _updateConfiguration(config.copyWith(splitSizeMB: mb));
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildBufferSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Pre-recording buffer',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Switch(
              value: config.preRecordingBuffer,
              onChanged: (value) {
                _updateConfiguration(config.copyWith(preRecordingBuffer: value));
              },
            ),
          ],
        ),
        if (config.preRecordingBuffer) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Buffer'),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: config.bufferSeconds,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: [5, 10, 15, 30, 60].map((seconds) {
                    return DropdownMenuItem(
                      value: seconds,
                      child: Text('$seconds seconds'),
                    );
                  }).toList(),
                  onChanged: (seconds) {
                    if (seconds != null) {
                      _updateConfiguration(config.copyWith(bufferSeconds: seconds));
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildWatermarkSettings(RecordingConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Add watermark',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            Switch(
              value: config.watermarkEnabled,
              onChanged: (value) {
                _updateConfiguration(config.copyWith(watermarkEnabled: value));
              },
            ),
          ],
        ),
        if (config.watermarkEnabled) ...[
          const SizedBox(height: 8),
          TextFormField(
            initialValue: config.watermarkText,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'Watermark text',
              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            onChanged: (value) {
              _updateConfiguration(config.copyWith(watermarkText: value));
            },
          ),
        ],
      ],
    );
  }

  Widget _buildTimestampSettings(RecordingConfiguration config) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          'Include timestamp overlay',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        Switch(
          value: config.timestampOverlay,
          onChanged: (value) {
            _updateConfiguration(config.copyWith(timestampOverlay: value));
          },
        ),
      ],
    );
  }

  Widget _buildMetadataSettings(RecordingConfiguration config) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          'Save recording metadata',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        Switch(
          value: config.saveMetadata,
          onChanged: (value) {
            _updateConfiguration(config.copyWith(saveMetadata: value));
          },
        ),
      ],
    );
  }

  Widget _buildActionButtons(RecordingConfiguration config) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: () => _resetToDefaults(),
            child: const Text('Reset to Defaults'),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: ElevatedButton(
            onPressed: () => _saveConfiguration(config),
            child: const Text('Save Settings'),
          ),
        ),
      ],
    );
  }

  void _updateConfiguration(RecordingConfiguration config) {
    ref.read(recordingConfigurationProvider.notifier).updateConfiguration(config);
    widget.onConfigurationChanged?.call(config);
  }

  void _resetToDefaults() {
    final defaultConfig = RecordingConfiguration.defaultConfiguration();
    _updateConfiguration(defaultConfig);
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Settings reset to defaults'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _saveConfiguration(RecordingConfiguration config) {
    ref.read(recordingConfigurationProvider.notifier).saveConfiguration();
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Settings saved successfully'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _selectStorageLocation() {
    // In a real implementation, this would open a folder picker
    // For now, we'll show a placeholder dialog
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Storage Location'),
        content: const Text('Folder picker would open here'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              final config = ref.read(recordingConfigurationProvider);
              _updateConfiguration(config.copyWith(
                storageLocation: '/Users/recordings',
              ));
            },
            child: const Text('Select'),
          ),
        ],
      ),
    );
  }
}

/// Recording configuration data class
class RecordingConfiguration {
  final VideoResolution resolution;
  final int frameRate;
  final QualityPreset qualityPreset;
  final int bitrate;
  final VideoFormat format;
  final VideoCodec codec;
  final int compressionLevel;
  final String? storageLocation;
  final String fileNamePattern;
  final bool autoDeleteEnabled;
  final int autoDeleteDays;
  final bool maxDurationEnabled;
  final int maxDurationMinutes;
  final bool splitLargeFiles;
  final int splitSizeMB;
  final bool preRecordingBuffer;
  final int bufferSeconds;
  final bool watermarkEnabled;
  final String watermarkText;
  final bool timestampOverlay;
  final bool saveMetadata;

  const RecordingConfiguration({
    required this.resolution,
    required this.frameRate,
    required this.qualityPreset,
    required this.bitrate,
    required this.format,
    required this.codec,
    required this.compressionLevel,
    this.storageLocation,
    required this.fileNamePattern,
    required this.autoDeleteEnabled,
    required this.autoDeleteDays,
    required this.maxDurationEnabled,
    required this.maxDurationMinutes,
    required this.splitLargeFiles,
    required this.splitSizeMB,
    required this.preRecordingBuffer,
    required this.bufferSeconds,
    required this.watermarkEnabled,
    required this.watermarkText,
    required this.timestampOverlay,
    required this.saveMetadata,
  });

  factory RecordingConfiguration.defaultConfiguration() {
    return const RecordingConfiguration(
      resolution: VideoResolution.hd720,
      frameRate: 30,
      qualityPreset: QualityPreset.balanced,
      bitrate: 2000,
      format: VideoFormat.mp4,
      codec: VideoCodec.h264,
      compressionLevel: 50,
      fileNamePattern: 'camera_{device}_{timestamp}',
      autoDeleteEnabled: false,
      autoDeleteDays: 30,
      maxDurationEnabled: false,
      maxDurationMinutes: 60,
      splitLargeFiles: false,
      splitSizeMB: 1000,
      preRecordingBuffer: false,
      bufferSeconds: 10,
      watermarkEnabled: false,
      watermarkText: '',
      timestampOverlay: true,
      saveMetadata: true,
    );
  }

  RecordingConfiguration copyWith({
    VideoResolution? resolution,
    int? frameRate,
    QualityPreset? qualityPreset,
    int? bitrate,
    VideoFormat? format,
    VideoCodec? codec,
    int? compressionLevel,
    String? storageLocation,
    String? fileNamePattern,
    bool? autoDeleteEnabled,
    int? autoDeleteDays,
    bool? maxDurationEnabled,
    int? maxDurationMinutes,
    bool? splitLargeFiles,
    int? splitSizeMB,
    bool? preRecordingBuffer,
    int? bufferSeconds,
    bool? watermarkEnabled,
    String? watermarkText,
    bool? timestampOverlay,
    bool? saveMetadata,
  }) {
    return RecordingConfiguration(
      resolution: resolution ?? this.resolution,
      frameRate: frameRate ?? this.frameRate,
      qualityPreset: qualityPreset ?? this.qualityPreset,
      bitrate: bitrate ?? this.bitrate,
      format: format ?? this.format,
      codec: codec ?? this.codec,
      compressionLevel: compressionLevel ?? this.compressionLevel,
      storageLocation: storageLocation ?? this.storageLocation,
      fileNamePattern: fileNamePattern ?? this.fileNamePattern,
      autoDeleteEnabled: autoDeleteEnabled ?? this.autoDeleteEnabled,
      autoDeleteDays: autoDeleteDays ?? this.autoDeleteDays,
      maxDurationEnabled: maxDurationEnabled ?? this.maxDurationEnabled,
      maxDurationMinutes: maxDurationMinutes ?? this.maxDurationMinutes,
      splitLargeFiles: splitLargeFiles ?? this.splitLargeFiles,
      splitSizeMB: splitSizeMB ?? this.splitSizeMB,
      preRecordingBuffer: preRecordingBuffer ?? this.preRecordingBuffer,
      bufferSeconds: bufferSeconds ?? this.bufferSeconds,
      watermarkEnabled: watermarkEnabled ?? this.watermarkEnabled,
      watermarkText: watermarkText ?? this.watermarkText,
      timestampOverlay: timestampOverlay ?? this.timestampOverlay,
      saveMetadata: saveMetadata ?? this.saveMetadata,
    );
  }
}

/// Video resolution enumeration
enum VideoResolution {
  qvga(320, 240, 'QVGA (320x240)'),
  vga(640, 480, 'VGA (640x480)'),
  hd720(1280, 720, 'HD 720p'),
  hd1080(1920, 1080, 'Full HD 1080p'),
  uhd4k(3840, 2160, '4K UHD');

  const VideoResolution(this.width, this.height, this.displayName);
  
  final int width;
  final int height;
  final String displayName;
}

/// Quality preset enumeration
enum QualityPreset {
  economy('Economy', 'Smaller file size, lower quality'),
  balanced('Balanced', 'Good balance of quality and file size'),
  quality('High Quality', 'Better quality, larger file size'),
  maximum('Maximum', 'Best quality, largest file size');

  const QualityPreset(this.displayName, this.description);
  
  final String displayName;
  final String description;
}

/// Video format enumeration
enum VideoFormat {
  mp4('mp4', 'MP4 - Most compatible'),
  avi('avi', 'AVI - Uncompressed'),
  mov('mov', 'MOV - Apple QuickTime'),
  mkv('mkv', 'MKV - Matroska');

  const VideoFormat(this.extension, this.description);
  
  final String extension;
  final String description;
}

/// Video codec enumeration
enum VideoCodec {
  h264('H.264 - Most compatible'),
  h265('H.265 - Better compression'),
  vp9('VP9 - Open source'),
  av1('AV1 - Next generation');

  const VideoCodec(this.description);
  
  final String description;
}