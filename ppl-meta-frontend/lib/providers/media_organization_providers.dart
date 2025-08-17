import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/models/collection_models.dart';
import '../services/media_organization_service.dart';
import '../core/providers/camera_providers.dart';

/// Provider for the MediaOrganizationService
final mediaOrganizationServiceProvider = Provider<MediaOrganizationService>((ref) {
  final mediaApiClient = ref.watch(mediaApiClientProvider);
  
  return MediaOrganizationService(
    mediaApiClient: mediaApiClient,
  );
});

/// Provider for available collections (for organization dialog)
final availableCollectionsProvider = FutureProvider<List<MediaCollection>>((ref) async {
  final organizationService = ref.watch(mediaOrganizationServiceProvider);
  return await organizationService.getAvailableCollections();
});

/// Provider to track organization operation state
final organizationOperationStateProvider = Provider<OrganizationOperationState>((ref) {
  final service = ref.watch(mediaOrganizationServiceProvider);
  
  return OrganizationOperationState(
    isInProgress: service.isOperationInProgress,
    progress: service.operationProgress,
    description: service.currentOperationDescription,
    error: service.operationError,
  );
});

/// State class for organization operations
class OrganizationOperationState {
  final bool isInProgress;
  final double progress;
  final String? description;
  final String? error;

  const OrganizationOperationState({
    required this.isInProgress,
    required this.progress,
    this.description,
    this.error,
  });

  bool get hasError => error != null;
  bool get isComplete => !isInProgress && progress >= 1.0 && error == null;
}
