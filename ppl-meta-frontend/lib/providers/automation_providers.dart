import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/automation_models.dart';
import '../core/api/api_client.dart';

/// Provider for API client
final apiClientProvider = Provider<ApiClient>((ref) {
  throw UnimplementedError('ApiClient provider not initialized');
});

/// Provider for automation rules
final automationRulesProvider = FutureProvider<List<AutomationRule>>((ref) async {
  try {
    // TODO: Replace with actual API call when backend is ready
    // final client = ref.read(apiClientProvider);
    // final rules = await client.getAutomationRules();
    // return rules;
    
    // Return mock data for now
    await Future.delayed(const Duration(milliseconds: 500)); // Simulate API delay
    return _generateMockRules();
  } catch (e) {
    // Return empty list if backend not ready
    return <AutomationRule>[];
  }
});

/// Provider for automation execution history
final automationExecutionHistoryProvider = FutureProvider<List<AutomationExecution>>((ref) async {
  try {
    // TODO: Replace with actual API call when backend is ready
    // final client = ref.read(apiClientProvider);
    // final executions = await client.getAutomationHistory();
    // return executions;
    
    // Return mock data for now
    await Future.delayed(const Duration(milliseconds: 300)); // Simulate API delay
    return _generateMockExecutions();
  } catch (e) {
    // Return empty list if backend not ready
    return <AutomationExecution>[];
  }
});

/// Provider for automation metrics
final automationMetricsProvider = FutureProvider<AutomationMetrics>((ref) async {
  try {
    // TODO: Replace with actual API call when backend is ready
    // final client = ref.read(apiClientProvider);
    // final metrics = await client.getAutomationMetrics();
    // return metrics;
    
    // Return mock data for now
    await Future.delayed(const Duration(milliseconds: 200)); // Simulate API delay
    return _generateMockMetrics();
  } catch (e) {
    // Return default metrics if backend not ready
    return const AutomationMetrics(
      activeRulesCount: 0,
      executionsToday: 0,
      successRate: 0.0,
      totalExecutions: 0,
      lastExecution: null,
    );
  }
});

/// Provider for automation engine status
final automationEngineStatusProvider = FutureProvider<AutomationEngineStatus>((ref) async {
  try {
    // TODO: Replace with actual API call when backend is ready
    // final client = ref.read(apiClientProvider);
    // final status = await client.getAutomationEngineStatus();
    // return status;
    
    // Return mock data for now
    await Future.delayed(const Duration(milliseconds: 100)); // Simulate API delay
    return AutomationEngineStatus(
      isRunning: true,
      version: '1.0.0',
      lastStartup: DateTime.now().subtract(const Duration(hours: 2)),
      processedEvents: 1247,
    );
  } catch (e) {
    // Return default status if backend not ready
    return const AutomationEngineStatus(
      isRunning: true,
      version: '1.0.0',
      lastStartup: null,
      processedEvents: 0,
    );
  }
});

/// Provider for real-time automation events
final automationEventsProvider = StreamProvider<AutomationEvent>((ref) async* {
  try {
    // TODO: Replace with actual WebSocket stream when backend is ready
    // final client = ref.read(apiClientProvider);
    // await for (final event in client.getAutomationEventsStream()) {
    //   yield event;
    // }
    
    // Simulate some events for demo
    yield* _generateMockEventStream();
  } catch (e) {
    // Emit empty stream if websocket not available
    yield* const Stream<AutomationEvent>.empty();
  }
});

// Mock data generators for development
List<AutomationRule> _generateMockRules() {
  return [
    AutomationRule(
      id: '1',
      name: 'Face Detection Alert',
      description: 'Send notification when face is detected on main camera',
      triggerType: 'face_detected',
      actions: ['send_notification', 'capture_snapshot'],
      isActive: true,
      createdAt: DateTime.now().subtract(const Duration(days: 5)),
      updatedAt: DateTime.now().subtract(const Duration(hours: 2)),
      lastExecuted: DateTime.now().subtract(const Duration(minutes: 30)),
      executionCount: 124,
      successRate: 0.96,
    ),
    AutomationRule(
      id: '2',
      name: 'Motion Detection Recording',
      description: 'Start recording when motion is detected',
      triggerType: 'motion_detected',
      actions: ['start_recording', 'send_notification'],
      isActive: true,
      createdAt: DateTime.now().subtract(const Duration(days: 10)),
      updatedAt: DateTime.now().subtract(const Duration(days: 1)),
      lastExecuted: DateTime.now().subtract(const Duration(hours: 1)),
      executionCount: 67,
      successRate: 0.88,
    ),
    AutomationRule(
      id: '3',
      name: 'Scheduled Backup',
      description: 'Daily backup of recorded media',
      triggerType: 'schedule',
      actions: ['backup_media', 'cleanup_old_files'],
      isActive: false,
      createdAt: DateTime.now().subtract(const Duration(days: 15)),
      updatedAt: DateTime.now().subtract(const Duration(days: 3)),
      lastExecuted: DateTime.now().subtract(const Duration(days: 1)),
      executionCount: 15,
      successRate: 1.0,
    ),
  ];
}

List<AutomationExecution> _generateMockExecutions() {
  return [
    AutomationExecution(
      id: 'exec_1',
      ruleId: '1',
      ruleName: 'Face Detection Alert',
      startedAt: DateTime.now().subtract(const Duration(minutes: 30)),
      completedAt: DateTime.now().subtract(const Duration(minutes: 29)),
      status: 'completed',
    ),
    AutomationExecution(
      id: 'exec_2',
      ruleId: '2',
      ruleName: 'Motion Detection Recording',
      startedAt: DateTime.now().subtract(const Duration(hours: 1)),
      completedAt: DateTime.now().subtract(const Duration(minutes: 58)),
      status: 'completed',
    ),
    AutomationExecution(
      id: 'exec_3',
      ruleId: '1',
      ruleName: 'Face Detection Alert',
      startedAt: DateTime.now().subtract(const Duration(hours: 2)),
      completedAt: DateTime.now().subtract(const Duration(hours: 2)),
      status: 'failed',
      errorMessage: 'Network timeout while sending notification',
    ),
  ];
}

AutomationMetrics _generateMockMetrics() {
  return AutomationMetrics(
    activeRulesCount: 2,
    executionsToday: 15,
    successRate: 0.93,
    totalExecutions: 206,
    lastExecution: DateTime.now().subtract(const Duration(minutes: 30)),
  );
}

Stream<AutomationEvent> _generateMockEventStream() async* {
  // Simulate periodic automation events
  while (true) {
    await Future.delayed(const Duration(seconds: 30));
    yield AutomationEvent(
      id: 'event_${DateTime.now().millisecondsSinceEpoch}',
      type: 'rule_executed',
      timestamp: DateTime.now(),
      ruleId: '1',
      data: {'camera_id': 'main_camera', 'confidence': 0.95},
    );
  }
}