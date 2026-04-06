// MVR Image Service
// Service for fetching best face and frame images for MVRpeople

import 'dart:developer' as developer;
import '../core/api/api_client.dart';
import '../models/mvr_best_image.dart';

class MVRImageService {
  final ApiClient _apiClient;

  MVRImageService(this._apiClient);

  /// Get best quality face and frame images for MVRpeople
  ///
  /// [mvrUuid] - MVRpeople UUID or Super-individual UUID
  /// [includeMerged] - Include merged children if super-individual
  /// [useCache] - Use cached result if available
  Future<BestImageResponse?> getBestImages(
    String mvrUuid, {
    bool includeMerged = false,
    bool useCache = true,
  }) async {
    try {
      developer.log(
        '🖼️ Fetching best images for MVR $mvrUuid (includeMerged=$includeMerged)',
        name: 'MVRImageService',
      );

      final response = await _apiClient.get(
        '/api/v1/mvr-people/$mvrUuid/best-image',
        queryParameters: {
          'include_merged': includeMerged,
          'use_cache': useCache,
        },
      );

      if (response.statusCode == 200 && response.data != null) {
        try {
          final bestImage = BestImageResponse.fromJson(
            response.data as Map<String, dynamic>,
          );

          developer.log(
            '✅ Got best images: quality=${bestImage.bestFace?.qualityScore.toStringAsFixed(3)}, '
            'time=${bestImage.metadata.processingTimeMs}ms',
            name: 'MVRImageService',
          );

          return bestImage;
        } catch (parseError, parseStack) {
          developer.log(
            '❌ Error parsing best image response: $parseError',
            name: 'MVRImageService',
            error: parseError,
            stackTrace: parseStack,
          );
          return null;
        }
      } else if (response.statusCode == 404) {
        developer.log(
          '⚠️ No images found for MVR $mvrUuid',
          name: 'MVRImageService',
        );
        return null;
      } else {
        developer.log(
          '❌ Failed to get best images: ${response.statusCode}',
          name: 'MVRImageService',
        );
        return null;
      }
    } catch (e, stackTrace) {
      developer.log(
        '❌ Error fetching best images for $mvrUuid: $e',
        name: 'MVRImageService',
        error: e,
        stackTrace: stackTrace,
      );
      return null;
    }
  }

  /// Batch fetch best images for multiple MVR UUIDs
  ///
  /// Returns a map of MVR UUID -> BestImageResponse
  Future<Map<String, BestImageResponse?>> getBestImagesForMultiple(
    List<String> mvrUuids, {
    bool includeMerged = false,
    bool useCache = true,
  }) async {
    developer.log(
      '🖼️ Batch fetching best images for ${mvrUuids.length} MVR UUIDs',
      name: 'MVRImageService',
    );

    final results = <String, BestImageResponse?>{};

    // Fetch in parallel for performance
    final futures = mvrUuids.map((uuid) async {
      final image = await getBestImages(
        uuid,
        includeMerged: includeMerged,
        useCache: useCache,
      );
      return MapEntry(uuid, image);
    }).toList();

    final entries = await Future.wait(futures);

    for (final entry in entries) {
      results[entry.key] = entry.value;
    }

    final successCount = results.values.where((v) => v != null).length;
    developer.log(
      '✅ Batch fetch complete: $successCount/${mvrUuids.length} successful',
      name: 'MVRImageService',
    );

    return results;
  }

  /// Fetch best face images for child MVR records (merged children of a
  /// super-individual). Keyed by child mvr_people_uuid.
  Future<Map<String, BestImageResponse?>> getBestImagesForMergedChildren(
    List<String> childMvrUuids,
  ) =>
      getBestImagesForMultiple(childMvrUuids, includeMerged: false, useCache: true);
}
