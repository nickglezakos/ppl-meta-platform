import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/recording_session_service.dart';
import '../services/camera_service.dart';
import '../services/camera_auth_service.dart';

/// Phase 4 Recording Session Management Widget
/// 
/// Provides comprehensive camera recording with database session persistence
class RecordingSessionWidget extends ConsumerStatefulWidget {
  final String cameraDeviceId;
  final String? cameraName;

  const RecordingSessionWidget({
    super.key,
    required this.cameraDeviceId,
    this.cameraName,
  });

  @override
  ConsumerState<RecordingSessionWidget> createState() => _RecordingSessionWidgetState();
}

class _RecordingSessionWidgetState extends ConsumerState<RecordingSessionWidget> {
  RecordingSessionService? _recordingService;
  CameraService? _cameraService;
  RecordingSession? _activeSession;
  bool _isRecording = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  void _initializeServices() {
    final authService = CameraAuthService(); // You might need to get this from provider
    _recordingService = RecordingSessionService(authService);
    _cameraService = CameraService(authService);
    
    // Load active sessions for this camera
    _loadActiveSessions();
  }

  Future<void> _loadActiveSessions() async {
    if (_recordingService == null) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final sessions = await _recordingService!.getCameraSessions(widget.cameraDeviceId);
      if (sessions != null && sessions.isNotEmpty) {
        // Find active session
        try {
          _activeSession = sessions.firstWhere(
            (session) => session.isActive,
          );
        } catch (e) {
          _activeSession = null; // No active session found
        }
        
        _isRecording = _activeSession != null;
      }
    } catch (e) {
      _errorMessage = 'Failed to load sessions: $e';
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _startRecording() async {
    if (_recordingService == null || _cameraService == null) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Step 1: Connect to camera
      final connected = await _cameraService!.connectCamera(widget.cameraDeviceId);
      if (!connected) {
        throw Exception('Failed to connect to camera');
      }

      // Step 2: Create recording session
      final session = await _recordingService!.createRecordingSession(
        cameraDeviceId: widget.cameraDeviceId,
        workflowId: 'camera-recording-workflow',
        metadata: {
          'camera_name': widget.cameraName ?? 'Unknown Camera',
          'recording_type': 'manual',
          'initiated_by': 'user',
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      if (session == null) {
        throw Exception('Failed to create recording session');
      }

      // Step 3: Start camera recording
      final recordingResult = await _cameraService!.startRecording(widget.cameraDeviceId);
      if (recordingResult == null) {
        // If camera recording fails, clean up the session
        await _recordingService!.deleteRecordingSession(session.sessionUuid);
        throw Exception('Failed to start camera recording');
      }

      // Step 4: Update session status to active
      await _recordingService!.updateSessionStatus(
        sessionUuid: session.sessionUuid,
        status: SessionStatus.active,
        metadata: {
          'recording_id': recordingResult.recordingId,
          'started_at': DateTime.now().toIso8601String(),
        },
      );

      setState(() {
        _activeSession = session;
        _isRecording = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Recording started for ${widget.cameraName ?? widget.cameraDeviceId}'),
          backgroundColor: Colors.green,
        ),
      );

    } catch (e) {
      _errorMessage = 'Failed to start recording: $e';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_errorMessage!),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _stopRecording() async {
    if (_recordingService == null || _cameraService == null || _activeSession == null) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Step 1: Stop camera recording
      final recordingResult = await _cameraService!.stopRecording(widget.cameraDeviceId);
      
      // Step 2: Update session status to completed
      await _recordingService!.updateSessionStatus(
        sessionUuid: _activeSession!.sessionUuid,
        status: SessionStatus.completed,
        metadata: {
          'stopped_at': DateTime.now().toIso8601String(),
          'final_file_path': recordingResult?.filePath,
          'duration_seconds': recordingResult?.durationSeconds,
          'file_size_bytes': recordingResult?.fileSizeBytes,
        },
      );

      // Step 3: Trigger face detection if enabled
      if (recordingResult?.collectionId != null) {
        await _recordingService!.triggerFaceDetection(
          sessionUuid: _activeSession!.sessionUuid,
          mediaUuid: recordingResult!.collectionId!,
          options: {
            'method': 'enhanced-v2',
            'auto_trigger': true,
          },
        );
      }

      // Step 4: Disconnect camera
      await _cameraService!.disconnectCamera(widget.cameraDeviceId);

      setState(() {
        _activeSession = null;
        _isRecording = false;
      });

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recording completed for ${widget.cameraName ?? widget.cameraDeviceId}'),
            backgroundColor: Colors.blue,
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

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(8.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  Icons.videocam,
                  color: _isRecording ? Colors.red : Colors.grey,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.cameraName ?? widget.cameraDeviceId,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                if (_isRecording)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Text(
                      'REC',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Session Information
            if (_activeSession != null) ...[
              _buildSessionInfo(),
              const SizedBox(height: 12),
            ],
            
            // Error Message
            if (_errorMessage != null) ...[
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: Colors.red.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error, color: Colors.red, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.red, fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],
            
            // Controls
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : (_isRecording ? _stopRecording : _startRecording),
                    icon: _isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(_isRecording ? Icons.stop : Icons.fiber_manual_record),
                    label: Text(_isRecording ? 'Stop Recording' : 'Start Recording'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _isRecording ? Colors.red : Colors.green,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _isLoading ? null : _loadActiveSessions,
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Refresh Status',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSessionInfo() {
    if (_activeSession == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.info, color: Colors.blue, size: 16),
              const SizedBox(width: 8),
              Text(
                'Recording Session',
                style: TextStyle(
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _buildInfoRow('Session ID', _activeSession!.sessionUuid.substring(0, 8) + '...'),
          _buildInfoRow('Status', _activeSession!.statusText),
          _buildInfoRow('Duration', _activeSession!.durationText),
          if (_activeSession!.framesRecorded != null)
            _buildInfoRow('Frames', _activeSession!.framesRecorded.toString()),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            '$label:',
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 12),
          ),
        ],
      ),
    );
  }
}

/// Phase 4 Recording Sessions Dashboard
/// 
/// Shows all active recording sessions across cameras
class RecordingSessionsDashboard extends ConsumerStatefulWidget {
  const RecordingSessionsDashboard({super.key});

  @override
  ConsumerState<RecordingSessionsDashboard> createState() => _RecordingSessionsDashboardState();
}

class _RecordingSessionsDashboardState extends ConsumerState<RecordingSessionsDashboard> {
  RecordingSessionService? _recordingService;
  SessionStatistics? _statistics;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _initializeService();
    _loadStatistics();
  }

  void _initializeService() {
    final authService = CameraAuthService(); // You might need to get this from provider
    _recordingService = RecordingSessionService(authService);
  }

  Future<void> _loadStatistics() async {
    if (_recordingService == null) return;
    
    setState(() {
      _isLoading = true;
    });

    try {
      _statistics = await _recordingService!.getSessionStatistics();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to load statistics: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.dashboard),
                const SizedBox(width: 8),
                Text(
                  'Recording Sessions Dashboard',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const Spacer(),
                IconButton(
                  onPressed: _isLoading ? null : _loadStatistics,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            if (_isLoading)
              const Center(child: CircularProgressIndicator())
            else if (_statistics != null)
              _buildStatisticsGrid()
            else
              const Center(
                child: Text('No statistics available'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatisticsGrid() {
    if (_statistics == null) return const SizedBox.shrink();

    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 2,
      children: [
        _buildStatCard(
          'Total Sessions',
          _statistics!.totalSessions.toString(),
          Icons.video_library,
          Colors.blue,
        ),
        _buildStatCard(
          'Active Sessions',
          _statistics!.activeSessions.toString(),
          Icons.fiber_manual_record,
          Colors.red,
        ),
        _buildStatCard(
          'Completed',
          _statistics!.completedSessions.toString(),
          Icons.check_circle,
          Colors.green,
        ),
        _buildStatCard(
          'Average Duration',
          '${_statistics!.averageDuration.toStringAsFixed(1)}s',
          Icons.timer,
          Colors.orange,
        ),
      ],
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: color is MaterialColor ? color.shade700 : color.withOpacity(0.7),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: color is MaterialColor ? color.shade800 : color.withOpacity(0.8),
            ),
          ),
        ],
      ),
    );
  }
}