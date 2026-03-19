/// Individual Groups API Client
/// Handles all API calls for individual groups feature
library;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/api_response.dart';
import '../models/individual_group_models.dart';

/// API client for Individual Groups operations
class IndividualGroupsApiClient {
  late final ApiClient _apiClient;

  IndividualGroupsApiClient([ApiClient? apiClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  /// Helper to parse error detail from response (handles both String and List)
  String _parseErrorDetail(dynamic detail, String fallback) {
    if (detail is List) {
      return detail.map((e) => e.toString()).join(', ');
    } else if (detail is String) {
      return detail;
    }
    return fallback;
  }

  /// List all groups with optional filtering
  Future<ApiResponse<ListGroupsResponse>> listGroups({
    String? userId,
    GroupVisibility? visibility,
    List<String>? tags,
    String? search,
    int skip = 0,
    int limit = 50,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
      };

      if (userId != null) queryParams['user_id'] = userId;
      if (visibility != null) {
        queryParams['visibility'] = visibility.toString().split('.').last;
      }
      if (tags != null && tags.isNotEmpty) {
        queryParams['tags'] = tags.join(',');
      }
      if (search != null && search.isNotEmpty) {
        queryParams['search'] = search;
      }

      final response = await _apiClient.get(
        '/api/v1/individual-groups',
        queryParameters: queryParams,
      );

      return ApiResponse<ListGroupsResponse>.success(
        ListGroupsResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ List groups failed: ${e.message}');
      return ApiResponse<ListGroupsResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to list groups',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ List groups error: $e');
      return ApiResponse<ListGroupsResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Create a new group
  Future<ApiResponse<GetGroupResponse>> createGroup(
    CreateGroupRequest request,
  ) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/individual-groups',
        data: request.toJson(),
      );

      return ApiResponse<GetGroupResponse>.success(
        GetGroupResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Create group failed: ${e.message}');
      return ApiResponse<GetGroupResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to create group',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Create group error: $e');
      return ApiResponse<GetGroupResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Get a specific group by ID
  Future<ApiResponse<GetGroupResponse>> getGroup(String groupId) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/individual-groups/$groupId',
      );

      return ApiResponse<GetGroupResponse>.success(
        GetGroupResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Get group failed: ${e.message}');
      return ApiResponse<GetGroupResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to get group',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Get group error: $e');
      return ApiResponse<GetGroupResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Update a group
  Future<ApiResponse<IndividualGroup>> updateGroup(
    String groupId,
    UpdateGroupRequest request,
  ) async {
    try {
      final response = await _apiClient.put(
        '/api/v1/individual-groups/$groupId',
        data: request.toJson(),
      );

      return ApiResponse<IndividualGroup>.success(
        IndividualGroup.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Update group failed: ${e.message}');
      return ApiResponse<IndividualGroup>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to update group',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Update group error: $e');
      return ApiResponse<IndividualGroup>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Delete a group
  Future<ApiResponse<void>> deleteGroup(
    String groupId, {
    bool removeMembers = false,
  }) async {
    try {
      await _apiClient.delete(
        '/api/v1/individual-groups/$groupId',
        queryParameters: {'remove_members': removeMembers},
      );

      return ApiResponse<void>.success(null);
    } on DioException catch (e) {
      debugPrint('❌ Delete group failed: ${e.message}');
      return ApiResponse<void>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to delete group',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Delete group error: $e');
      return ApiResponse<void>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Add members to a group
  Future<ApiResponse<AddMembersResponse>> addMembers(
    String groupId,
    AddMembersRequest request,
  ) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/individual-groups/$groupId/members',
        data: request.toJson(),
      );

      return ApiResponse<AddMembersResponse>.success(
        AddMembersResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Add members failed: ${e.message}');
      return ApiResponse<AddMembersResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to add members',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Add members error: $e');
      return ApiResponse<AddMembersResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Remove members from a group
  Future<ApiResponse<RemoveMembersResponse>> removeMembers(
    String groupId,
    RemoveMembersRequest request,
  ) async {
    try {
      final response = await _apiClient.delete(
        '/api/v1/individual-groups/$groupId/members',
        data: request.toJson(),
      );

      return ApiResponse<RemoveMembersResponse>.success(
        RemoveMembersResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Remove members failed: ${e.message}');
      return ApiResponse<RemoveMembersResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to remove members',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Remove members error: $e');
      return ApiResponse<RemoveMembersResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Get group members with pagination
  Future<ApiResponse<ListMembersResponse>> getGroupMembers(
    String groupId, {
    int skip = 0,
    int limit = 50,
    String sort = 'added_date',
  }) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/individual-groups/$groupId/members',
        queryParameters: {
          'skip': skip,
          'limit': limit,
          'sort': sort,
        },
      );

      return ApiResponse<ListMembersResponse>.success(
        ListMembersResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Get group members failed: ${e.message}');
      return ApiResponse<ListMembersResponse>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to get members',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Get group members error: $e');
      return ApiResponse<ListMembersResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Get groups that an individual belongs to
  Future<ApiResponse<List<IndividualGroup>>> getIndividualGroups(
    String individualId,
  ) async {
    try {
      final response = await _apiClient.get(
        '/api/v1/individual-groups/individuals/$individualId/groups',
      );

      final groups = (response.data['groups'] as List)
          .map((json) => IndividualGroup.fromJson(json))
          .toList();

      return ApiResponse<List<IndividualGroup>>.success(groups);
    } on DioException catch (e) {
      debugPrint('❌ Get individual groups failed: ${e.message}');
      return ApiResponse<List<IndividualGroup>>.error(
        _parseErrorDetail(
          e.response?.data?['detail'],
          e.message ?? 'Failed to get groups',
        ),
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Get individual groups error: $e');
      return ApiResponse<List<IndividualGroup>>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Get thumbnail URL for an individual
  String getThumbnailUrl(String individualId, {String size = 'medium'}) {
    final baseUrl = _apiClient.baseUrl;
    return '$baseUrl/api/v1/individuals/$individualId/thumbnail?size=$size';
  }

  /// Generate thumbnail for an individual
  Future<ApiResponse<Map<String, dynamic>>> generateThumbnail(
    String individualId,
  ) async {
    try {
      final response = await _apiClient.post(
        '/api/v1/individuals/$individualId/thumbnail/generate',
      );

      return ApiResponse<Map<String, dynamic>>.success(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Generate thumbnail failed: ${e.message}');
      return ApiResponse<Map<String, dynamic>>.error(
        e.response?.data?['detail'] ?? e.message ?? 'Failed to generate thumbnail',
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Generate thumbnail error: $e');
      return ApiResponse<Map<String, dynamic>>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Search for group members in camera footage
  Future<ApiResponse<Map<String, dynamic>>> searchGroupInCamera({
    required String groupId,
    String? cameraId,  // Single camera (deprecated, for backward compatibility)
    List<String>? cameraIds,  // Multiple cameras
    required String startTime,
    required String endTime,
    double confidenceThreshold = 0.7,
  }) async {
    try {
      // Support both single and multiple cameras
      final cameras = cameraIds ?? (cameraId != null ? [cameraId] : null);
      if (cameras == null || cameras.isEmpty) {
        throw ArgumentError('Either cameraId or cameraIds must be provided');
      }
      
      debugPrint('🔍 Searching group $groupId in ${cameras.length} camera(s): $cameras');
      
      final requestData = <String, dynamic>{
        'start_time': startTime,
        'end_time': endTime,
        'confidence_threshold': confidenceThreshold,
      };
      
      // Use camera_ids for multiple cameras, camera_id for single camera (backward compat)
      if (cameras.length > 1) {
        requestData['camera_ids'] = cameras;
      } else {
        requestData['camera_id'] = cameras.first;
      }
      
      final response = await _apiClient.post(
        '/api/v1/individual-groups/$groupId/camera-search',
        data: requestData,
      );

      debugPrint('✅ Camera search response: ${response.data}');
      return ApiResponse<Map<String, dynamic>>.success(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      final errorDetail = _parseErrorDetail(e.response, 'Camera search failed');
      debugPrint('❌ Camera search error: $errorDetail');
      return ApiResponse<Map<String, dynamic>>.error(
        errorDetail,
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Camera search error: $e');
      return ApiResponse<Map<String, dynamic>>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Check for duplicate members in a group
  Future<ApiResponse<CheckDuplicatesResponse>> checkDuplicates(
    String groupId,
    CheckDuplicatesRequest request,
  ) async {
    try {
      debugPrint('🔍 Checking duplicates in group $groupId for candidate ${request.candidateMvrUuid}');
      
      final response = await _apiClient.post(
        '/api/v1/individual-groups/$groupId/check-duplicates',
        data: request.toJson(),
      );

      debugPrint('✅ Check duplicates response: ${response.data}');
      return ApiResponse<CheckDuplicatesResponse>.success(
        CheckDuplicatesResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      final errorDetail = _parseErrorDetail(e.response, 'Check duplicates failed');
      debugPrint('❌ Check duplicates error: $errorDetail');
      return ApiResponse<CheckDuplicatesResponse>.error(
        errorDetail,
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Check duplicates error: $e');
      return ApiResponse<CheckDuplicatesResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Merge members in a group (creates super-individual)
  Future<ApiResponse<MergeMembersResponse>> mergeMembers(
    String groupId,
    MergeMembersRequest request,
  ) async {
    try {
      debugPrint('🔄 Merging members in group $groupId: ${request.sourceMvrUuid} → ${request.targetMvrUuid}');
      
      final response = await _apiClient.post(
        '/api/v1/individual-groups/$groupId/merge-members',
        data: request.toJson(),
      );

      debugPrint('✅ Merge members response: ${response.data}');
      return ApiResponse<MergeMembersResponse>.success(
        MergeMembersResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      final errorDetail = _parseErrorDetail(e.response, 'Merge members failed');
      debugPrint('❌ Merge members error: $errorDetail');
      return ApiResponse<MergeMembersResponse>.error(
        errorDetail,
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Merge members error: $e');
      return ApiResponse<MergeMembersResponse>.error(
        'Unexpected error: $e',
      );
    }
  }
}
