/// PPL Meta Frontend - Person Objects API Client
/// 
/// API client for PPL Thread (Person Objects) functionality integration.
/// Provides access to Vision Service person objects endpoints and handles
/// data transformation between the backend and frontend models.
/// 
/// Key Features:
/// - Vision Service discovery and connection
/// - Person objects data retrieval by media UUID
/// - Workflow triggering and status monitoring
/// - Error handling and logging
/// - Type-safe data transformation

import 'dart:convert';
import 'dart:developer' as developer;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../models/person_objects_models.dart';
import '../core/api/api_client.dart';
import '../services/discovery_service_client.dart';
import '../core/config/app_config.dart';

class PersonObjectsApiClient {
  late final ApiClient _apiClient;
  final DiscoveryServiceClient _discoveryService = DiscoveryServiceClient();
  
  static const String _logName = 'PersonObjectsApiClient';
  
  PersonObjectsApiClient([ApiClient? apiClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }
  
  /// Get person objects for a media item (via Orchestrator endpoint)
  Future<PersonObjectsData?> getPersonObjectsForMedia(String mediaUuid) async {
    try {
      developer.log(
        'Getting person objects for media: $mediaUuid via Orchestrator',
        name: _logName,
      );

      // 🚀 PERSON OBJECTS API: Call Orchestrator service directly (port 8002)
      // This uses the actual person objects endpoint with grouping and tracking
      developer.log(
        'Getting person objects from Orchestrator for media: $mediaUuid',
        name: _logName,
      );

      // Use Person Objects endpoint directly to Orchestrator
      final orchestratorUrl = 'http://localhost:8002';
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = orchestratorUrl;
      
      final response = await _apiClient.get(
        '/person-objects/$mediaUuid',
      );
      
      _apiClient.dio.options.baseUrl = originalBaseUrl;

      developer.log(
        'Orchestrator response: status=${response.statusCode}, data=${response.data}',
        name: _logName,
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data;
        
        developer.log(
          'Successfully retrieved Person Objects response: ${data['total_persons']} persons from ${data['total_faces']} faces',
          name: _logName,
        );
        
        // Transform Person Objects response to PersonObjectsData format
        final totalFaces = data['total_faces'] ?? 0;
        final totalPersons = data['total_persons'] ?? 0; // Use actual person grouping count
        final sessionUuid = data['session_uuid'] ?? mediaUuid;
        final status = data['status'] ?? 'unknown';
        final groupingAlgorithm = data['grouping_algorithm'] ?? 'rectangle_overlap_detection';
        final processingTimeMs = data['processing_time_ms'] ?? 0.0;
        
        developer.log(
          'Person Objects data: totalFaces=$totalFaces, totalPersons=$totalPersons, algorithm=$groupingAlgorithm',
          name: _logName,
        );
        
        print('🎯 PERSON OBJECTS DATA: totalPersons=$totalPersons, totalFaces=$totalFaces, algorithm=$groupingAlgorithm');
        
        final personObjectsData = PersonObjectsData(
          workflowId: data['media_id'] ?? mediaUuid,
          sessionUuid: sessionUuid,
          success: data['success'] ?? false,
          originalGroups: totalFaces,
          mergedGroups: totalPersons,
          totalPersons: totalPersons,
          groupTracking: [],
          statistics: PersonObjectsStatistics(
            totalGroups: totalPersons,
            originalUniqueFaces: totalFaces,
            mergedGroupsCount: totalPersons,
            totalDetections: totalFaces,
            framesProcessed: 0,
            groupingAlgorithm: groupingAlgorithm,
            tolerancePercent: 20.0,
            trackedFaces: totalFaces,
            newFaces: 0,
            mergeIterations: 1,
          ),
          bestQualityFaces: {},
          classifiedFaces: _extractClassifiedFaces(data),
          processingTimestamp: DateTime.now().toIso8601String(),
          workflowType: status == 'completed' ? 'bulk_processing_complete' : 'processing',
        );
        
        print('🎯 CREATED PersonObjectsData: totalPersons=${personObjectsData.totalPersons}');
        return personObjectsData;
      } else {
        developer.log(
          'No person objects found for media: $mediaUuid (status: ${response.statusCode})',
          name: _logName,
        );
        
        // Return null to indicate no data available (UI will handle this gracefully)
        return null;
      }
      
    } catch (e) {
      developer.log(
        'Failed to get person objects for media $mediaUuid via Orchestrator: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }

  /// Extract classified faces from person objects response
  List<ClassifiedFace> _extractClassifiedFaces(Map<String, dynamic> data) {
    final classifiedFaces = <ClassifiedFace>[];
    
    // Extract faces from person_groups if available
    final personGroups = data['person_groups'] as List<dynamic>?;
    if (personGroups != null) {
      for (var group in personGroups) {
        final personId = group['person_id'] ?? 'unknown_person';
        
        // Add representative faces
        final representativeFaces = group['representative_faces'] as List<dynamic>?;
        if (representativeFaces != null) {
          for (var i = 0; i < representativeFaces.length; i++) {
            final face = representativeFaces[i];
            final faceData = face['face_data'];
            if (faceData != null) {
              final classifiedFace = ClassifiedFace(
                personId: personId,
                faceDetectionId: 'face_${classifiedFaces.length + 1}',
                matchType: 'representative_face',
                matchDistance: (face['quality_score'] ?? 0).toDouble(),
                frameNumber: faceData['frame_number'] ?? 0,
                positionX: (faceData['center_x'] ?? 0).toDouble(),
                positionY: (faceData['center_y'] ?? 0).toDouble(),
              );
              classifiedFaces.add(classifiedFace);
            }
          }
        }
      }
    }
    
    developer.log(
      'Extracted ${classifiedFaces.length} classified faces from person objects data',
      name: _logName,
    );
    
    return classifiedFaces;
  }
  
  /// Get person objects for a specific session
  Future<PersonObjectsData?> getPersonObjectsForSession(String sessionUuid) async {
    try {
      developer.log(
        'Getting person objects for session: $sessionUuid',
        name: _logName,
      );

      // Use gateway routing instead of direct service discovery
      final visionServiceUrl = 'http://localhost:8080';

      // Temporarily set base URL to Vision service via gateway
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = visionServiceUrl;
      
      final response = await _apiClient.get(
        '/api/v1/person-objects/sessions/$sessionUuid',
      );
      
      // Restore original base URL
      _apiClient.dio.options.baseUrl = originalBaseUrl;

      if (response.statusCode == 200 && response.data != null) {
        final personObjects = PersonObjectsData.fromJson(response.data);
        
        developer.log(
          'Successfully retrieved person objects: ${personObjects.totalPersons} persons from ${personObjects.originalGroups} faces',
          name: _logName,
        );
        
        return personObjects;
      } else if (response.statusCode == 404) {
        // No person objects found - this is normal for unprocessed sessions
        developer.log(
          'No person objects found for session: $sessionUuid',
          name: _logName,
        );
        return null;
      } else {
        throw Exception('Failed to get person objects: ${response.statusCode}');
      }
      
    } catch (e) {
      developer.log(
        'Failed to get person objects for session $sessionUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
  
  /// Start person objects workflow for a session
  Future<PersonObjectsData?> startPersonObjectsWorkflow(
    String sessionUuid, {
    double tolerancePercent = 20.0,
    bool enableQualityAnalysis = true,
    bool enableAgeDetection = true,
    Map<String, dynamic>? workflowMetadata,
  }) async {
    try {
      developer.log(
        'Starting person objects workflow for session: $sessionUuid (tolerance: $tolerancePercent%)',
        name: _logName,
      );

      // Use gateway routing instead of direct service discovery
      final visionServiceUrl = 'http://localhost:8080';

      final requestBody = {
        'session_uuid': sessionUuid,
        'tolerance_percent': tolerancePercent,
        'enable_quality_analysis': enableQualityAnalysis,
        'enable_age_detection': enableAgeDetection,
        if (workflowMetadata != null) 'workflow_metadata': workflowMetadata,
      };

      // Temporarily set base URL to Vision service via gateway
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = visionServiceUrl;
      
      final response = await _apiClient.post(
        '/api/v1/person-objects/workflows/start',
        data: requestBody,
      );
      
      // Restore original base URL
      _apiClient.dio.options.baseUrl = originalBaseUrl;

      if (response.statusCode == 200 && response.data != null) {
        final personObjects = PersonObjectsData.fromJson(response.data);
        
        developer.log(
          'Person objects workflow completed successfully: ${personObjects.workflowId}',
          name: _logName,
        );
        
        return personObjects;
      } else {
        final error = 'Failed to start person objects workflow: ${response.statusCode} - ${response.data}';
        developer.log(error, name: _logName);
        throw Exception(error);
      }
      
    } catch (e) {
      developer.log(
        'Failed to start person objects workflow for session $sessionUuid: $e',
        name: _logName,
        error: e,
      );
      rethrow;
    }
  }
  
  /// Get workflow status for a person objects workflow
  Future<Map<String, dynamic>?> getWorkflowStatus(String workflowId) async {
    try {
      developer.log(
        'Getting workflow status: $workflowId',
        name: _logName,
      );

      // Use gateway routing instead of direct service discovery
      final visionServiceUrl = 'http://localhost:8080';

      // Temporarily set base URL to Vision service via gateway
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = visionServiceUrl;
      
      final response = await _apiClient.get(
        '/api/v1/person-objects/workflows/$workflowId/status',
      );
      
      // Restore original base URL
      _apiClient.dio.options.baseUrl = originalBaseUrl;

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data;
        developer.log(
          'Workflow status retrieved: ${data['status']}',
          name: _logName,
        );
        return data;
      } else {
        throw Exception('Failed to get workflow status: ${response.statusCode}');
      }
      
    } catch (e) {
      developer.log(
        'Failed to get workflow status for $workflowId: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
  
  /// Get session statistics for person objects
  Future<Map<String, dynamic>?> getSessionStatistics(String sessionUuid) async {
    try {
      developer.log(
        'Getting session statistics: $sessionUuid',
        name: _logName,
      );

      // Use gateway routing instead of direct service discovery
      final visionServiceUrl = 'http://localhost:8080';

      // Temporarily set base URL to Vision service via gateway
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = visionServiceUrl;
      
      final response = await _apiClient.get(
        '/api/v1/person-objects/sessions/$sessionUuid/statistics',
      );
      
      // Restore original base URL
      _apiClient.dio.options.baseUrl = originalBaseUrl;

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data;
        developer.log(
          'Session statistics retrieved: ${data['total_person_objects']} persons',
          name: _logName,
        );
        return data;
      } else {
        throw Exception('Failed to get session statistics: ${response.statusCode}');
      }
      
    } catch (e) {
      developer.log(
        'Failed to get session statistics for $sessionUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }

  /// Check if person objects are available for a media item
  Future<bool> hasPersonObjectsForMedia(String mediaUuid) async {
    try {
      final sessionUuid = await _getSessionUuidForMedia(mediaUuid);
      if (sessionUuid == null) return false;
      
      final personObjects = await getPersonObjectsForSession(sessionUuid);
      return personObjects != null && personObjects.success;
      
    } catch (e) {
      developer.log(
        'Failed to check person objects availability for $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return false;
    }
  }

  /// Automatically trigger person objects workflow if conditions are met
  Future<PersonObjectsData?> autoTriggerPersonObjectsWorkflow(String mediaUuid) async {
    debugPrint('🎯 ENTRY: autoTriggerPersonObjectsWorkflow called for mediaUuid: $mediaUuid');
    debugPrint('🆕 NEW CODE VERSION: Using direct workflow approach (v2.0)');
    
    try {
      debugPrint('🎯 STARTING: Auto-triggering person objects workflow for media: $mediaUuid');
      
      developer.log(
        'Auto-triggering person objects workflow for media: $mediaUuid',
        name: _logName,
      );

      // Check if person objects already exist and are valid
      final existing = await getPersonObjectsForMedia(mediaUuid);
      if (existing != null && existing.success && existing.totalPersons > 0) {
        debugPrint('✅ EXISTING VALID: Person objects already exist for media: $mediaUuid (persons: ${existing.totalPersons})');
        developer.log(
          'Person objects already exist for media: $mediaUuid (persons: ${existing.totalPersons})',
          name: _logName,
        );
        return existing;
      } else if (existing != null) {
        debugPrint('🔄 PLACEHOLDER DETECTED: Found placeholder/failed result for media: $mediaUuid (success: ${existing.success}, persons: ${existing.totalPersons})');
      } else {
        debugPrint('❌ NO DATA: No person objects found for media: $mediaUuid');
      }

      // Try using Orchestrator's bulk processing which can handle media without sessions
      debugPrint('🚀 ORCHESTRATOR APPROACH: Attempting bulk face detection workflow via Orchestrator for media: $mediaUuid');
      
      try {
        final response = await _apiClient.post(
          '/api/v1/orchestrator/workflows/face-detection/bulk-process',
          data: {
            'media_ids': [mediaUuid],
            'method': 'cached_faces',
            'confidence_threshold': 0.7,
            'store_results': true,
            'workflow_metadata': {
              'triggered_by': 'auto_trigger_person_objects',
              'frontend_initiated': true,
              'enable_person_objects': true,
            },
          },
        );
        
        debugPrint('🎯 ORCHESTRATOR RESPONSE: statusCode=${response.statusCode}, data=${response.data}');
        
        if (response.statusCode == 200 && response.data != null) {
          final workflowId = response.data['workflow_id'] as String?;
          final status = response.data['status'] as String?;
          debugPrint('✅ ORCHESTRATOR SUCCESS: workflowId=$workflowId, status=$status');
          
          if (workflowId != null) {
            // Poll workflow status until completion using proper async/await
            debugPrint('📊 MONITORING: Awaiting workflow completion via status polling...');
            
            String? finalStatus = await _pollWorkflowCompletion(workflowId);
            
            if (finalStatus == 'completed') {
              debugPrint('� FETCHING: Getting person objects data after successful workflow completion...');
              final result = await getPersonObjectsForMedia(mediaUuid);
              debugPrint('🎯 FINAL RESULT: ${result?.totalPersons} persons found');
              return result;
            } else {
              debugPrint('💔 WORKFLOW INCOMPLETE: Final status was $finalStatus, cannot fetch person objects');
              return null;
            }
          }
        }
        
        debugPrint('❌ ORCHESTRATOR FAILED: Unexpected response: ${response.statusCode}');
        return null;
        
      } catch (orchestratorError) {
        debugPrint('❌ ORCHESTRATOR ERROR: $orchestratorError');
        
        // Fall back to session-based approach if orchestrator workflow fails
        debugPrint('🔄 FALLBACK: Trying session-based approach due to orchestrator error...');
        
        // Get session UUID and trigger workflow
        var sessionUuid = await _getSessionUuidForMedia(mediaUuid);
        debugPrint('🔍 SESSION LOOKUP: mediaUuid=$mediaUuid, sessionUuid=$sessionUuid');
        
        if (sessionUuid == null) {
          debugPrint('🚀 CREATING SESSION: No existing session found for media: $mediaUuid. Attempting to create one...');
          
          developer.log(
            'No existing session found for media: $mediaUuid. Attempting to create one...',
            name: _logName,
          );
          
          // Try to create a session by triggering face detection workflow first
          sessionUuid = await _createSessionForMedia(mediaUuid);
          debugPrint('🔍 SESSION CREATION RESULT: mediaUuid=$mediaUuid, newSessionUuid=$sessionUuid');
          
          if (sessionUuid == null) {
            debugPrint('❌ SESSION CREATION FAILED: Failed to create session for media: $mediaUuid');
            
            developer.log(
              'Failed to create session for media, cannot trigger workflow: $mediaUuid',
              name: _logName,
            );
            return null;
          } else {
            debugPrint('✅ SESSION CREATED: Successfully created session for media: $mediaUuid, sessionUuid: $sessionUuid');
          }
        } else {
          debugPrint('✅ EXISTING SESSION: Found existing session for media: $mediaUuid, sessionUuid: $sessionUuid');
        }

        // Start workflow with default parameters
        return await startPersonObjectsWorkflow(
          sessionUuid,
          workflowMetadata: {
            'triggered_by': 'auto_trigger_fallback',
            'media_uuid': mediaUuid,
            'trigger_timestamp': DateTime.now().toIso8601String(),
          },
        );
      }
      
    } catch (e, stackTrace) {
      debugPrint('🚨 ERROR in autoTriggerPersonObjectsWorkflow: $e');
      debugPrint('🚨 STACK TRACE: $stackTrace');
      
      developer.log(
        'Failed to auto-trigger person objects workflow for $mediaUuid: $e',
        name: _logName,
        error: e,
        stackTrace: stackTrace,
      );
      
      // Return a failed result instead of null so the controller knows what happened
      return PersonObjectsData(
        workflowId: 'error',
        sessionUuid: 'error',
        success: false,
        originalGroups: 0,
        mergedGroups: 0,
        totalPersons: 0,
        groupTracking: [],
        statistics: PersonObjectsStatistics(
          totalGroups: 0,
          originalUniqueFaces: 0,
          mergedGroupsCount: 0,
          totalDetections: 0,
          framesProcessed: 0,
          groupingAlgorithm: 'error',
          tolerancePercent: 0.0,
          trackedFaces: 0,
          newFaces: 0,
          mergeIterations: 0,
        ),
        bestQualityFaces: {},
        classifiedFaces: [],
        processingTimestamp: DateTime.now().toIso8601String(),
        workflowType: 'auto_trigger_failed',
      );
    }
  }
  
  /// Poll workflow status until completion (async/await based)
  Future<String?> _pollWorkflowCompletion(String workflowId) async {
    debugPrint('📊 STARTING POLL: Beginning async workflow status monitoring for $workflowId');
    
    const maxAttempts = 24; // Max 2 minutes of polling
    int attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        final statusResponse = await _apiClient.get('/api/v1/orchestrator/workflows/face-detection/status/$workflowId');
        
        if (statusResponse.statusCode == 200 && statusResponse.data != null) {
          final workflowStatus = statusResponse.data['status'] as String?;
          final processedCount = statusResponse.data['processed_media_count'] as int? ?? 0;
          final totalCount = statusResponse.data['total_media_count'] as int? ?? 1;
          
          debugPrint('📈 POLL ${attempts + 1}/$maxAttempts: $workflowStatus ($processedCount/$totalCount)');
          
          if (workflowStatus == 'completed') {
            debugPrint('✅ WORKFLOW SUCCESS: Async polling detected completion');
            return 'completed';
          } else if (workflowStatus == 'failed') {
            debugPrint('❌ WORKFLOW FAILED: Async polling detected failure');
            return 'failed';
          } else if (workflowStatus == 'processing' || workflowStatus == 'queued') {
            debugPrint('⏳ WORKFLOW ACTIVE: Continue polling... ($workflowStatus)');
          } else {
            debugPrint('❓ UNKNOWN STATUS: $workflowStatus - treating as failure');
            return 'unknown';
          }
        } else {
          debugPrint('⚠️ INVALID RESPONSE: Status check returned ${statusResponse.statusCode}');
        }
        
        // Brief pause before next poll (non-blocking)
        await Future.delayed(Duration(seconds: 5));
        attempts++;
        
      } catch (pollError) {
        debugPrint('⚠️ POLL ERROR: $pollError (attempt ${attempts + 1}/$maxAttempts)');
        attempts++;
        await Future.delayed(Duration(seconds: 5));
      }
    }
    
    debugPrint('⏰ POLL TIMEOUT: Reached maximum attempts without completion');
    return 'timeout';
  }
  
  /// Get session UUID for a media item (internal helper)
  Future<String?> _getSessionUuidForMedia(String mediaUuid) async {
    try {
      developer.log(
        'Looking for session UUID for media: $mediaUuid',
        name: _logName,
      );

      // Use the new dynamic session discovery endpoint
      try {
        final response = await _apiClient.get('/api/v1/person-objects/media/$mediaUuid/session');
        
        if (response.statusCode == 200 && response.data != null) {
          final sessionUuid = response.data['session_uuid'] as String?;
          if (sessionUuid != null && sessionUuid.isNotEmpty) {
            developer.log(
              'Found session UUID via dynamic discovery: $sessionUuid',
              name: _logName,
            );
            return sessionUuid;
          }
        }
        
        if (response.statusCode == 404) {
          developer.log(
            'No session found for media UUID: $mediaUuid',
            name: _logName,
          );
          return null;
        }
        
        developer.log(
          'Session discovery returned unexpected status: ${response.statusCode}',
          name: _logName,
        );
        return null;
        
      } catch (e) {
        developer.log(
          'Dynamic session discovery failed for $mediaUuid: $e',
          name: _logName,
          error: e,
        );
        return null;
      }
      
    } catch (e) {
      developer.log(
        'Failed to get session UUID for media $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }

  /// Batch check person objects availability for multiple media items
  Future<Map<String, bool>> batchCheckPersonObjects(List<String> mediaUuids) async {
    final results = <String, bool>{};
    
    // Process in parallel with limited concurrency
    final futures = mediaUuids.map((uuid) async {
      final hasPersonObjects = await hasPersonObjectsForMedia(uuid);
      return MapEntry(uuid, hasPersonObjects);
    });
    
    final entries = await Future.wait(futures);
    for (final entry in entries) {
      results[entry.key] = entry.value;
    }
    
    developer.log(
      'Batch person objects check completed: ${results.values.where((v) => v).length}/${results.length} have person objects',
      name: _logName,
    );
    
    return results;
  }

  /// Create a Vision Service session for media with existing face data
  Future<String?> _createSessionForMedia(String mediaUuid) async {
    try {
      developer.log(
        'Attempting to create Vision Service session for media: $mediaUuid',
        name: _logName,
      );

      // Use gateway routing instead of direct service discovery
      final visionServiceUrl = 'http://localhost:8080';

      // Temporarily set base URL to Vision service via gateway
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      _apiClient.dio.options.baseUrl = visionServiceUrl;
      
      try {
        // Create a face detection session using the correct Vision Service endpoint
        final response = await _apiClient.post(
          '/sessions/start',
          data: {
            'media_uuid': mediaUuid,
            'session_type': 'streaming',  // Use 'streaming' as it's accepted by Pydantic validation
            'camera_device_uuid': null, // Not camera-based
            // Removed metadata to avoid database schema issue
          },
        );

        if (response.statusCode == 200 && response.data != null) {
          debugPrint('✅ SESSION RESPONSE: ${response.data}');
          
          // Vision Service returns session data in 'session' field
          final sessionData = response.data['session'] as Map<String, dynamic>?;
          final sessionUuid = sessionData?['session_uuid'] as String?;
          
          if (sessionUuid != null && sessionUuid.isNotEmpty) {
            debugPrint('✅ SESSION CREATED: Successfully created session for media $mediaUuid: $sessionUuid');
            developer.log(
              'Successfully created session for media $mediaUuid: $sessionUuid',
              name: _logName,
            );
            return sessionUuid;
          } else {
            debugPrint('❌ INVALID RESPONSE: No session_uuid in response: ${response.data}');
          }
        }
        
        developer.log(
          'Failed to create session - unexpected response: ${response.statusCode}',
          name: _logName,
        );
        return null;
        
      } finally {
        // Restore original base URL
        _apiClient.dio.options.baseUrl = originalBaseUrl;
      }
      
    } catch (e) {
      developer.log(
        'Failed to create session for media $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
  
  /// Trigger PPL Thread workflow for legacy media with face detections but no sessions
  Future<PersonObjectsData?> triggerPPLThreadWorkflow(String mediaUuid) async {
    try {
      developer.log(
        'Triggering PPL Thread workflow for legacy media: $mediaUuid',
        name: _logName,
      );
      
      debugPrint('🎯 PPL THREAD: Triggering legacy media workflow for: $mediaUuid');

      // Use gateway routing instead of direct service discovery
      final visionEndpoint = 'http://localhost:8080';
      
      final originalBaseUrl = _apiClient.dio.options.baseUrl;
      
      try {
        // Set base URL to Vision Service via gateway
        _apiClient.dio.options.baseUrl = visionEndpoint;
        
        debugPrint('🔗 VISION ENDPOINT: Using $visionEndpoint for PPL Thread workflow');
        
        // Call the PPL Thread workflow trigger endpoint
        final response = await _apiClient.post(
          '/api/v1/person-objects/workflow/trigger',
          data: {
            'media_id': mediaUuid,
          },
        );
        
        debugPrint('📊 PPL THREAD RESPONSE: statusCode=${response.statusCode}, data=${response.data}');
        
        if (response.statusCode == 200 && response.data != null) {
          final personObjectsData = PersonObjectsData.fromJson(response.data);
          
          debugPrint('✅ PPL THREAD SUCCESS: ${personObjectsData.totalPersons} persons processed');
          
          developer.log(
            'PPL Thread workflow completed successfully for media: $mediaUuid (${personObjectsData.totalPersons} persons)',
            name: _logName,
          );
          
          return personObjectsData;
        } else {
          debugPrint('❌ PPL THREAD FAILED: Unexpected response: ${response.statusCode}');
          throw Exception('PPL Thread workflow failed: ${response.statusCode}');
        }
        
      } finally {
        // Restore original base URL
        _apiClient.dio.options.baseUrl = originalBaseUrl;
      }
      
    } catch (e) {
      debugPrint('❌ PPL THREAD ERROR: $e');
      developer.log(
        'Failed to trigger PPL Thread workflow for media $mediaUuid: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }
}