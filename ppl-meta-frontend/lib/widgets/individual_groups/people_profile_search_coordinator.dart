/// Shared flow: open restricted analytics filter → known-people search →
/// Cross-Video Individual Analysis for a Presence People Profile.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../models/cross_video_analysis_models.dart';
import '../../models/presence_models.dart';
import '../../screens/person_objects_detail_screen.dart';
import '../../services/media_api_client.dart';
import '../../services/presence_api_client.dart';
import '../analytics_filter_dialog.dart';

class PeopleProfileSearchCoordinator {
  PeopleProfileSearchCoordinator._();

  static (DateTime, DateTime) resolveTimeRange({
    required String timeFilter,
    DateTime? startDate,
    DateTime? endDate,
  }) {
    final now = DateTime.now().toUtc();
    switch (timeFilter) {
      case 'custom':
        return (
          (startDate ?? now.subtract(const Duration(days: 1))).toUtc(),
          (endDate ?? now).toUtc(),
        );
      case 'last_hour':
        return (now.subtract(const Duration(hours: 1)), now);
      case 'last_3_hours':
        return (now.subtract(const Duration(hours: 3)), now);
      case 'last_week':
        return (now.subtract(const Duration(days: 7)), now);
      case 'last_month':
        return (now.subtract(const Duration(days: 30)), now);
      case 'today':
      default:
        return (DateTime.utc(now.year, now.month, now.day), now);
    }
  }

  static List<String> expandDataSources(String dataSource) {
    switch (dataSource) {
      case 'instant_detection':
        return ['instant_detection'];
      case 'both':
        return ['recording', 'instant_detection'];
      case 'recording':
      default:
        return ['recording'];
    }
  }

