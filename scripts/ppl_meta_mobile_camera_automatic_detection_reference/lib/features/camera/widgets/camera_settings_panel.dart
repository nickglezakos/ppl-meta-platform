import 'package:flutter/material.dart';

/// Camera settings panel for quality and configuration options
class CameraSettingsPanel extends StatelessWidget {
  final Function(String) onQualityChanged;
  final String currentQuality;
  final VoidCallback onClose;

  const CameraSettingsPanel({
    Key? key,
    required this.onQualityChanged,
    required this.currentQuality,
    required this.onClose,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 300,
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.2),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.5),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          _buildHeader(),
          
          // Settings Content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Photo Quality Section
                _buildPhotoQualitySection(),
                
                const SizedBox(height: 24),
                
                // Resolution Section
                _buildResolutionSection(),
                
                const SizedBox(height: 24),
                
                // Advanced Settings
                _buildAdvancedSettings(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(16),
          topRight: Radius.circular(16),
        ),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.settings,
            color: Colors.white,
            size: 24,
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Camera Settings',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          IconButton(
            onPressed: onClose,
            icon: const Icon(
              Icons.close,
              color: Colors.white,
              size: 20,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPhotoQualitySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Photo Quality',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        _buildQualityOptions(),
      ],
    );
  }

  Widget _buildQualityOptions() {
    final qualities = [
      {'label': 'High', 'value': 'high', 'desc': '4K resolution, best quality'},
      {'label': 'Medium', 'value': 'medium', 'desc': '1080p resolution, balanced'},
      {'label': 'Low', 'value': 'low', 'desc': '720p resolution, smaller files'},
    ];

    return Column(
      children: qualities.map((quality) {
        final isSelected = currentQuality.toLowerCase() == quality['value'];
        
        return GestureDetector(
          onTap: () => onQualityChanged(quality['value']!),
          child: Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isSelected 
                  ? Colors.blue.withOpacity(0.3)
                  : Colors.white.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isSelected 
                    ? Colors.blue
                    : Colors.white.withOpacity(0.2),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  isSelected 
                      ? Icons.radio_button_checked 
                      : Icons.radio_button_unchecked,
                  color: isSelected ? Colors.blue : Colors.white70,
                  size: 20,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        quality['label']!,
                        style: TextStyle(
                          color: isSelected ? Colors.blue : Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      Text(
                        quality['desc']!,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildResolutionSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Resolution',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              _buildResolutionInfo('High Quality', '3840 x 2160 (4K)'),
              const Divider(color: Colors.white24, height: 16),
              _buildResolutionInfo('Medium Quality', '1920 x 1080 (1080p)'),
              const Divider(color: Colors.white24, height: 16),
              _buildResolutionInfo('Low Quality', '1280 x 720 (720p)'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildResolutionInfo(String quality, String resolution) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          quality,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
          ),
        ),
        Text(
          resolution,
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 12,
          ),
        ),
      ],
    );
  }

  Widget _buildAdvancedSettings() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Advanced',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Column(
          children: [
            _buildAdvancedOption(
              'Grid Lines',
              'Show rule of thirds grid',
              true,
              (value) {
                // Future: Grid lines toggle
              },
            ),
            _buildAdvancedOption(
              'Auto Focus',
              'Automatic focus adjustment',
              true,
              (value) {
                // Future: Auto focus toggle
              },
            ),
            _buildAdvancedOption(
              'Image Stabilization',
              'Reduce camera shake',
              false,
              (value) {
                // Future: Stabilization toggle
              },
            ),
            _buildAdvancedOption(
              'Geo-tagging',
              'Save location in photos',
              false,
              (value) {
                // Future: Geo-tagging toggle
              },
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildAdvancedOption(
    String title,
    String description,
    bool value,
    Function(bool) onChanged,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: Colors.blue,
            inactiveThumbColor: Colors.white.withOpacity(0.7),
            inactiveTrackColor: Colors.white.withOpacity(0.3),
          ),
        ],
      ),
    );
  }
}
