import 'package:flutter/material.dart';

/// Streaming panel for live video streaming controls and statistics
class StreamingPanel extends StatelessWidget {
  final bool isStreaming;
  final Map<String, dynamic> streamingStats;
  final VoidCallback onStartStreaming;
  final VoidCallback onStopStreaming;
  final Function(String) onQualityChanged;
  final VoidCallback onClose;

  const StreamingPanel({
    Key? key,
    required this.isStreaming,
    required this.streamingStats,
    required this.onStartStreaming,
    required this.onStopStreaming,
    required this.onQualityChanged,
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
          color: isStreaming 
              ? Colors.red.withOpacity(0.5)
              : Colors.white.withOpacity(0.2),
          width: 2,
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
          
          // Content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Stream Status
                _buildStreamStatus(),
                
                const SizedBox(height: 16),
                
                // Stream Controls
                _buildStreamControls(),
                
                if (isStreaming) ...[
                  const SizedBox(height: 16),
                  _buildStreamStats(),
                ] else ...[
                  const SizedBox(height: 16),
                  _buildStreamQualitySettings(),
                ],
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
        color: isStreaming 
            ? Colors.red.withOpacity(0.2)
            : Colors.white.withOpacity(0.1),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(16),
          topRight: Radius.circular(16),
        ),
      ),
      child: Row(
        children: [
          Icon(
            isStreaming ? Icons.videocam : Icons.videocam_off,
            color: isStreaming ? Colors.red : Colors.white,
            size: 24,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Live Streaming',
                  style: TextStyle(
                    color: isStreaming ? Colors.red : Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  isStreaming ? 'Broadcasting Live' : 'Ready to Stream',
                  style: TextStyle(
                    color: (isStreaming ? Colors.red : Colors.white).withOpacity(0.8),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          if (isStreaming)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'LIVE',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
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

  Widget _buildStreamStatus() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isStreaming 
            ? Colors.red.withOpacity(0.1)
            : Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isStreaming 
              ? Colors.red.withOpacity(0.3)
              : Colors.white.withOpacity(0.2),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: isStreaming ? Colors.red : Colors.grey,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              isStreaming 
                  ? 'Stream is live and broadcasting'
                  : 'Stream is offline',
              style: TextStyle(
                color: isStreaming ? Colors.red : Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStreamControls() {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton(
            onPressed: isStreaming ? onStopStreaming : onStartStreaming,
            style: ElevatedButton.styleFrom(
              backgroundColor: isStreaming ? Colors.red : Colors.green,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  isStreaming ? Icons.stop : Icons.play_arrow,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  isStreaming ? 'Stop Stream' : 'Start Stream',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStreamStats() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Stream Statistics',
          style: TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              _buildStatRow(
                'Duration',
                _formatDuration(streamingStats['streamDuration'] ?? 0),
              ),
              _buildStatRow(
                'Frames Sent',
                (streamingStats['framesSent'] ?? 0).toString(),
              ),
              _buildStatRow(
                'Data Transferred',
                streamingStats['bytesTransferredMB']?.toString() ?? '0.0' + ' MB',
              ),
              _buildStatRow(
                'Average FPS',
                streamingStats['averageFps']?.toString() ?? '0',
              ),
              _buildStatRow(
                'Bitrate',
                streamingStats['averageBitrate']?.toString() ?? '0 kbps',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStreamQualitySettings() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Stream Quality',
          style: TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Column(
          children: [
            _buildQualityOption('High', '1080p • 30fps', 'high'),
            _buildQualityOption('Medium', '720p • 30fps', 'medium'),
            _buildQualityOption('Low', '480p • 24fps', 'low'),
          ],
        ),
      ],
    );
  }

  Widget _buildQualityOption(String label, String description, String value) {
    return GestureDetector(
      onTap: () => onQualityChanged(value),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: Colors.white.withOpacity(0.2),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.radio_button_unchecked,
              color: Colors.white70,
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
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
          ],
        ),
      ),
    );
  }

  Widget _buildStatRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 12,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(int seconds) {
    final hours = seconds ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    final remainingSeconds = seconds % 60;

    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
    } else {
      return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
    }
  }
}
