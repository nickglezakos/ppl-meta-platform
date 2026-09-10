import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

class ModelsCatalogClient {
  ModelsCatalogClient(this._api);

  final ApiClient _api;

  Future<List<dynamic>> listModels() async {
    final response = await _api.get('/api/v1/mv-models/');
    final data = response.data as Map<String, dynamic>;
    return List<dynamic>.from(data['models'] as List? ?? const []);
  }

  Future<List<dynamic>> listAssignments() async {
    final response = await _api.get('/api/v1/mv-models/assignments');
    final data = response.data as Map<String, dynamic>;
    return List<dynamic>.from(data['assignments'] as List? ?? const []);
  }

  Future<List<dynamic>> listRecipes({String? capability}) async {
    final response = await _api.get(
      '/api/v1/mv-models/recipes',
      queryParameters: {
        if (capability != null) 'capability': capability,
      },
    );
    final data = response.data as Map<String, dynamic>;
    return List<dynamic>.from(data['recipes'] as List? ?? const []);
  }

  Future<List<dynamic>> listGoldenSets() async {
    final response = await _api.get('/api/v1/mv-models/golden-sets');
    final data = response.data as Map<String, dynamic>;
    return List<dynamic>.from(data['golden_sets'] as List? ?? const []);
  }

  Future<Map<String, dynamic>> activate({
    required String modelId,
    required String version,
    required String path,
    String capability = 'face_detection',
    String scopeType = 'platform',
    String scopeId = '',
    bool shadow = false,
  }) async {
    final response = await _api.post(
      '/api/v1/mv-models/$modelId/versions/$version/activate',
      data: {
        'path': path,
        'capability': capability,
        'scope_type': scopeType,
        'scope_id': scopeId,
        'shadow': shadow,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> activateRecipe({
    required String recipeId,
    required String path,
    String capability = 'face_detection',
    String scopeType = 'platform',
    String scopeId = '',
    bool shadow = false,
  }) async {
    final response = await _api.post(
      '/api/v1/mv-models/recipes/$recipeId/activate',
      data: {
        'path': path,
        'capability': capability,
        'scope_type': scopeType,
        'scope_id': scopeId,
        'shadow': shadow,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> createModel({
    required String modelId,
    required String displayName,
    String capability = 'face_detection',
  }) async {
    final response = await _api.post(
      '/api/v1/mv-models/',
      data: {
        'model_id': modelId,
        'display_name': displayName,
        'capability': capability,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> uploadVersion({
    required String modelId,
    required String version,
    required String runtime,
    required List<int> bytes,
    required String filename,
    String latencyClass = 'instant',
    String compatiblePaths = 'instant,bulk',
  }) async {
    final form = FormData.fromMap({
      'version': version,
      'runtime': runtime,
      'latency_class': latencyClass,
      'compatible_paths': compatiblePaths,
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });
    final response = await _api.post(
      '/api/v1/mv-models/$modelId/versions',
      data: form,
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> validateVersion({
    required String modelId,
    required String version,
  }) async {
    final response = await _api.post(
      '/api/v1/mv-models/$modelId/versions/$version/validate',
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<dynamic>> listValidationRuns({
    required String modelId,
    required String version,
  }) async {
    final response = await _api.get(
      '/api/v1/mv-models/$modelId/versions/$version/validation-runs',
    );
    final data = response.data as Map<String, dynamic>;
    return List<dynamic>.from(data['runs'] as List? ?? const []);
  }

  Future<Map<String, dynamic>> createRecipe({
    required String recipeId,
    required String displayName,
    required String kind,
    required List<Map<String, String>> steps,
    String capability = 'face_detection',
  }) async {
    final response = await _api.post(
      '/api/v1/mv-models/recipes',
      data: {
        'recipe_id': recipeId,
        'display_name': displayName,
        'capability': capability,
        'kind': kind,
        'steps': steps,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }
}

final modelsCatalogClientProvider = Provider<ModelsCatalogClient>((ref) {
  return ModelsCatalogClient(ref.watch(apiClientProvider));
});
