import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';

/// Client for MVR People Body APIs (posture/height/colors).
class MvrPeopleBodyApiClient {
  MvrPeopleBodyApiClient(this._api);

  final ApiClient _api;

  static dynamic _normalizeDominantColors(dynamic colors) {
    if (colors == null) return null;
    if (colors is String && colors.isNotEmpty) {
      try {
        return jsonDecode(colors);
      } catch (_) {
        return null;
      }
    }
    return colors;
  }

  static Map<String, dynamic> _normalizeItem(Map<dynamic, dynamic> raw) {
    final item = Map<String, dynamic>.from(raw);
    item['dominant_colors'] = _normalizeDominantColors(item['dominant_colors']);
    return item;
  }

  Future<List<Map<String, dynamic>>> listForMedia(String mediaId) async {
    final response = await _api.get('/api/v1/mvr-people-body/media/$mediaId');
    final data = response.data;
    if (data is Map && data['mvr_people_body'] is List) {
      return (data['mvr_people_body'] as List)
          .whereType<Map>()
          .map((e) => _normalizeItem(e))
          .toList();
    }
    return const [];
  }
}

final mvrPeopleBodyApiClientProvider = Provider<MvrPeopleBodyApiClient>((ref) {
  return MvrPeopleBodyApiClient(ref.watch(apiClientProvider));
});
