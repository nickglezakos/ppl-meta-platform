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
  
  /// Get person count for media ID (READ-ONLY - no workflow triggering)
  /// 
  /// This method retrieves stored person objects data from the Orchestrator Service
  /// which implements the proper architectural pattern:
  /// 1. Lookup session UUID from media ID
  /// 2. Retrieve person objects data from Vision Service
  /// 3. Transform and return total_persons count
  Future<int> getPersonCount(String mediaId) async {
    try {
      developer.log(
        'Getting person count for media: $mediaId',
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
      
      // � ENHANCED LOGIC V2: Use new session-based endpoint via Gateway
      // GET face detection data via Gateway -> Orchestrator Enhanced Logic V2
      final response = await _dio.get('/api/v1/media/$mediaId/faces/enhanced-v2');
      
      developer.log(
        'Person objects response: ${response.statusCode} - ${response.data}',
        name: _logName,
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        developer.log(
          'Raw person objects response data: $data',
          name: _logName,
        );
        
        developer.log(
          'PARSING DEBUG - data type: ${data.runtimeType}, keys: ${data is Map ? data.keys.toList() : "not a map"}',
          name: _logName,
        );
        
        // 🚀 ENHANCED LOGIC V2 PARSING: Handle session-based response format
        int totalPersons = 0;
        int totalFaces = 0;
        
        if (data is Map<String, dynamic>) {
          developer.log(
            'Enhanced Logic V2 response - keys: ${data.keys.toList()}',
            name: _logName,
          );
          
          // Parse total_faces from Enhanced Logic V2 response
          if (data.containsKey('total_faces')) {
            final totalFacesValue = data['total_faces'];
            developer.log(
              'PARSING DEBUG - total_faces value: $totalFacesValue, type: ${totalFacesValue.runtimeType}',
              name: _logName,
            );
            
            if (totalFacesValue is int) {
              totalFaces = totalFacesValue;
            } else if (totalFacesValue is num) {
              totalFaces = totalFacesValue.toInt();
            } else if (totalFacesValue is String) {
              totalFaces = int.tryParse(totalFacesValue) ?? 0;
            }
          }
          
          // For person count, use faces count as approximation or check if faces array exists
          if (data.containsKey('faces') && data['faces'] is List) {
            // Use faces array length directly - no estimation
            final faces = data['faces'] as List;
            totalPersons = faces.length; // NO ESTIMATION: Use face count directly
          } else {
            // Fallback: use total_faces value directly
            totalPersons = totalFaces; // NO ESTIMATION: Backend should handle person grouping
          }
          
          // Log Enhanced Logic V2 specific fields
          final sessionUuid = data['session_uuid'] ?? 'N/A';
          final source = data['source'] ?? 'unknown';
          final message = data['message'] ?? 'No message';
          
          developer.log(
            'Enhanced Logic V2 - Session: $sessionUuid, Source: $source, Message: $message',
            name: _logName,
          );
        }
        
        developer.log(
          'ENHANCED LOGIC V2 RESULT: Successfully parsed faces: $totalFaces, estimated persons: $totalPersons for media $mediaId',
          name: _logName,
        );
        
        return totalPersons;
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
  
  /// Check if person objects data exists for this media
  /// 
  /// This is useful for determining whether to show loading states
  /// or "processing" messages in the UI.
  Future<bool> hasPersonObjectsData(String mediaId) async {
    try {
      developer.log(
        'Checking if person objects data exists for media: $mediaId',
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
      
      // 🚀 ENHANCED LOGIC V2: Call Orchestrator service directly
      final orchestratorUrl = 'http://localhost:8002/api/v1/media/$mediaId/faces/enhanced-v2';
      final response = await Dio().get(
        orchestratorUrl,
        options: Options(
          headers: {
            'Authorization': 'Bearer ${_apiClient.authToken}',
            'Content-Type': 'application/json',
          },
        ),
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        final hasData = data['success'] == true && 
                       data['status'] == 'completed' && 
                       data['total_persons'] != null;
        
        developer.log(
          'Person objects data exists for media $mediaId: $hasData',
          name: _logName,
        );
        
        return hasData;
      }
      
      return false;
      
    } catch (e) {
      developer.log(
        'Error checking person objects data existence for media $mediaId: $e',
        name: _logName,
        error: e,
      );
      return false;
    }
  }
  
  /// Get complete person objects response for advanced use cases
  /// 
  /// Returns the full response data including faces count, status, etc.
  Future<Map<String, dynamic>?> getPersonObjectsData(String mediaId) async {
    try {
      developer.log(
        'Getting complete person objects data for media: $mediaId',
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
      
      // 🚀 ENHANCED LOGIC V2: Call Orchestrator service directly
      final orchestratorUrl = 'http://localhost:8002/api/v1/media/$mediaId/faces/enhanced-v2';
      final response = await Dio().get(
        orchestratorUrl,
        options: Options(
          headers: {
            'Authorization': 'Bearer ${_apiClient.authToken}',
            'Content-Type': 'application/json',
          },
        ),
      );
      
      developer.log(
        'Complete person objects response: ${response.statusCode} - ${response.data}',
        name: _logName,
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        developer.log(
          'Successfully retrieved complete person objects data for media $mediaId',
          name: _logName,
        );
        
        return data;
      }
      
      return null;
      
    } catch (e) {
      developer.log(
        'Error getting complete person objects data for media $mediaId: $e',
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
}