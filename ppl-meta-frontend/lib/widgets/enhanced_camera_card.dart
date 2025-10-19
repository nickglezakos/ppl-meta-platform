import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/models/camera.dart';
import '../services/camera_service.dart' hide Camera;
import '../services/recording_session_service.dart';
import '../services/camera_auth_service.dart';
import '../widgets/recording_session_widget.dart';

/// Enhanced CameraCard with Phase 4 Recording Session Integration
/// 
/// Combines existing camera functionality with Phase 4 database persistence
class EnhancedCameraCard extends ConsumerStatefulWidget {
  final Camera camera;
  final bool showRecordingControls;
  final VoidCallback? onTap;

  const EnhancedCameraCard({
    super.key,
    required this.camera,
    this.showRecordingControls = true,
    this.onTap,
  });

  @override
  ConsumerState<EnhancedCameraCard> createState() => _EnhancedCameraCardState();
}

class _EnhancedCameraCardState extends ConsumerState<EnhancedCameraCard> {
  RecordingSessionService? _recordingService;
  bool _isConnected = false;
  bool _isRecording = false;
  bool _isLoading = false;
  RecordingSession? _activeSession;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeServices();
    _checkConnectionStatus();
  }

  void _initializeServices() {
    final authService = CameraAuthService();
    _recordingService = RecordingSessionService(authService);
  }

  Future<void> _checkConnectionStatus() async {
    // Check if camera is connected
    _isConnected = widget.camera.isActive;
    
    // Check if there's an active recording session
    if (_recordingService != null) {
      try {
        final sessions = await _recordingService!.getCameraSessions(widget.camera.deviceId);
        if (sessions != null && sessions.isNotEmpty) {
          _activeSession = sessions.firstWhere(
            (session) => session.isActive,
            orElse: () => sessions.isNotEmpty ? sessions.first : throw StateError('No active session'),
          );
          _isRecording = _activeSession != null;
        }
      } catch (e) {
        debugPrint('Failed to check recording status: $e');
      }
    }
    
    if (mounted) setState(() {});
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    if (_recordingService == null) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Create recording session with Phase 4 database persistence
      final session = await _recordingService!.createRecordingSession(
        cameraDeviceId: widget.camera.deviceId,
        workflowId: 'enhanced-camera-recording',
        metadata: {
          'camera_name': widget.camera.name,
          'camera_brand': widget.camera.manufacturer ?? 'Unknown',
          'camera_model': widget.camera.model ?? 'Unknown',
          'ip_address': widget.camera.metadata?['ip_address'] ?? 'Unknown',
          'recording_type': 'user_initiated',
          'ui_component': 'EnhancedCameraCard',
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (session == null) {
        throw Exception('Failed to create recording session');
      }

      // Update session status to active (simulating camera start)
      await _recordingService!.updateSessionStatus(
        sessionUuid: session.sessionUuid,
        status: SessionStatus.active,
        metadata: {
          'started_at': DateTime.now().toIso8601String(),
          'camera_connected': true,
        },
      );

      setState(() {
        _activeSession = session;
        _isRecording = true;
        _isConnected = true;
      });

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recording started for ${widget.camera.name}'),
            backgroundColor: Colors.green,
            action: SnackBarAction(
              label: 'View Session',
              onPressed: () => _showSessionDetails(),
            ),
          ),
        );
      }

    } catch (e) {
      _errorMessage = 'Failed to start recording: $e';
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage!),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _stopRecording() async {
    if (_recordingService == null || _activeSession == null) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Update session status to completed
      await _recordingService!.updateSessionStatus(
        sessionUuid: _activeSession!.sessionUuid,
        status: SessionStatus.completed,
        metadata: {
          'stopped_at': DateTime.now().toIso8601String(),
          'duration_seconds': _activeSession!.currentDuration ?? 0,
          'recording_quality': 'HD',
          'frames_captured': DateTime.now().difference(_activeSession!.createdAt).inSeconds * 30, // Simulated 30 FPS
        },
      );

      // Auto-trigger face detection for completed session
      await _recordingService!.triggerFaceDetection(
        sessionUuid: _activeSession!.sessionUuid,
        mediaUuid: 'media-${_activeSession!.sessionUuid}',
        options: {
          'method': 'enhanced-v2',
          'auto_trigger': true,
          'source': 'camera_recording',
        },
      );

      setState(() {
        _activeSession = null;
        _isRecording = false;
      });

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recording completed for ${widget.camera.name}'),
            backgroundColor: Colors.blue,
            action: SnackBarAction(
              label: 'View Results',
              onPressed: () => _showSessionHistory(),
            ),
          ),
        );
      }

    } catch (e) {
      _errorMessage = 'Failed to stop recording: $e';
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage!),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _showSessionDetails() {
    if (_activeSession == null) return;
    
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Active Recording Session',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              _buildDetailRow('Session ID', _activeSession!.sessionUuid.substring(0, 8) + '...'),
              _buildDetailRow('Camera', widget.camera.name),
              _buildDetailRow('Status', _activeSession!.statusText),
              _buildDetailRow('Duration', _activeSession!.durationText),
              _buildDetailRow('Workflow', _activeSession!.workflowId),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Close'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      _toggleRecording();
                    },
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                    child: const Text('Stop Recording'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showSessionHistory() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 400,
          height: 500,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Recording History - ${widget.camera.name}',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              Expanded(
                child: FutureBuilder<List<RecordingSession>?>(
                  future: _recordingService?.getCameraSessions(widget.camera.deviceId),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    
                    if (snapshot.hasError) {
                      return Center(
                        child: Text('Error: ${snapshot.error}'),
                      );
                    }
                    
                    final sessions = snapshot.data ?? [];
                    if (sessions.isEmpty) {
                      return const Center(
                        child: Text('No recording sessions found'),
                      );
                    }
                    
                    return ListView.builder(
                      itemCount: sessions.length,
                      itemBuilder: (context, index) {
                        final session = sessions[index];
                        return Card(
                          child: ListTile(
                            leading: Icon(
                              session.isActive ? Icons.fiber_manual_record : Icons.check_circle,
                              color: session.isActive ? Colors.red : Colors.green,
                            ),
                            title: Text('Session ${session.sessionUuid.substring(0, 8)}...'),
                            subtitle: Text(
                              '${session.statusText} • ${session.durationText}',
                            ),
                            trailing: Text(
                              session.createdAt.toString().substring(0, 16),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Close'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: _isRecording ? 8 : 2,
      margin: const EdgeInsets.all(8),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: _isRecording 
                ? Border.all(color: Colors.red, width: 2)
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with camera info and status
              Row(
                children: [
                  Icon(
                    Icons.videocam,
                    color: _isConnected ? Colors.green : Colors.grey,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.camera.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (_isRecording) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'REC',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              
              const SizedBox(height: 8),
              
              // Camera details
              Text(
                '${widget.camera.manufacturer ?? 'Unknown'} ${widget.camera.model ?? ''}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (widget.camera.metadata?['ip_address'] != null)
                Text(
                  widget.camera.metadata!['ip_address'].toString(),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              
              const SizedBox(height: 12),
              
              // Active session info
              if (_activeSession != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.blue.withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Recording Session',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.blue.shade700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Duration: ${_activeSession!.durationText}',
                        style: const TextStyle(fontSize: 11),
                      ),
                      Text(
                        'Status: ${_activeSession!.statusText}',
                        style: const TextStyle(fontSize: 11),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
              ],
              
              // Error message
              if (_errorMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.red.withOpacity(0.3)),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(
                      color: Colors.red,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],
              
              // Recording controls (if enabled)
              if (widget.showRecordingControls) ...[
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _toggleRecording,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Icon(
                                _isRecording ? Icons.stop : Icons.fiber_manual_record,
                                size: 16,
                              ),
                        label: Text(
                          _isRecording ? 'Stop' : 'Record',
                          style: const TextStyle(fontSize: 12),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _isRecording ? Colors.red : Colors.green,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      onPressed: _activeSession != null ? _showSessionDetails : _showSessionHistory,
                      icon: const Icon(Icons.info_outline, size: 18),
                      tooltip: _activeSession != null ? 'Session Details' : 'Recording History',
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}