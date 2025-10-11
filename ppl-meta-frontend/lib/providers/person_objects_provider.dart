/// PPL Meta Frontend - Person Objects Provider
/// 
/// Riverpod state management for PPL Thread (Person Objects) functionality.
/// Manages person objects data, workflow state, and integration with the
/// existing media processing workflow system.
/// 
/// Key Features:
/// - Automatic person objects loading for media items
/// - Workflow state management and progress tracking
/// - Integration with existing face detection workflow
/// - Caching and performance optimization
/// - Real-time status updates and notifications

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';
import 'dart:developer' as developer;

import '../models/person_objects_models.dart';
import '../services/person_objects_api_client.dart';
import '../core/api/api_client.dart';

// API Client Provider - uses the authenticated ApiClient from the global provider
final personObjectsApiClientProvider = Provider<PersonObjectsApiClient>((ref) {
  // Import the global apiClientProvider
  final apiClient = ref.watch(apiClientProvider);
  return PersonObjectsApiClient(apiClient);
});

// Person Objects Data Provider (per media UUID)
// Added keepAlive to prevent excessive re-fetching when multiple widgets watch the same data
final personObjectsDataProvider = FutureProvider.autoDispose
    .family<PersonObjectsData?, String>((ref, mediaUuid) async {
  // Keep the provider alive for 30 seconds to prevent excessive API calls
  ref.keepAlive();
  
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.getPersonObjectsForMedia(mediaUuid);
});

// Person Objects Session Data Provider (per session UUID)
final personObjectsSessionProvider = FutureProvider.autoDispose
    .family<PersonObjectsData?, String>((ref, sessionUuid) async {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.getPersonObjectsForSession(sessionUuid);
});

// Person Objects Availability Provider (per media UUID)
final personObjectsAvailabilityProvider = FutureProvider.autoDispose
    .family<bool, String>((ref, mediaUuid) async {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.hasPersonObjectsForMedia(mediaUuid);
});

// Workflow Status Provider
final workflowStatusProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>((ref, workflowId) async {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.getWorkflowStatus(workflowId);
});

// Session Statistics Provider
final personObjectsSessionStatisticsProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>((ref, sessionUuid) async {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.getSessionStatistics(sessionUuid);
});

// Person Objects Workflow State
enum PersonObjectsWorkflowState {
  idle,
  checking,
  triggering,
  processing,
  completed,
  failed,
}

// Person Objects Workflow Controller
class PersonObjectsWorkflowController extends StateNotifier<PersonObjectsWorkflowState> {
  PersonObjectsWorkflowController(this._apiClient) : super(PersonObjectsWorkflowState.idle);
  
  final PersonObjectsApiClient _apiClient;
  static const String _logName = 'PersonObjectsWorkflowController';
  
  String? _currentWorkflowId;
  String? _currentMediaUuid;
  PersonObjectsData? _lastResult;
  
  // Getters
  String? get currentWorkflowId => _currentWorkflowId;
  String? get currentMediaUuid => _currentMediaUuid;
  PersonObjectsData? get lastResult => _lastResult;
  bool get isProcessing => state != PersonObjectsWorkflowState.idle;
  
