import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user_action_model.dart';
import '../core/config.dart';

/// Service for managing user-defined trigger actions
class UserActionService {
  String? _authToken;
  final String baseUrl = Config.mediaServiceUrl;

  void setAuthToken(String token) {
    _authToken = token;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  /// Fetch paginated list of user actions
  Future<UserActionListResponse> fetchUserActions({
    int page = 1,
    int pageSize = 20,
    bool? isActive,
    String? actionType,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
      if (isActive != null) 'is_active': isActive.toString(),
      if (actionType != null) 'action_type': actionType,
    };

    final uri = Uri.parse('$baseUrl/api/v1/user-actions')
        .replace(queryParameters: queryParams);

    final response = await http.get(uri, headers: _headers);

    if (response.statusCode == 200) {
      return UserActionListResponse.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to load user actions: ${response.statusCode} ${response.body}');
    }
  }

  /// Fetch a single user action by UUID
  Future<UserActionModel> fetchUserAction(String uuid) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/user-actions/$uuid'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return UserActionModel.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to load user action: ${response.statusCode} ${response.body}');
    }
  }

  /// Create a new user action
  Future<UserActionModel> createUserAction(
      UserActionCreateRequest request) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/user-actions'),
      headers: _headers,
      body: json.encode(request.toJson()),
    );

    if (response.statusCode == 201) {
      return UserActionModel.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to create user action: ${response.statusCode} ${response.body}');
    }
  }

  /// Update an existing user action
  Future<UserActionModel> updateUserAction(
      String uuid, UserActionCreateRequest request) async {
    final response = await http.put(
      Uri.parse('$baseUrl/api/v1/user-actions/$uuid'),
      headers: _headers,
      body: json.encode(request.toJson()),
    );

    if (response.statusCode == 200) {
      return UserActionModel.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to update user action: ${response.statusCode} ${response.body}');
    }
  }

  /// Toggle active status of a user action
  Future<UserActionModel> toggleUserAction(String uuid) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/api/v1/user-actions/$uuid/toggle'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return UserActionModel.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to toggle user action: ${response.statusCode} ${response.body}');
    }
  }

  /// Delete a user action
  Future<void> deleteUserAction(String uuid) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/api/v1/user-actions/$uuid'),
      headers: _headers,
    );

    if (response.statusCode != 204) {
      throw Exception(
          'Failed to delete user action: ${response.statusCode} ${response.body}');
    }
  }

  /// Get statistics summary
  Future<UserActionStatsResponse> fetchStats() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/user-actions/stats/summary'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return UserActionStatsResponse.fromJson(json.decode(response.body));
    } else {
      throw Exception(
          'Failed to load stats: ${response.statusCode} ${response.body}');
    }
  }
}
