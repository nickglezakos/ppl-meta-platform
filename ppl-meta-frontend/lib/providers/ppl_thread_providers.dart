/// PPL Meta Frontend - PPL Thread Providers
/// 
/// Riverpod state management for the new PPL Thread service integration.
/// Provides simple READ-ONLY access to person count data from the
/// Orchestrator API endpoints.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/ppl_thread_service.dart';
import '../core/api/api_client.dart';
import '../models/enhanced_person_objects_models.dart';

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

// =============================================================================
// ENHANCED PROVIDERS FOR DISTANCE-BASED COLOR CODING
// =============================================================================

// Enhanced Person Objects Provider with distance calculations
final enhancedPersonObjectsProvider = FutureProvider.autoDispose
    .family<EnhancedPPLThreadResponse?, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.getEnhancedPersonObjects(mediaId);
});

// Person Object Groups Provider (simplified for UI widgets)
final personObjectGroupsProvider = FutureProvider.autoDispose
    .family<List<EnhancedPersonObjectGroup>, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.getPersonObjectGroups(mediaId);
});

// Enhanced Person Objects Existence Provider
final enhancedPersonObjectsExistsProvider = FutureProvider.autoDispose
    .family<bool, String>((ref, mediaId) async {
  final service = ref.read(pplThreadServiceProvider);
  return await service.hasEnhancedPersonObjectsData(mediaId);
});

// Person Objects Statistics Provider (derived from enhanced data)
final personObjectsStatisticsProvider = FutureProvider.autoDispose
    .family<PersonObjectsStatistics?, String>((ref, mediaId) async {
  final enhancedData = await ref.watch(enhancedPersonObjectsProvider(mediaId).future);
  
  if (enhancedData == null) return null;
  
  return PersonObjectsStatistics(
    totalPersons: enhancedData.totalPersons,
    totalFaces: enhancedData.totalFaces,
    processingTimeMs: enhancedData.processingTimeMs,
    groupingAlgorithm: enhancedData.groupingAlgorithm,
    sessionUuid: enhancedData.sessionUuid,
    personGroups: enhancedData.personGroups,
  );
});

// =============================================================================
// PERSON OBJECTS STATISTICS DATA CLASS
// =============================================================================

/// Statistics derived from enhanced person objects data
class PersonObjectsStatistics {
  final int totalPersons;
  final int totalFaces;
  final double processingTimeMs;
  final String groupingAlgorithm;
  final String sessionUuid;
  final List<EnhancedPersonObjectGroup> personGroups;

  const PersonObjectsStatistics({
    required this.totalPersons,
    required this.totalFaces,
    required this.processingTimeMs,
    required this.groupingAlgorithm,
    required this.sessionUuid,
    required this.personGroups,
  });

  /// Get the closest person (minimum distance)
  EnhancedPersonObjectGroup? get closestPerson {
    if (personGroups.isEmpty) return null;
    
    return personGroups.reduce((current, next) =>
        current.closestDistance < next.closestDistance ? current : next);
  }

  /// Get the average distance across all persons
  double get averageDistance {
    if (personGroups.isEmpty) return 0.0;
    
    final totalDistance = personGroups
        .map((group) => group.closestDistance)
        .reduce((a, b) => a + b);
    
    return totalDistance / personGroups.length;
  }

  /// Get count of persons in close proximity (< 20m)
  int get closeProximityCount {
    return personGroups.where((group) => group.closestDistance < 20).length;
  }

  /// Get count of persons at safe distance (>= 30m)
  int get safeDistanceCount {
    return personGroups.where((group) => group.closestDistance >= 30).length;
  }

  @override
  String toString() {
    return 'PersonObjectsStatistics(persons: $totalPersons, faces: $totalFaces, '
           'avg_distance: ${averageDistance.toStringAsFixed(1)}m, close: $closeProximityCount)';
  }
}