import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';
import '../services/media_api_client.dart';

/// Body detection box for replay overlay (mirrors FaceDetection shape).
class BodyDetection {
  final String id;
  final int frameNumber;
  final FaceBoundingBox boundingBox;
  final double confidence;
  final String? posture;

  const BodyDetection({
    required this.id,
    required this.frameNumber,
    required this.boundingBox,
    required this.confidence,
    this.posture,
  });
}

class MediaBodyDataState {
  final String mediaId;
  final Map<int, List<BodyDetection>> bodiesByFrame;
  final bool isLoading;
  final String? error;

  const MediaBodyDataState({
    required this.mediaId,
    this.bodiesByFrame = const {},
    this.isLoading = false,
    this.error,
  });

  List<BodyDetection> forFrame(int frame) => bodiesByFrame[frame] ?? const [];

  int get totalCount =>
      bodiesByFrame.values.fold(0, (sum, list) => sum + list.length);
}

class MediaBodyDataNotifier extends StateNotifier<MediaBodyDataState> {
  MediaBodyDataNotifier(this._api, this.mediaId)
      : super(MediaBodyDataState(mediaId: mediaId, isLoading: true));

  final ApiClient _api;
  final String mediaId;

  Future<void> loadBodies() async {
    state = MediaBodyDataState(mediaId: mediaId, isLoading: true);
    try {
      final response = await _api.get(
        '/api/v1/object-detections/by-frame',
        queryParameters: {'media_id': mediaId},
      );
      final data = response.data;
      final raw = (data is Map && data['bodies_by_frame'] is Map)
          ? data['bodies_by_frame'] as Map
          : <dynamic, dynamic>{};
      final mapped = <int, List<BodyDetection>>{};
      raw.forEach((key, value) {
        final frame = int.tryParse(key.toString()) ?? 0;
        final list = <BodyDetection>[];
        if (value is List) {
          for (final item in value) {
            if (item is! Map) continue;
            final bbox = item['bbox'];
            if (bbox is! List || bbox.length < 4) continue;
            final x1 = (bbox[0] as num).toDouble();
            final y1 = (bbox[1] as num).toDouble();
            final x2 = (bbox[2] as num).toDouble();
            final y2 = (bbox[3] as num).toDouble();
            list.add(
              BodyDetection(
                id: item['id']?.toString() ?? '${frame}_${list.length}',
                frameNumber: frame,
                boundingBox: FaceBoundingBox(
                  left: x1,
                  top: y1,
                  width: (x2 - x1).abs(),
                  height: (y2 - y1).abs(),
                ),
                confidence: (item['confidence'] as num?)?.toDouble() ?? 0,
                posture: item['posture']?.toString(),
              ),
            );
          }
        }
        if (list.isNotEmpty) {
          mapped[frame] = list;
        }
      });
      state = MediaBodyDataState(mediaId: mediaId, bodiesByFrame: mapped);
    } catch (e) {
      state = MediaBodyDataState(
        mediaId: mediaId,
        error: e.toString(),
      );
    }
  }
}

final mediaBodyDataProvider = StateNotifierProvider.family<
    MediaBodyDataNotifier, MediaBodyDataState, String>((ref, mediaId) {
  final api = ref.watch(apiClientProvider);
  final notifier = MediaBodyDataNotifier(api, mediaId);
  notifier.loadBodies();
  return notifier;
});
