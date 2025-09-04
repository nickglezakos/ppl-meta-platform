import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../services/mobile_streaming_service.dart';

/// Streaming controls widget for mobile camera streaming
class StreamingControlsWidget extends StatefulWidget {
  final CameraDescription camera;
  final String? rtmpUrl;
  final VoidCallback? onStreamingStarted;
  final VoidCallback? onStreamingStopped;
  
  const StreamingControlsWidget({
    Key? key,
    required this.camera,
    this.rtmpUrl,
    this.onStreamingStarted,
    this.onStreamingStopped,
  }) : super(key: key);
  
  @override
  State<StreamingControlsWidget> createState() => _StreamingControlsWidgetState();
}

class _StreamingControlsWidgetState extends State<StreamingControlsWidget> {
  final MobileStreamingService _streamingService = MobileStreamingService();
  StreamQuality _selectedQuality = StreamQuality.medium;
  bool _isLoading = false;
  
  @override
  void initState() {
    super.initState();
    _initializeService();
  }
  
  Future<void> _initializeService() async {
    await _streamingService.initialize();
    if (mounted) {
      setState(() {});
    }
  }
  
  @override
  void dispose() {
    _streamingService.dispose();
    super.dispose();
  }
  
  Future<void> _startStreaming() async {
    if (widget.rtmpUrl == null) {
      _showError('No RTMP URL provided');
      return;
    }
    
    setState(() {
      _isLoading = true;
    });
    
    try {
      final config = StreamConfig.fromQuality(_selectedQuality);
      final success = await _streamingService.startStreaming(
        rtmpUrl: widget.rtmpUrl!,
        config: config,
        camera: widget.camera,
      );
      
      if (success) {
        widget.onStreamingStarted?.call();
        _showSuccess('Streaming started successfully');
      } else {
        _showError('Failed to start streaming');
      }
    } catch (e) {
      _showError('Error starting stream: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
  
  Future<void> _stopStreaming() async {
    setState(() {
      _isLoading = true;
    });
    
    try {
      await _streamingService.stopStreaming();
      widget.onStreamingStopped?.call();
      _showSuccess('Streaming stopped');
    } catch (e) {
      _showError('Error stopping stream: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
  
  Future<void> _updateQuality(StreamQuality? quality) async {
    if (quality == null) return;
    
    setState(() {
      _selectedQuality = quality;
    });
    
    if (_streamingService.isStreaming) {
      final success = await _streamingService.updateStreamQuality(quality);
      if (success) {
        _showSuccess('Quality updated to ${quality.displayName}');
      } else {
        _showError('Failed to update quality');
      }
    }
  }
  
  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  void _showSuccess(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.videocam, color: Colors.blue),
                const SizedBox(width: 8),
                const Text(
                  'Live Streaming',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                _buildStreamingStatusIndicator(),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Quality Selection
            Row(
              children: [
                const Icon(Icons.settings, size: 20),
                const SizedBox(width: 8),
                const Text('Quality:'),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButton<StreamQuality>(
                    value: _selectedQuality,
                    isExpanded: true,
                    items: StreamQuality.values.map((quality) {
                      return DropdownMenuItem(
                        value: quality,
                        child: Text(quality.displayName),
                      );
                    }).toList(),
                    onChanged: _updateQuality,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Control Buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : (
                      _streamingService.isStreaming ? _stopStreaming : _startStreaming
                    ),
                    icon: _isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(_streamingService.isStreaming ? Icons.stop : Icons.play_arrow),
                    label: Text(
                      _isLoading
                          ? 'Loading...'
                          : (_streamingService.isStreaming ? 'Stop Streaming' : 'Start Streaming'),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _streamingService.isStreaming ? Colors.red : Colors.green,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Streaming Information
            if (_streamingService.isStreaming) ...[
              const Divider(),
              _buildStreamingInfo(),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildStreamingStatusIndicator() {
    if (!_streamingService.isInitialized) {
      return const SizedBox.shrink();
    }
    
    return StreamBuilder<StreamingStatus>(
      stream: _streamingService.statusStream,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const SizedBox.shrink();
        }
        
        final status = snapshot.data!;
        Color color;
        IconData icon;
        
        switch (status.state) {
          case StreamingState.streaming:
            color = Colors.green;
            icon = Icons.radio_button_checked;
            break;
          case StreamingState.initializing:
          case StreamingState.stopping:
            color = Colors.orange;
            icon = Icons.hourglass_empty;
            break;
          case StreamingState.error:
            color = Colors.red;
            icon = Icons.error;
            break;
          case StreamingState.stopped:
            color = Colors.grey;
            icon = Icons.radio_button_unchecked;
            break;
        }
        
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 16),
            const SizedBox(width: 4),
            Text(
              status.state.name.toUpperCase(),
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ],
        );
      },
    );
  }
  
  Widget _buildStreamingInfo() {
    final session = _streamingService.currentSession;
    if (session == null) return const SizedBox.shrink();
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Streaming Information',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        
        Row(
          children: [
            const Icon(Icons.schedule, size: 16),
            const SizedBox(width: 4),
            Text('Duration: ${_formatDuration(session.duration)}'),
          ],
        ),
        
        const SizedBox(height: 4),
        
        Row(
          children: [
            const Icon(Icons.aspect_ratio, size: 16),
            const SizedBox(width: 4),
            Text('Resolution: ${session.config.resolution}'),
          ],
        ),
        
        const SizedBox(height: 4),
        
        Row(
          children: [
            const Icon(Icons.speed, size: 16),
            const SizedBox(width: 4),
            Text('FPS: ${session.config.fps}'),
          ],
        ),
        
        const SizedBox(height: 8),
        
        // Real-time statistics
        StreamBuilder<StreamingStats>(
          stream: _streamingService.statsStream,
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return const Text('Loading statistics...');
            }
            
            final stats = snapshot.data!;
            return Column(
              children: [
                Row(
                  children: [
                    const Icon(Icons.signal_cellular_alt, size: 16),
                    const SizedBox(width: 4),
                    Text('Bitrate: ${(stats.bitrate / 1000).toStringAsFixed(0)} kbps'),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.access_time, size: 16),
                    const SizedBox(width: 4),
                    Text('Latency: ${stats.latency.inMilliseconds}ms'),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }
  
  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);
    
    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    } else {
      return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
  }
}
