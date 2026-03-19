// MVR Image Service Provider
// Riverpod provider for MVRImageService

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api/api_client.dart';
import '../services/mvr_image_service.dart';

final mvrImageServiceProvider = Provider<MVRImageService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return MVRImageService(apiClient);
});
