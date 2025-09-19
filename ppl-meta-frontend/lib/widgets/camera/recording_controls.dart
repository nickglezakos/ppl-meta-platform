import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';
import '../../core/models/camera.dart';
import '../../core/providers/camera_providers.dart';
// import '../../widgets/common/status_indicator.dart';

/// Widget for manual camera recording controls
/// Provides start/stop recording functionality with real-time status
class RecordingControls extends ConsumerStatefulWidget {
  final String? selectedDeviceId;
  final Function()? onRecordingStarted;
  final Function()? onRecordingStopped;

  const RecordingControls({
    Key? key,
    this.selectedDeviceId,
    this.onRecordingStarted,
    this.onRecordingStopped,
  }) : super(key: key);

  @override
  ConsumerState<RecordingControls> createState() => _RecordingControlsState();
}

class _RecordingControlsState extends ConsumerState<RecordingControls>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  Timer? _recordingTimer;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(seconds: 1),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _recordingTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final recordingState = ref.watch(recordingStateProvider(widget.selectedDeviceId));
    final automationSettings = ref.watch(automationSettingsProvider);

    // Start/stop pulse animation based on recording state
    if (recordingState.isRecording && !_pulseController.isAnimating) {
      _pulseController.repeat(reverse: true);
    } else if (!recordingState.isRecording && _pulseController.isAnimating) {
      _pulseController.stop();
      _pulseController.reset();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            Text(
              'Recording Controls',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 20),
            
            // Main recording button
            _buildRecordingButton(context, recordingState),
            
            const SizedBox(height: 20),
            
            // Recording status and timer
            _buildStatusSection(context, recordingState),
            
            const SizedBox(height: 16),
            
            // Quick automation settings
            _buildQuickSettings(context, automationSettings),
            
            const SizedBox(height: 16),
            
            // Advanced settings button
            _buildAdvancedSettingsButton(context),
          ],
        ),
      ),
    );
  }

  Widget _buildRecordingButton(BuildContext context, RecordingState recordingState) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDisabled = widget.selectedDeviceId == null || recordingState.isConnecting;

    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: recordingState.isRecording ? _pulseAnimation.value : 1.0,
          child: SizedBox(
            width: 120,
            height: 120,
            child: ElevatedButton(
              onPressed: isDisabled ? null : _toggleRecording,
              style: ElevatedButton.styleFrom(
                backgroundColor: recordingState.isRecording 
                    ? colorScheme.error 
                    : colorScheme.primary,
                foregroundColor: Colors.white,
                shape: const CircleBorder(),
                elevation: recordingState.isRecording ? 8 : 4,
              ),
              child: recordingState.isConnecting
                  ? const CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 3,
                    )
                  : Icon(
                      recordingState.isRecording ? Icons.stop : Icons.fiber_manual_record,
                      size: 48,
                    ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusSection(BuildContext context, RecordingState recordingState) {
    final theme = Theme.of(context);

    return Column(
      children: [
        // Recording status indicator
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            StatusIndicator(
              status: recordingState.status,
              size: 12,
            ),
            const SizedBox(width: 8),
            Text(
              recordingState.statusText,
              style: theme.textTheme.titleMedium,
            ),
          ],
        ),
        
        const SizedBox(height: 8),
        
        // Recording timer
        if (recordingState.isRecording)
          RecordingTimer(
            startTime: recordingState.startTime!,
            style: theme.textTheme.headlineMedium?.copyWith(
              fontFamily: 'monospace',
              fontWeight: FontWeight.bold,
            ),
          ),
          
        // Device info
        if (widget.selectedDeviceId != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Device: ${widget.selectedDeviceId}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildQuickSettings(BuildContext context, AutomationSettings settings) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick Settings',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: AutomationQuickToggle(
                label: 'Auto Face Detection',
                value: settings.autoFaceDetectionEnabled,
                onChanged: (value) => ref
                    .read(automationSettingsProvider.notifier)
                    .updateAutoFaceDetection(value),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: AutomationQuickToggle(
                label: 'Notifications',
                value: settings.notificationsEnabled,
                onChanged: (value) => ref
                    .read(automationSettingsProvider.notifier)
                    .updateNotifications(value),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildAdvancedSettingsButton(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () => _showAdvancedSettings(context),
      icon: const Icon(Icons.settings),
      label: const Text('Advanced Settings'),
    );
  }

  void _toggleRecording() async {
    if (widget.selectedDeviceId == null) return;

    final recordingNotifier = ref.read(recordingStateProvider(widget.selectedDeviceId).notifier);
    final currentState = ref.read(recordingStateProvider(widget.selectedDeviceId));

    try {
      if (currentState.isRecording) {
        await recordingNotifier.stopRecording();
        widget.onRecordingStopped?.call();
      } else {
        await recordingNotifier.startRecording();
        widget.onRecordingStarted?.call();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recording error: ${e.toString()}'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }

  void _showAdvancedSettings(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => RecordingSettingsSheet(
        deviceId: widget.selectedDeviceId,
      ),
    );
  }
}

/// Timer widget that shows recording duration
class RecordingTimer extends StatefulWidget {
  final DateTime startTime;
  final TextStyle? style;

  const RecordingTimer({
    Key? key,
    required this.startTime,
    this.style,
  }) : super(key: key);

  @override
  State<RecordingTimer> createState() => _RecordingTimerState();
}

class _RecordingTimerState extends State<RecordingTimer> {
  Timer? _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {
          _elapsed = DateTime.now().difference(widget.startTime);
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      _formatDuration(_elapsed),
      style: widget.style,
    );
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours.toString().padLeft(2, '0');
    final minutes = (duration.inMinutes % 60).toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    
    if (duration.inHours > 0) {
      return '$hours:$minutes:$seconds';
    } else {
      return '$minutes:$seconds';
    }
  }
}

/// Quick toggle widget for automation settings
class AutomationQuickToggle extends StatelessWidget {
  final String label;
  final bool value;
  final Function(bool) onChanged;

  const AutomationQuickToggle({
    Key? key,
    required this.label,
    required this.value,
    required this.onChanged,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Switch.adaptive(
          value: value,
          onChanged: onChanged,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}

/// Advanced recording settings bottom sheet
class RecordingSettingsSheet extends ConsumerWidget {
  final String? deviceId;

  const RecordingSettingsSheet({
    Key? key,
    this.deviceId,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      maxChildSize: 0.9,
      builder: (context, scrollController) {
        return Container(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Recording Settings',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView(
                  controller: scrollController,
                  children: [
                    // Recording quality settings
                    _buildQualitySettings(context, ref),
                    const SizedBox(height: 16),
                    
                    // Duration settings
                    _buildDurationSettings(context, ref),
                    const SizedBox(height: 16),
                    
                    // Face detection method settings
                    _buildFaceDetectionSettings(context, ref),
                    const SizedBox(height: 16),
                    
                    // Storage settings
                    _buildStorageSettings(context, ref),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildQualitySettings(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recording Quality',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            // Quality selection implementation
            Text(
              'Quality settings will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDurationSettings(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recording Duration',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            // Duration settings implementation
            Text(
              'Duration settings will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFaceDetectionSettings(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Face Detection',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            // Face detection method selection implementation
            Text(
              'Face detection method selection will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStorageSettings(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Storage Options',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            // Storage settings implementation
            Text(
              'Storage settings will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}