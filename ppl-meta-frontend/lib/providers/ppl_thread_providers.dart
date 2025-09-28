/// PPL Meta Frontend - PPL Thread Providers
/// 
/// Riverpod state management for the new PPL Thread service integration.
/// Provides simple READ-ONLY access to person count data from the
/// Orchestrator API endpoints.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/ppl_thread_service.dart';
import '../core/api/api_client.dart';

// PPL Thread Service Provider
final pplThreadServiceProvider = Provider<PPLThreadService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PPLThreadService(apiClient);
});

// Person Count Provider (per media ID)
final personCountProvider = FutureProvider.autoDispose
    .family<int, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.getPersonCount(mediaId);
});

// Person Objects Data Existence Provider (per media ID)
final personObjectsExistsProvider = FutureProvider.autoDispose
    .family<bool, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.hasPersonObjectsData(mediaId);
});

// Complete Person Objects Data Provider (per media ID)
final pplPersonObjectsDataProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>?, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.getPersonObjectsData(mediaId);
});