  /// Opens filter dialog, runs search, navigates to cross-video analysis.
  static Future<void> run({
    required BuildContext context,
    required WidgetRef ref,
    required PresencePeopleProfile profile,
  }) async {
    final messenger = ScaffoldMessenger.of(context);
    final presence = PresenceApiClient(ref.read(apiClientProvider));
    final media = MediaApiClient(ref.read(apiClientProvider));

    // Ensure links are loaded
    PresencePeopleProfile resolved = profile;
    if (profile.links.isEmpty && profile.linkedMemberCount > 0) {
      final detail = await presence.getPeopleProfile(profile.pppUuid);
      if (detail.success && detail.data != null) {
        resolved = detail.data!;
      }
    }

    final mvrUuids = <String>{};
    for (final link in resolved.links) {
      final id = link.individualId.trim();
      if (id.isNotEmpty) mvrUuids.add(id);
    }

    if (mvrUuids.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'This people profile has no linked members to search for',
          ),
        ),
      );
      return;
    }

    final camerasResp = await media.getEnrichedCamerasList();
    if (!context.mounted) return;
    if (!camerasResp.success || camerasResp.data == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(camerasResp.error ?? 'Failed to load cameras'),
        ),
      );
      return;
    }
    final cameras = camerasResp.data!;

    final filterResult = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AnalyticsFilterDialog(
        title: 'Search detections — ${resolved.name}',
        currentTimeFilter: 'today',
        selectedCollectionIds: const [],
        selectedGenders: const [],
        selectedAgeGroups: const [],
        dataSource: 'both',
        detectionModality: 'face',
        autoRefresh: false,
        cameras: cameras,
        showDataSource: true,
        allowBothDataSources: true,
        showDetectionModality: false,
        showDemographics: false,
        showAgeGroups: false,
        showAutoRefresh: false,
        selectionLabel: 'Cameras',
      ),
    );

    if (filterResult == null || !context.mounted) return;

    final timeFilter = filterResult['timeFilter'] as String? ?? 'today';
    final (startTime, endTime) = resolveTimeRange(
      timeFilter: timeFilter,
      startDate: filterResult['startDate'] as DateTime?,
      endDate: filterResult['endDate'] as DateTime?,
    );
    final dataSource = filterResult['dataSource'] as String? ?? 'both';
    final sources = expandDataSources(dataSource);
    final selectedIds =
        (filterResult['collectionIds'] as List?)?.cast<String>() ?? <String>[];

    // Empty selection = all cameras (backend treats empty lists as unrestricted).
    final cameraIds = <String>[];
    final cameraDeviceIds = <String>[];
    if (selectedIds.isNotEmpty) {
      final selectedCameras = cameras.where((c) {
        final id = (c['id'] ??
                c['collection_name'] ??
                c['name'] ??
                c['uuid'] ??
                c['device_id'] ??
                c['camera_device_id'])
            ?.toString();
        return id != null && selectedIds.contains(id);
      }).toList();
      for (final c in selectedCameras) {
        final id = (c['id'] ?? c['collection_name'] ?? c['name'] ?? c['uuid'])
            ?.toString();
        if (id != null && id.isNotEmpty) cameraIds.add(id);
        final deviceId = (c['camera_device_id'] ?? c['device_id'])?.toString();
        if (deviceId != null && deviceId.isNotEmpty) {
          cameraDeviceIds.add(deviceId);
        }
      }
    }

    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(
        content: Row(
          children: [
            CircularProgressIndicator(),
            SizedBox(width: 20),
            Expanded(child: Text('Searching detections…')),
          ],
        ),
      ),
    );

    final searchResp = await media.searchKnownPeople(
      mvrPeopleUuids: mvrUuids.toList(),
      sources: sources,
      startTime: startTime,
      endTime: endTime,
      cameraIds: sources.contains('recording') ? cameraIds : null,
      cameraDeviceIds:
          sources.contains('instant_detection') ? cameraDeviceIds : null,
    );

    if (!context.mounted) return;
    Navigator.of(context, rootNavigator: true).pop(); // loading dialog

    if (!searchResp.success || searchResp.data == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(searchResp.error ?? 'Search failed'),
        ),
      );
      return;
    }

    final data = searchResp.data!;
    final matchedPeople =
        (data['matched_people'] as List?)?.cast<dynamic>() ?? const [];
    if (matchedPeople.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No detections found for this person')),
      );
      return;
    }

    final matchedUuids = <String>[];
    final searchResults = <Map<String, dynamic>>[];
    final instantMvrs = <Map<String, dynamic>>[];
    final appearanceByKnown = <String, List<Map<String, dynamic>>>{};

    for (final raw in matchedPeople) {
      if (raw is! Map) continue;
      final person = Map<String, dynamic>.from(raw);
      final uuid = person['mvr_people_uuid']?.toString();
      if (uuid == null || uuid.isEmpty) continue;
      matchedUuids.add(uuid);
      final appearances =
          (person['appearances'] as List?)?.whereType<Map>().toList() ?? [];
      appearanceByKnown[uuid] = appearances
          .map((a) => Map<String, dynamic>.from(a))
          .toList();
      final inst =
          (person['instant_mvrs'] as List?)?.whereType<Map>().toList() ?? [];
      for (final i in inst) {
        instantMvrs.add(Map<String, dynamic>.from(i));
      }
      searchResults.add({
        'mvr_people_uuid': uuid,
        'individual_uuids': [
          for (final a in appearances)
            if (a['individual_uuid'] != null) a['individual_uuid'].toString(),
        ],
        'total_appearances': person['total_appearances'] ?? appearances.length,
        'unique_videos': appearances
            .map((a) => a['video_uuid']?.toString())
            .whereType<String>()
            .toSet()
            .length,
        'first_seen': appearances.isNotEmpty
            ? appearances.first['timestamp']
            : startTime.toIso8601String(),
        'last_seen': appearances.isNotEmpty
            ? appearances.last['timestamp']
            : endTime.toIso8601String(),
        'confidence_score': person['best_similarity'] ?? 0.0,
        'quality_score': person['best_similarity'] ?? 0.0,
        'appearances': appearances,
        'data_sources': person['data_sources'] ?? sources,
      });
    }

    final sessionUuid =
        (data['search_session_uuid'] as String?) ??
            'people_profile_search_${resolved.pppUuid}_${DateTime.now().millisecondsSinceEpoch}';

    final analysisContext = CrossVideoAnalysisContext(
      individualUuids: matchedUuids,
      sessionUuid: sessionUuid,
      sessionData: {
        'source': 'people_profile_search',
        'ppp_uuid': resolved.pppUuid,
        'ppp_name': resolved.name,
        'data_sources': sources,
        'search_parameters': {
          'camera_ids': cameraIds,
          'camera_device_ids': cameraDeviceIds,
          'start_time': startTime.toIso8601String(),
          'end_time': endTime.toIso8601String(),
          'detection_modality': 'face',
          'time_filter': timeFilter,
        },
        'search_results': searchResults,
        'matched_appearances_by_mvr': appearanceByKnown,
        'instant_mvrs': instantMvrs,
        'individuals_found': matchedUuids.length,
        'unsearchable_mvr_uuids': data['unsearchable_mvr_uuids'] ?? [],
      },
    );

    if (!context.mounted) return;
    await Navigator.of(context, rootNavigator: true).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            PersonObjectsDetailScreen(crossVideoContext: analysisContext),
      ),
    );
  }
}
