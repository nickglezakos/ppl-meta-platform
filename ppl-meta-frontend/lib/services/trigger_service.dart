import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/trigger_model.dart';
import '../models/signage_models.dart';
import '../core/config.dart';

class TriggerService {
  final String baseUrl;
  String? _authToken;

  TriggerService({String? baseUrl})
      : baseUrl = baseUrl ?? Config.gatewayServiceUrl;

  String get _triggersEndpoint => '$baseUrl/api/v1/triggers';
  String get _signageEndpoint => '$baseUrl/api/v1/signage';

  /// Set authentication token
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Get headers with auth token if available
  Map<String, String> get _headers {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  /// Fetch all triggers with optional pagination and filtering
  Future<TriggerListResponse> fetchTriggers({
    int page = 1,
    int pageSize = 50,
    bool? isActive,
    String? action,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    if (isActive != null) {
      queryParams['is_active'] = isActive.toString();
    }
    if (action != null) {
      queryParams['action'] = action;
    }

    final uri = Uri.parse(_triggersEndpoint).replace(queryParameters: queryParams);

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return TriggerListResponse.fromJson(jsonData);
      } else {
        throw Exception('Failed to load triggers: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching triggers: $e');
    }
  }

  /// Fetch a single trigger by UUID
  Future<TriggerModel> fetchTrigger(String uuid) async {
    final uri = Uri.parse('$_triggersEndpoint/$uuid');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return TriggerModel.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('Trigger not found');
      } else {
        throw Exception('Failed to load trigger: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching trigger: $e');
    }
  }

  /// Create a new trigger
  Future<TriggerModel> createTrigger(TriggerCreateRequest request) async {
    final uri = Uri.parse(_triggersEndpoint);

    try {
      final response = await http.post(
        uri,
        headers: _headers,
        body: json.encode(request.toJson()),
      );

      if (response.statusCode == 201) {
        final jsonData = json.decode(response.body);
        return TriggerModel.fromJson(jsonData);
      } else {
        final errorBody = json.decode(response.body);
        throw Exception('Failed to create trigger: ${errorBody['detail'] ?? response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error creating trigger: $e');
    }
  }

  /// Update an existing trigger
  Future<TriggerModel> updateTrigger(
    String uuid,
    TriggerCreateRequest request,
  ) async {
    final uri = Uri.parse('$_triggersEndpoint/$uuid');

    try {
      final response = await http.put(
        uri,
        headers: _headers,
        body: json.encode(request.toJson()),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return TriggerModel.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('Trigger not found');
      } else {
        final errorBody = json.decode(response.body);
        throw Exception('Failed to update trigger: ${errorBody['detail'] ?? response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error updating trigger: $e');
    }
  }

  /// Toggle trigger active status
  Future<TriggerModel> toggleTrigger(String uuid) async {
    final uri = Uri.parse('$_triggersEndpoint/$uuid/toggle');

    try {
      final response = await http.patch(uri, headers: _headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return TriggerModel.fromJson(jsonData);
      } else if (response.statusCode == 404) {
        throw Exception('Trigger not found');
      } else {
        throw Exception('Failed to toggle trigger: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error toggling trigger: $e');
    }
  }

  /// Delete a trigger
  Future<void> deleteTrigger(String uuid) async {
    final uri = Uri.parse('$_triggersEndpoint/$uuid');

    try {
      final response = await http.delete(uri, headers: _headers);

      if (response.statusCode == 204) {
        return;
      } else if (response.statusCode == 404) {
        throw Exception('Trigger not found');
      } else {
        throw Exception('Failed to delete trigger: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error deleting trigger: $e');
    }
  }

  /// Get trigger statistics
  Future<Map<String, dynamic>> fetchStats() async {
    final uri = Uri.parse('$_triggersEndpoint/stats/summary');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load stats: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching stats: $e');
    }
  }
  
  /// Fetch signage devices for demographic triggers
  Future<List<DatabaseSignageDevice>> fetchSignageDevices() async {
    final uri = Uri.parse('$_signageEndpoint/devices');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final Map<String, dynamic> jsonData = json.decode(response.body);
        // Handle paginated response with 'results' array
        final List<dynamic> jsonList = jsonData['results'] as List<dynamic>;
        return jsonList.map((json) => DatabaseSignageDevice.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load signage devices: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching signage devices: $e');
    }
  }
  
  /// Fetch signage video lists (playlists) for demographic triggers
  Future<List<VideoList>> fetchSignagePlaylists() async {
    final uri = Uri.parse('$_signageEndpoint/video-lists');

    try {
      final response = await http.get(uri, headers: _headers);

      if (response.statusCode == 200) {
        final Map<String, dynamic> jsonData = json.decode(response.body);
        // Handle paginated response with 'results' array
        final List<dynamic> jsonList = jsonData['results'] as List<dynamic>;
        return jsonList.map((json) => VideoList.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load video lists: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching video lists: $e');
    }
  }
}
