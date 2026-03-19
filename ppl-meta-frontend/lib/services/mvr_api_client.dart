/// MVR People API Client
/// Handles all API calls for MVR (Multi-Video Recognition) people operations
library;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/api_response.dart';

/// Response from updating an MVR person's name
class UpdateNameResponse {
  final bool success;
  final String? updatedAt;
  final List<String> propagatedTo;
  final List<String> affectedSuperIndividuals;

  UpdateNameResponse({
    required this.success,
    this.updatedAt,
    required this.propagatedTo,
    required this.affectedSuperIndividuals,
  });

  factory UpdateNameResponse.fromJson(Map<String, dynamic> json) {
    return UpdateNameResponse(
      success: json['success'] as bool? ?? false,
      updatedAt: json['updated_at'] as String?,
      propagatedTo: (json['propagated_to'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      affectedSuperIndividuals:
          (json['affected_super_individuals'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'success': success,
      'updated_at': updatedAt,
      'propagated_to': propagatedTo,
      'affected_super_individuals': affectedSuperIndividuals,
    };
  }
}

/// Response from updating an MVR person's gender
class UpdateGenderResponse {
  final bool success;
  final String? updatedAt;
  final List<String> propagatedTo;
  final List<String> affectedSuperIndividuals;

  UpdateGenderResponse({
    required this.success,
    this.updatedAt,
    required this.propagatedTo,
    required this.affectedSuperIndividuals,
  });

  factory UpdateGenderResponse.fromJson(Map<String, dynamic> json) {
    return UpdateGenderResponse(
      success: json['success'] as bool? ?? false,
      updatedAt: json['updated_at'] as String?,
      propagatedTo: (json['propagated_to'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      affectedSuperIndividuals:
          (json['affected_super_individuals'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'success': success,
      'updated_at': updatedAt,
      'propagated_to': propagatedTo,
      'affected_super_individuals': affectedSuperIndividuals,
    };
  }
}


/// API client for MVR People operations
class MVRApiClient {
  late final ApiClient _apiClient;

  MVRApiClient([ApiClient? apiClient]) {
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

  /// Update an MVR person's name
  /// 
  /// [mvrPersonUuid] - UUID of the MVR person to update
  /// [name] - New name for the person (max 255 characters, cannot be whitespace only)
  /// [propagate] - Whether to propagate the name to merged constituents (default: true)
  /// 
  /// Returns an [ApiResponse] containing the update result with propagation information.
  Future<ApiResponse<UpdateNameResponse>> updateMVRPersonName(
    String mvrPersonUuid,
    String name, {
    bool propagate = true,
  }) async {
    try {
      final requestData = {
        'name': name,
        'propagate': propagate,
      };

      final response = await _apiClient.patch(
        '/api/v1/mvr-people/$mvrPersonUuid/name',
        data: requestData,
      );

      return ApiResponse<UpdateNameResponse>.success(
        UpdateNameResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Update MVR person name failed: ${e.message}');
      
      // Extract error detail from response
      String errorMessage = 'Failed to update name';
      if (e.response?.data != null) {
        if (e.response!.data is Map) {
          errorMessage = _parseErrorDetail(
            e.response!.data['detail'],
            e.message ?? errorMessage,
          );
        } else if (e.response!.data is String) {
          errorMessage = e.response!.data;
        }
      } else if (e.message != null) {
        errorMessage = e.message!;
      }

      return ApiResponse<UpdateNameResponse>.error(
        errorMessage,
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Update MVR person name error: $e');
      return ApiResponse<UpdateNameResponse>.error(
        'Unexpected error: $e',
      );
    }
  }

  /// Update the gender of an MVR person with optional propagation to merged individuals.
  /// 
  /// [mvrPersonUuid] - UUID of the MVR person to update
  /// [gender] - Gender value: 'male', 'female', or empty string to clear
  /// [propagate] - Whether to propagate the gender to merged constituents (default: true)
  /// 
  /// Returns an [ApiResponse] containing the update result with propagation information.
  Future<ApiResponse<UpdateGenderResponse>> updateMVRPersonGender(
    String mvrPersonUuid,
    String gender, {
    bool propagate = true,
  }) async {
    try {
      final requestData = {
        'gender': gender,
        'propagate': propagate,
      };

      final response = await _apiClient.patch(
        '/api/v1/mvr-people/$mvrPersonUuid/gender',
        data: requestData,
      );

      return ApiResponse<UpdateGenderResponse>.success(
        UpdateGenderResponse.fromJson(response.data),
      );
    } on DioException catch (e) {
      debugPrint('❌ Update MVR person gender failed: ${e.message}');
      
      // Extract error detail from response
      String errorMessage = 'Failed to update gender';
      if (e.response?.data != null) {
        if (e.response!.data is Map) {
          errorMessage = _parseErrorDetail(
            e.response!.data['detail'],
            e.message ?? errorMessage,
          );
        } else if (e.response!.data is String) {
          errorMessage = e.response!.data;
        }
      } else if (e.message != null) {
        errorMessage = e.message!;
      }

      return ApiResponse<UpdateGenderResponse>.error(
        errorMessage,
        statusCode: e.response?.statusCode,
      );
    } catch (e) {
      debugPrint('❌ Update MVR person gender error: $e');
      return ApiResponse<UpdateGenderResponse>.error(
        'Unexpected error: $e',
      );
    }
  }
}
