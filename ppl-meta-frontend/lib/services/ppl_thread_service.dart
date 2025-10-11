/// PPL Meta Frontend - PPL Thread Service
/// 
/// Service for retrieving person count data from the PPL Thread workflow system.
/// This service implements the READ-ONLY pattern where:
/// - PPL Thread workflows are triggered automatically by the backend
/// - Flutter only reads the stored person objects data
/// - No workflow triggering from the frontend
///
/// Features:
/// - Authentication using existing ApiClient system
/// - Direct communication with Orchestrator API
/// - Simple person count retrieval
/// - Error handling and fallbacks

import 'dart:developer' as developer;
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/enhanced_person_objects_models.dart';

class PPLThreadService {
  static const String _logName = 'PPLThreadService';
  
  final ApiClient _apiClient;
  late final Dio _dio;
  
  PPLThreadService(this._apiClient) {
    // 🔧 CORS FIX: Use Gateway (port 8080) instead of direct Orchestrator (port 8002)
    // Flutter web can't access port 8002 directly due to CORS restrictions
    // Gateway proxies requests to Orchestrator with proper CORS headers
    _dio = Dio(BaseOptions(
      baseUrl: _apiClient.baseUrl, // Use Gateway base URL
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));
    
    // Add auth interceptor
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // Add auth token if available
          if (_apiClient.authToken != null) {
            options.headers['Authorization'] = 'Bearer ${_apiClient.authToken}';
          }
          handler.next(options);
        },
      ),
    );
  }
  
  /// Get person count for media ID using simplified Enhanced Logic V2 endpoint
  /// 
  /// This method now calls the simplified PPL Thread endpoint that:
  /// 1. Uses Enhanced Logic V2 to get face detection data
  /// 2. Applies grouping logic to calculate person objects
  /// 3. Returns meaningful person count (not just face count)
  Future<int> getPersonCount(String mediaId) async {
    try {
      developer.log(
        '🎯 PPL THREAD: Getting person count for media: $mediaId via Enhanced Logic V2 PPL Thread',
        name: _logName,
      );
      
      // Ensure we have a valid auth token
      if (_apiClient.authToken == null) {
        developer.log(
          'Not authenticated - returning 0 person count',
          name: _logName,
        );
        return 0;
      }
      
      // 🎯 GATEWAY ROUTE: Use Enhanced Logic V2-based PPL Thread via Gateway
      // The gateway proxies this to the Orchestrator PPL Thread endpoint
      final response = await _dio.get('/api/v1/orchestrator/person-objects/$mediaId');
      
      developer.log(
        '🎯 PPL THREAD: Enhanced Logic V2 response: ${response.statusCode} - ${response.data}',
        name: _logName,
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        developer.log(
          'Raw PPL Thread response data: $data',
          name: _logName,
        );
        
        // 🎯 PARSE SIMPLIFIED PPL THREAD RESPONSE
        if (data is Map<String, dynamic>) {
          final success = data['success'] ?? false;
          final totalPersons = data['total_persons'] ?? 0;
          final totalFaces = data['total_faces'] ?? 0;
          final status = data['status'] ?? 'unknown';
          final message = data['message'] ?? 'No message';
          
          developer.log(
            '🎯 PPL THREAD: Enhanced Logic V2 - Success: $success, Persons: $totalPersons, Faces: $totalFaces, Status: $status',
            name: _logName,
          );
          
          if (success) {
            developer.log(
              '🎯 PPL THREAD SUCCESS: $totalPersons persons from $totalFaces faces for media $mediaId',
              name: _logName,
            );
            
            // Return the calculated person count from the backend grouping logic
            return totalPersons is int ? totalPersons : (totalPersons as num).toInt();
          } else {
            developer.log(
              'PPL Thread failed: $message',
              name: _logName,
            );
            return 0;
          }
        }
        
        developer.log(
          'PPL Thread response format unexpected, returning 0',
          name: _logName,
        );
        return 0;
      }
      
      // If no data found, return 0 (PPL Thread may not have processed yet)
      developer.log(
        'No person objects data found for media $mediaId (HTTP ${response.statusCode})',
        name: _logName,
      );
      return 0;
      
    } catch (e) {
      developer.log(
        'PARSING ERROR for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return 0;
    }
  }
  
  /// Check if person objects data exists for media ID using simplified PPL Thread endpoint
  /// 
  /// This is useful for determining whether to show loading states
  /// or "processing" messages in the UI.
  Future<bool> hasPersonObjectsData(String mediaId) async {
    try {
      developer.log(
        'Checking if person objects data exists for media: $mediaId via PPL Thread',
        name: _logName,
      );
      
      // Ensure we have a valid auth token
      if (_apiClient.authToken == null) {
        developer.log(
          'Not authenticated - returning false for data existence check',
          name: _logName,
        );
        return false;
      }
      
      // Use the same simplified PPL Thread endpoint via gateway
      final response = await _dio.get('/api/v1/orchestrator/person-objects/$mediaId');
      
      if (response.statusCode == 200) {
        final data = response.data;
        if (data is Map<String, dynamic>) {
          final success = data['success'] ?? false;
          final totalPersons = data['total_persons'] ?? 0;
          final status = data['status'] ?? 'unknown';
          
          // Data exists if the request was successful and status is completed
          final hasData = success && status == 'completed';
          
          developer.log(
            'PPL Thread data exists for media $mediaId: $hasData (persons: $totalPersons, status: $status)',
            name: _logName,
          );
          
          return hasData;
        }
      }
      
      return false;
      
    } catch (e) {
      developer.log(
        'Error checking PPL Thread data existence for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return false;
    }
  }
  
  /// Get complete person objects response using simplified PPL Thread endpoint
  /// 
  /// Returns the full response data including faces count, status, etc.
  Future<Map<String, dynamic>?> getPersonObjectsData(String mediaId) async {
    try {
      developer.log(
        'Getting complete PPL Thread data for media: $mediaId',
        name: _logName,
      );
      
      // Ensure we have a valid auth token
      if (_apiClient.authToken == null) {
        developer.log(
          'Not authenticated - returning null for complete data',
          name: _logName,
        );
        return null;
      }
      
      // Use the same simplified PPL Thread endpoint via gateway
      final response = await _dio.get('/api/v1/orchestrator/person-objects/$mediaId');
      
      developer.log(
        'Complete PPL Thread response: ${response.statusCode} - ${response.data}',
        name: _logName,
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        developer.log(
          'Successfully retrieved complete PPL Thread data for media $mediaId',
          name: _logName,
        );
        
        return data is Map<String, dynamic> ? data : null;
      }
      
      return null;
      
    } catch (e) {
      developer.log(
        'Error getting complete PPL Thread data for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }

  /// Manually trigger PPL Thread workflow for media (TESTING ONLY)
  /// This should not be needed in production - workflows should run automatically
  Future<bool> triggerWorkflowManually(String mediaId) async {
    try {
      developer.log(
        'Manually triggering PPL Thread workflow for media: $mediaId',
        name: _logName,
      );
      
      // Since automatic workflows aren't implemented yet, return false
      // In a full implementation, this would POST to trigger the workflow
      developer.log(
        'Manual workflow trigger not implemented - workflows should be automatic after face detection',
        name: _logName,
      );
      return false;
      
    } catch (e) {
      developer.log(
        'Error manually triggering workflow: $e',
        name: _logName,
      );
      return false;
    }
  }

  // =============================================================================
  // ENHANCED PERSON OBJECTS WITH DISTANCE-BASED COLOR CODING
  // =============================================================================

  /// Get enhanced person objects data with distance calculations and representative faces
  /// 
  /// This method calls the enhanced PPL Thread endpoint that returns:
  /// - Detailed person groups with UUIDs
  /// - Representative faces with quality scoring
  /// - Distance calculations for each face
  /// - Movement tracking data (for future route visualization)
  Future<EnhancedPPLThreadResponse?> getEnhancedPersonObjects(String mediaId) async {
    try {
      developer.log(
        '🚀 ENHANCED PPL THREAD: Getting detailed person objects for media: $mediaId',
        name: _logName,
      );
      
      // Ensure we have a valid auth token
      if (_apiClient.authToken == null) {
        developer.log(
          'Not authenticated - cannot get enhanced person objects',
          name: _logName,
        );
        return null;
      }
      
      // Call the enhanced PPL Thread endpoint via Gateway
      final response = await _dio.get('/api/v1/orchestrator/person-objects/$mediaId');
      
      developer.log(
        '🚀 ENHANCED PPL THREAD: Response: ${response.statusCode}',
        name: _logName,
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        if (data is Map<String, dynamic>) {
          developer.log(
            '🚀 ENHANCED PPL THREAD: Successfully parsed response data',
            name: _logName,
          );
          
          // Parse the enhanced response
          final enhancedResponse = EnhancedPPLThreadResponse.fromJson(data);
          
          developer.log(
            '🚀 ENHANCED PPL THREAD: Found ${enhancedResponse.totalPersons} persons with ${enhancedResponse.personGroups.length} groups',
            name: _logName,
          );
          
          // Log distance information for debugging
          for (final group in enhancedResponse.personGroups) {
            developer.log(
              '🎯 Person ${group.personId}: ${group.faceCount} faces, closest distance: ${group.closestDistance.toStringAsFixed(1)}m',
              name: _logName,
            );
          }
          
          return enhancedResponse;
        }
      }
      
      developer.log(
        'No enhanced person objects data found for media $mediaId (HTTP ${response.statusCode})',
        name: _logName,
      );
      return null;
      
    } catch (e) {
      developer.log(
        'Error getting enhanced person objects for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return null;
    }
  }

  /// Get enhanced person objects with simpler error handling for UI widgets
  Future<List<EnhancedPersonObjectGroup>> getPersonObjectGroups(String mediaId) async {
    try {
      final response = await getEnhancedPersonObjects(mediaId);
      return response?.personGroups ?? [];
    } catch (e) {
      developer.log(
        'Error getting person object groups for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return [];
    }
  }

  /// Check if enhanced person objects data is available for media
  Future<bool> hasEnhancedPersonObjectsData(String mediaId) async {
    try {
      final response = await getEnhancedPersonObjects(mediaId);
      return response != null && response.success;
    } catch (e) {
      developer.log(
        'Error checking enhanced person objects availability for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return false;
    }
  }
}