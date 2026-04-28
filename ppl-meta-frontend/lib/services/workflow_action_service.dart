// Workflow Action Service for PPL Meta Platform
// Handles API communication with orchestrator workflows registry

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/workflow_action_model.dart';
import '../core/config/app_config.dart';

class WorkflowActionService {
  /// Optional override — if null, falls back to AppConfig.instance.apiBaseUrl
  /// (resolved lazily so the mobile host override is respected).
  final String? _baseUrlOverride;
  String? _authToken;

  WorkflowActionService({String? baseUrl}) : _baseUrlOverride = baseUrl;

  String get baseUrl => _baseUrlOverride ?? AppConfig.instance.apiBaseUrl;

  /// Set authentication token for API requests
  void setAuthToken(String token) {
    _authToken = token;
  }

  /// Get authorization headers
  Map<String, String> get _headers {
    final headers = {
      'Content-Type': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  /// Get all workflows from registry
  Future<List<WorkflowAction>> getWorkflows({
    String? category,
    bool? isActive,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (category != null) queryParams['category'] = category;
      if (isActive != null) queryParams['is_active'] = isActive.toString();

      final uri = Uri.parse('$baseUrl/api/v1/workflows/registry')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      print('Fetching workflows from: $uri');

      final response = await http.get(uri, headers: _headers);

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList
            .map((json) => WorkflowAction.fromJson(json as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception(
            'Failed to load workflows: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('Error fetching workflows: $e');
      rethrow;
    }
  }

  /// Get a specific workflow by ID
  Future<WorkflowAction> getWorkflow(String workflowId) async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/workflows/registry/$workflowId');

      print('Fetching workflow: $uri');

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return WorkflowAction.fromJson(
            json.decode(response.body) as Map<String, dynamic>);
      } else if (response.statusCode == 404) {
        throw Exception('Workflow not found: $workflowId');
      } else {
        throw Exception(
            'Failed to load workflow: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('Error fetching workflow: $e');
      rethrow;
    }
  }

  /// Get workflow count and category statistics
  Future<Map<String, dynamic>> getWorkflowCount() async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/workflows/registry/count');

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw Exception(
            'Failed to load workflow count: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('Error fetching workflow count: $e');
      rethrow;
    }
  }

  /// Get list of workflow categories
  Future<List<Map<String, String>>> getCategories() async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/workflows/registry/categories');

      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final categories = data['categories'] as List<dynamic>;
        return categories
            .map((cat) => Map<String, String>.from(cat as Map))
            .toList();
      } else {
        throw Exception(
            'Failed to load categories: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('Error fetching categories: $e');
      rethrow;
    }
  }

  /// Get workflows filtered by category
  Future<List<WorkflowAction>> getWorkflowsByCategory(String category) async {
    return getWorkflows(category: category);
  }

  /// Get only active workflows
  Future<List<WorkflowAction>> getActiveWorkflows() async {
    return getWorkflows(isActive: true);
  }
}