  /// Auto-trigger person objects workflow for a media item
  Future<PersonObjectsData?> autoTriggerWorkflow(String mediaUuid) async {
    try {
      state = PersonObjectsWorkflowState.checking;
      _currentMediaUuid = mediaUuid;
      
      developer.log(
        'Auto-triggering person objects workflow for: $mediaUuid',
        name: _logName,
      );
      
      // Check if person objects already exist
      final existing = await _apiClient.getPersonObjectsForMedia(mediaUuid);
      
      debugPrint('🎯 CONTROLLER: getPersonObjectsForMedia returned: ${existing?.totalPersons ?? "null"} (success: ${existing?.success}) for $mediaUuid');
      
      // Only consider it as "existing" if we have a successful result with actual persons
      if (existing != null && existing.success && existing.totalPersons > 0) {
        debugPrint('🎯 CONTROLLER: Valid person objects already exist (${existing.totalPersons} persons), not triggering workflow');
        
        state = PersonObjectsWorkflowState.completed;
        _lastResult = existing;
        
        developer.log(
          'Person objects already available for: $mediaUuid (${existing.totalPersons} persons)',
          name: _logName,
        );
        
        return existing;
      }
      
      debugPrint('🎯 CONTROLLER: No valid person objects found (result: ${existing?.success == true ? "success but 0 persons" : "failed/null"}), proceeding to trigger workflow');
      
      // Trigger new workflow
      state = PersonObjectsWorkflowState.triggering;
      
      debugPrint('🎯 CONTROLLER: About to call _apiClient.autoTriggerPersonObjectsWorkflow for $mediaUuid');
      
      final result = await _apiClient.autoTriggerPersonObjectsWorkflow(mediaUuid);
      
      debugPrint('🎯 CONTROLLER: Result from autoTriggerPersonObjectsWorkflow: ${result?.totalPersons ?? "null"}');
      
      if (result != null) {
        state = PersonObjectsWorkflowState.completed;
        _currentWorkflowId = result.workflowId;
        _lastResult = result;
        
        developer.log(
          'Person objects workflow completed: ${result.workflowId} (${result.totalPersons} persons)',
          name: _logName,
        );
        
        // No need to invalidate providers since widget uses workflow result directly
        developer.log(
          'Workflow result available for UI: ${result.totalPersons} persons',
          name: _logName,
        );
        
        return result;
      } else {
        state = PersonObjectsWorkflowState.failed;
        developer.log(
          'Person objects workflow failed for: $mediaUuid',
          name: _logName,
        );
        return null;
      }
      
    } catch (e) {
      state = PersonObjectsWorkflowState.failed;
      developer.log(
        'Error in auto-trigger workflow for $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
  
  /// Manually start person objects workflow with custom parameters
  Future<PersonObjectsData?> startWorkflow(
    String sessionUuid, {
    double tolerancePercent = 20.0,
    bool enableQualityAnalysis = true,
    bool enableAgeDetection = true,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      state = PersonObjectsWorkflowState.processing;
      
      developer.log(
        'Starting person objects workflow for session: $sessionUuid',
        name: _logName,
      );
      
      final result = await _apiClient.startPersonObjectsWorkflow(
        sessionUuid,
        tolerancePercent: tolerancePercent,
        enableQualityAnalysis: enableQualityAnalysis,
        enableAgeDetection: enableAgeDetection,
        workflowMetadata: metadata,
      );
      
      if (result != null) {
        state = PersonObjectsWorkflowState.completed;
        _currentWorkflowId = result.workflowId;
        _lastResult = result;
        
        developer.log(
          'Person objects workflow started successfully: ${result.workflowId}',
          name: _logName,
        );
        
        return result;
      } else {
        state = PersonObjectsWorkflowState.failed;
        return null;
      }
      
    } catch (e) {
      state = PersonObjectsWorkflowState.failed;
      developer.log(
        'Error starting workflow for $sessionUuid: $e',
        name: _logName,
        error: e,
      );
      rethrow;
    }
  }
  
  /// Reset workflow state
  void reset() {
    state = PersonObjectsWorkflowState.idle;
    _currentWorkflowId = null;
    _currentMediaUuid = null;
    _lastResult = null;
  }
  
  /// Check workflow status
  Future<Map<String, dynamic>?> checkWorkflowStatus() async {
    if (_currentWorkflowId == null) return null;
    
    try {
      return await _apiClient.getWorkflowStatus(_currentWorkflowId!);
    } catch (e) {
      developer.log(
        'Error checking workflow status: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
  
  /// Trigger PPL Thread workflow for legacy media with face detections but no sessions
  Future<PersonObjectsData?> triggerLegacyMediaWorkflow(String mediaUuid) async {
    try {
      state = PersonObjectsWorkflowState.processing;
      _currentMediaUuid = mediaUuid;
      
      developer.log(
        'Triggering PPL Thread workflow for legacy media: $mediaUuid',
        name: _logName,
      );
      
      // Call the PPL Thread workflow trigger endpoint directly
      final result = await _apiClient.triggerPPLThreadWorkflow(mediaUuid);
      
      if (result != null) {
        state = PersonObjectsWorkflowState.completed;
        _currentWorkflowId = result.workflowId;
        _lastResult = result;
        
        developer.log(
          'PPL Thread workflow completed for legacy media: ${result.workflowId} (${result.totalPersons} persons)',
          name: _logName,
        );
        
        return result;
      } else {
        state = PersonObjectsWorkflowState.failed;
        developer.log(
          'PPL Thread workflow failed for legacy media: $mediaUuid',
          name: _logName,
        );
        return null;
      }
      
    } catch (e) {
      state = PersonObjectsWorkflowState.failed;
      developer.log(
        'Error in PPL Thread workflow for legacy media $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
}

// Person Objects Workflow Controller Provider
final personObjectsWorkflowControllerProvider = 
    StateNotifierProvider<PersonObjectsWorkflowController, PersonObjectsWorkflowState>((ref) {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return PersonObjectsWorkflowController(apiClient);
});

// Batch Person Objects Availability Provider
final batchPersonObjectsAvailabilityProvider = FutureProvider.autoDispose
    .family<Map<String, bool>, List<String>>((ref, mediaUuids) async {
  final apiClient = ref.read(personObjectsApiClientProvider);
  return await apiClient.batchCheckPersonObjects(mediaUuids);
});

// Person Objects Summary Provider (derived from data)
final personObjectsSummaryProvider = Provider.autoDispose
    .family<PersonObjectsSummary?, String>((ref, mediaUuid) {
  final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaUuid));
  
  return personObjectsAsync.when(
    data: (data) => data?.summary,
    loading: () => null,
    error: (error, stack) => null,
  );
});

// Helper provider to check if person objects should be automatically loaded
final shouldAutoLoadPersonObjectsProvider = Provider.autoDispose
    .family<bool, String>((ref, mediaUuid) {
  // Auto-load if face detection is completed
  // This can be enhanced with user preferences
  return true; // For now, always attempt to auto-load
});

// Person Objects Statistics for UI Display
class PersonObjectsUIStats {
  final int totalPersons;
  final int totalFaces;
  final int qualityAnalysisCount;
  final double groupingEfficiency;
  final String processingTime;
  final bool hasAgeDetection;
  
  const PersonObjectsUIStats({
    required this.totalPersons,
    required this.totalFaces,
    required this.qualityAnalysisCount,
    required this.groupingEfficiency,
    required this.processingTime,
    required this.hasAgeDetection,
  });
  
  factory PersonObjectsUIStats.fromPersonObjectsData(PersonObjectsData data) {
    final hasAge = data.bestQualityFaces.values
        .any((face) => face.ageDetection.hasValidAge);
    
    return PersonObjectsUIStats(
      totalPersons: data.totalPersons,
      totalFaces: data.originalGroups,
      qualityAnalysisCount: data.bestQualityFaces.length,
      groupingEfficiency: data.statistics.groupingEfficiency,
      processingTime: data.processingTimestamp,
      hasAgeDetection: hasAge,
    );
  }
  
  String get compactDisplay => '$totalPersons persons from $totalFaces faces';
  
  String get efficiencyDisplay => '${groupingEfficiency.toStringAsFixed(1)}% grouping efficiency';
}

// UI Stats Provider
final personObjectsUIStatsProvider = Provider.autoDispose
    .family<PersonObjectsUIStats?, String>((ref, mediaUuid) {
  final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaUuid));
  
  return personObjectsAsync.when(
    data: (data) => data != null ? PersonObjectsUIStats.fromPersonObjectsData(data) : null,
    loading: () => null,
    error: (error, stack) => null,
  );
});

// Enhanced Media Processing Integration
// This extends the existing workflow system to include person objects
extension PersonObjectsWorkflowIntegration on Ref {
  /// Trigger person objects workflow after face detection completes
  Future<void> triggerPersonObjectsAfterFaceDetection(String mediaUuid) async {
    try {
      final controller = read(personObjectsWorkflowControllerProvider.notifier);
      
      // Wait a bit for face detection to settle
      await Future.delayed(const Duration(seconds: 2));
      
      // Auto-trigger person objects workflow
      await controller.autoTriggerWorkflow(mediaUuid);
      
      // Invalidate providers to refresh UI
      invalidate(personObjectsDataProvider(mediaUuid));
      invalidate(personObjectsAvailabilityProvider(mediaUuid));
      
    } catch (e) {
      developer.log(
        'Failed to trigger person objects after face detection: $e',
        name: 'PersonObjectsWorkflowIntegration',
        error: e,
      );
    }
  }
}