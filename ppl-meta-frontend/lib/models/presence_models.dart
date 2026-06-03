class PresenceAnalyticsSummary {
  final int totalSessions;
  final int completedSessions;
  final int pendingSessions;
  final int grantedSessions;
  final int deniedSessions;

  const PresenceAnalyticsSummary({
    required this.totalSessions,
    required this.completedSessions,
    required this.pendingSessions,
    required this.grantedSessions,
    required this.deniedSessions,
  });

  factory PresenceAnalyticsSummary.fromJson(Map<String, dynamic> json) {
    int readInt(List<String> keys) {
      for (final key in keys) {
        final value = json[key];
        if (value is int) {
          return value;
        }
        if (value is num) {
          return value.toInt();
        }
      }
      return 0;
    }

    final totalSessions = readInt(['total_sessions', 'sessions_total', 'total', 'sessions', 'attempts']);
    final grantedSessions = readInt(['granted_sessions', 'sessions_granted', 'granted']);
    final deniedSessions = readInt(['denied_sessions', 'sessions_denied', 'denied']);
    final failedSessions = readInt(['failed_sessions', 'sessions_failed', 'failed']);
    final completedSessions = readInt(['completed_sessions', 'sessions_completed']);
    final resolvedCompletedSessions = completedSessions > 0
        ? completedSessions
        : grantedSessions + deniedSessions + failedSessions;
    final pendingSessions = readInt(['pending_sessions', 'sessions_pending']);
    final resolvedPendingSessions = pendingSessions > 0
        ? pendingSessions
        : (totalSessions - resolvedCompletedSessions).clamp(0, totalSessions);

    return PresenceAnalyticsSummary(
      totalSessions: totalSessions,
      completedSessions: resolvedCompletedSessions,
      pendingSessions: resolvedPendingSessions,
      grantedSessions: grantedSessions,
      deniedSessions: deniedSessions,
    );
  }
}

class PresencePolicyRule {
  final String? triggerType;
  final String? actionType;

  const PresencePolicyRule({
    this.triggerType,
    this.actionType,
  });

  bool get isEmpty =>
      (triggerType == null || triggerType!.isEmpty) &&
      (actionType == null || actionType!.isEmpty);

  Map<String, dynamic> toJson() => {
        if (triggerType != null && triggerType!.isNotEmpty) 'trigger_type': triggerType,
        if (actionType != null && actionType!.isNotEmpty) 'action_type': actionType,
      };

  factory PresencePolicyRule.fromJson(Map<String, dynamic> json) {
    return PresencePolicyRule(
      triggerType: json['trigger_type']?.toString(),
      actionType: json['action_type']?.toString(),
    );
  }
}

class PresenceGroupPolicy {
  final PresencePolicyRule? granted;
  final PresencePolicyRule? denied;
  final PresencePolicyRule? retryRequired;
  final PresencePolicyRule? failed;

  const PresenceGroupPolicy({
    this.granted,
    this.denied,
    this.retryRequired,
    this.failed,
  });

  Map<String, dynamic> toJson() => {
        if (granted != null && !granted!.isEmpty) 'granted': granted!.toJson(),
        if (denied != null && !denied!.isEmpty) 'denied': denied!.toJson(),
        if (retryRequired != null && !retryRequired!.isEmpty) 'retry_required': retryRequired!.toJson(),
        if (failed != null && !failed!.isEmpty) 'failed': failed!.toJson(),
      };

  factory PresenceGroupPolicy.fromJson(Map<String, dynamic> json) {
    PresencePolicyRule? readRule(String key) {
      final value = json[key];
      if (value is Map<String, dynamic>) {
        return PresencePolicyRule.fromJson(value);
      }
      return null;
    }

    return PresenceGroupPolicy(
      granted: readRule('granted'),
      denied: readRule('denied'),
      retryRequired: readRule('retry_required'),
      failed: readRule('failed'),
    );
  }
}

class PresenceSessionSettings {
  final int sessionTimeoutSeconds;
  final int maxUnsuccessfulAttempts;
  final bool allowConcurrentTriggerOperations;
  final int qrToCameraTransitionWindowMinutes;

  const PresenceSessionSettings({
    required this.sessionTimeoutSeconds,
    required this.maxUnsuccessfulAttempts,
    required this.allowConcurrentTriggerOperations,
    required this.qrToCameraTransitionWindowMinutes,
  });

  const PresenceSessionSettings.defaults()
      : sessionTimeoutSeconds = 300,
        maxUnsuccessfulAttempts = 3,
        allowConcurrentTriggerOperations = true,
        qrToCameraTransitionWindowMinutes = 10;

  Map<String, dynamic> toJson() => {
        'session_timeout_seconds': sessionTimeoutSeconds,
        'max_unsuccessful_attempts': maxUnsuccessfulAttempts,
        'allow_concurrent_trigger_operations': allowConcurrentTriggerOperations,
      'qr_to_camera_transition_window_minutes': qrToCameraTransitionWindowMinutes,
      };

  factory PresenceSessionSettings.fromJson(Map<String, dynamic> json) {
    int readInt(String key, int fallback) {
      final value = json[key];
      if (value is int) {
        return value;
      }
      if (value is num) {
        return value.toInt();
      }
      return fallback;
    }

    return PresenceSessionSettings(
      sessionTimeoutSeconds: readInt('session_timeout_seconds', 300),
      maxUnsuccessfulAttempts: readInt('max_unsuccessful_attempts', 3),
      allowConcurrentTriggerOperations: json['allow_concurrent_trigger_operations'] != false,
      qrToCameraTransitionWindowMinutes: readInt('qr_to_camera_transition_window_minutes', 10),
    );
  }
}

class PresenceResourceReservation {
  final String resourceUuid;
  final String resourceType;
  final String installationUuid;
  final String platformResourceUuid;
  final String status;
  final Map<String, dynamic> metadata;

  const PresenceResourceReservation({
    required this.resourceUuid,
    required this.resourceType,
    required this.installationUuid,
    required this.platformResourceUuid,
    required this.status,
    required this.metadata,
  });

  factory PresenceResourceReservation.fromJson(Map<String, dynamic> json) {
    return PresenceResourceReservation(
      resourceUuid: (json['resource_uuid'] ?? '').toString(),
      resourceType: (json['resource_type'] ?? '').toString(),
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      platformResourceUuid: (json['platform_resource_uuid'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      metadata: (json['metadata'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class PresenceInstallationContext {
  final String installationUuid;
  final String presenceProfileUuid;
  final String installationName;
  final String licenceStatus;
  final String detectionBackendMode;
  final String? activePresenceIndividualGroupId;
  final String? activePresenceIndividualGroupName;
  final List<String> preferredCameraTypes;
  final List<String> preferredCameraNames;
  final List<String> allowedCameraStatuses;
  final Map<String, dynamic> installationReference;
  final PresenceGroupPolicy? groupPolicy;
  final PresenceSessionSettings sessionSettings;
  final String? reservedCameraUuid;
  final String? reservedCollectionUuid;
  final PresenceResourceReservation? reservedCamera;
  final PresenceResourceReservation? reservedCollection;

  const PresenceInstallationContext({
    required this.installationUuid,
    required this.presenceProfileUuid,
    required this.installationName,
    required this.licenceStatus,
    required this.detectionBackendMode,
    required this.activePresenceIndividualGroupId,
    required this.activePresenceIndividualGroupName,
    required this.preferredCameraTypes,
    required this.preferredCameraNames,
    required this.allowedCameraStatuses,
    required this.installationReference,
    required this.groupPolicy,
    required this.sessionSettings,
    required this.reservedCameraUuid,
    required this.reservedCollectionUuid,
    required this.reservedCamera,
    required this.reservedCollection,
  });

  factory PresenceInstallationContext.fromJson(Map<String, dynamic> json) {
    List<String> readList(String key) {
      final value = json[key];
      if (value is List) {
        return value.map((item) => item.toString()).toList();
      }
      return const [];
    }

    return PresenceInstallationContext(
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      presenceProfileUuid: (json['presence_profile_uuid'] ?? '').toString(),
      installationName: (json['installation_name'] ?? '').toString(),
      licenceStatus: (json['licence_status'] ?? '').toString(),
      detectionBackendMode: (json['detection_backend_mode'] ?? '').toString(),
      activePresenceIndividualGroupId: json['active_presence_individual_group_id']?.toString(),
      activePresenceIndividualGroupName: json['active_presence_individual_group_name']?.toString(),
      preferredCameraTypes: readList('preferred_camera_types'),
      preferredCameraNames: readList('preferred_camera_names'),
      allowedCameraStatuses: readList('allowed_camera_statuses'),
        installationReference: (json['installation_reference'] as Map<String, dynamic>? ?? const {}),
      groupPolicy: json['group_policy'] is Map<String, dynamic>
          ? PresenceGroupPolicy.fromJson(json['group_policy'] as Map<String, dynamic>)
          : null,
        sessionSettings: json['session_settings'] is Map<String, dynamic>
          ? PresenceSessionSettings.fromJson(json['session_settings'] as Map<String, dynamic>)
          : const PresenceSessionSettings.defaults(),
      reservedCameraUuid: json['reserved_camera_uuid']?.toString(),
      reservedCollectionUuid: json['reserved_collection_uuid']?.toString(),
      reservedCamera: json['reserved_camera'] is Map<String, dynamic>
          ? PresenceResourceReservation.fromJson(json['reserved_camera'] as Map<String, dynamic>)
          : null,
      reservedCollection: json['reserved_collection'] is Map<String, dynamic>
          ? PresenceResourceReservation.fromJson(json['reserved_collection'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PresenceIndividualGroupOption {
  final String individualGroupId;
  final String name;
  final String? description;
  final int memberCount;

  const PresenceIndividualGroupOption({
    required this.individualGroupId,
    required this.name,
    required this.description,
    required this.memberCount,
  });

  factory PresenceIndividualGroupOption.fromJson(Map<String, dynamic> json) {
    final rawMemberCount = json['member_count'];
    return PresenceIndividualGroupOption(
      individualGroupId: (json['individual_group_id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      description: json['description']?.toString(),
      memberCount: rawMemberCount is num ? rawMemberCount.toInt() : 0,
    );
  }
}

class PresenceCameraOption {
  final String deviceId;
  final String name;
  final String cameraType;
  final String status;
  final bool reservedForPresence;
  final String? reservedResourceUuid;
  final String? reservedInstallationUuid;
  final String? linkedCollectionUuid;

  const PresenceCameraOption({
    required this.deviceId,
    required this.name,
    required this.cameraType,
    required this.status,
    required this.reservedForPresence,
    required this.reservedResourceUuid,
    required this.reservedInstallationUuid,
    required this.linkedCollectionUuid,
  });

  factory PresenceCameraOption.fromJson(Map<String, dynamic> json) {
    return PresenceCameraOption(
      deviceId: (json['device_id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      cameraType: (json['camera_type'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      reservedForPresence: json['reserved_for_presence'] == true,
      reservedResourceUuid: json['reserved_resource_uuid']?.toString(),
      reservedInstallationUuid: json['reserved_installation_uuid']?.toString(),
      linkedCollectionUuid: json['linked_collection_uuid']?.toString(),
    );
  }
}

class PresenceAnalyticsBucket {
  final String key;
  final int count;

  const PresenceAnalyticsBucket({
    required this.key,
    required this.count,
  });

  String get label {
    return key
        .split('_')
        .where((part) => part.isNotEmpty)
        .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
  }

  factory PresenceAnalyticsBucket.fromJson(Map<String, dynamic> json) {
    final rawKey = json['session_mode'] ??
        json['grant_type'] ??
        json['key'] ??
        json['name'] ??
        'unknown';
    final rawCount = json['count'] ?? json['event_count'] ?? json['sessions'] ?? 0;

    return PresenceAnalyticsBucket(
      key: rawKey.toString(),
      count: rawCount is num ? rawCount.toInt() : 0,
    );
  }
}

class PresenceSessionTraceSummary {
  final String sessionUuid;
  final String status;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String qrStatus;
  final String decision;
  final String? reasonCode;
  final String? actorLabel;
  final String? actorEmail;
  final String? interactionLabel;
  final String? sourceLabel;
  final String? cameraLabel;
  final String? headline;
  final String? subtitle;
  final DateTime? createdAt;
  final DateTime? completedAt;

  const PresenceSessionTraceSummary({
    required this.sessionUuid,
    required this.status,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.qrStatus,
    required this.decision,
    required this.reasonCode,
    required this.actorLabel,
    required this.actorEmail,
    required this.interactionLabel,
    required this.sourceLabel,
    required this.cameraLabel,
    required this.headline,
    required this.subtitle,
    required this.createdAt,
    required this.completedAt,
  });

  factory PresenceSessionTraceSummary.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(String key) {
      final value = json[key];
      if (value is String && value.isNotEmpty) {
        return DateTime.tryParse(value)?.toLocal();
      }
      return null;
    }

    return PresenceSessionTraceSummary(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      status: (json['status'] ?? 'unknown').toString(),
      sessionMode: (json['session_mode'] ?? 'unknown').toString(),
      assuranceLevel: (json['assurance_level'] ?? 'unknown').toString(),
      grantType: (json['grant_type'] ?? 'unknown').toString(),
      qrStatus: (json['qr_status'] ?? 'unknown').toString(),
      decision: (json['decision'] ?? 'unknown').toString(),
      reasonCode: json['reason_code']?.toString(),
      actorLabel: json['actor_label']?.toString(),
      actorEmail: json['actor_email']?.toString(),
      interactionLabel: json['interaction_label']?.toString(),
      sourceLabel: json['source_label']?.toString(),
      cameraLabel: json['camera_label']?.toString(),
      headline: json['headline']?.toString(),
      subtitle: json['subtitle']?.toString(),
      createdAt: parseDate('created_at'),
      completedAt: parseDate('completed_at'),
    );
  }
}

class PresenceSessionTracePage {
  final List<PresenceSessionTraceSummary> items;
  final int total;
  final int returned;
  final int limit;
  final int offset;
  final bool hasMore;

  const PresenceSessionTracePage({
    required this.items,
    required this.total,
    required this.returned,
    required this.limit,
    required this.offset,
    required this.hasMore,
  });

  factory PresenceSessionTracePage.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'];
    final items = rawItems is List
        ? rawItems
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .map(PresenceSessionTraceSummary.fromJson)
            .toList()
        : const <PresenceSessionTraceSummary>[];
    int readInt(String key, int fallback) {
      final value = json[key];
      return value is num ? value.toInt() : fallback;
    }

    return PresenceSessionTracePage(
      items: items,
      total: readInt('total', items.length),
      returned: readInt('returned', items.length),
      limit: readInt('limit', items.length),
      offset: readInt('offset', 0),
      hasMore: json['has_more'] == true,
    );
  }
}

class PresenceUserDayAwardSummary {
  final String userEmail;
  final String userLabel;
  final String? userUuid;
  final DateTime date;
  final Map<String, int> grantTypeTotals;
  final int totalAwards;
  final DateTime? firstAwardAt;
  final DateTime? lastAwardAt;
  final int qrToCamTransitionCount;
  final int qrToCamTransitionWindowMinutes;
  final List<String> qrToCamContributingSessionUuids;

  const PresenceUserDayAwardSummary({
    required this.userEmail,
    required this.userLabel,
    required this.userUuid,
    required this.date,
    required this.grantTypeTotals,
    required this.totalAwards,
    required this.firstAwardAt,
    required this.lastAwardAt,
    required this.qrToCamTransitionCount,
    required this.qrToCamTransitionWindowMinutes,
    required this.qrToCamContributingSessionUuids,
  });

  String get identity => userEmail.isNotEmpty ? userEmail : userLabel;

  String get rowKey => '${identity.toLowerCase()}|${date.toIso8601String().split('T').first}';

  factory PresenceUserDayAwardSummary.fromJson(Map<String, dynamic> json) {
    DateTime? parseDateTime(dynamic value) {
      if (value == null) {
        return null;
      }
      return DateTime.tryParse(value.toString());
    }

    final dateValue = DateTime.tryParse((json['date'] ?? '').toString()) ?? DateTime.now();
    final rawTotals = json['grant_type_totals'];
    final totals = <String, int>{};
    if (rawTotals is Map) {
      rawTotals.forEach((key, value) {
        if (key == null) {
          return;
        }
        final parsedValue = value is num ? value.toInt() : int.tryParse(value.toString()) ?? 0;
        totals[key.toString()] = parsedValue;
      });
    }

    final userEmail = (json['user_email'] ?? '').toString();
    final userLabel = (json['user_label'] ?? '').toString();
    return PresenceUserDayAwardSummary(
      userEmail: userEmail,
      userLabel: userLabel,
      userUuid: json['user_uuid']?.toString(),
      date: DateTime(dateValue.year, dateValue.month, dateValue.day),
      grantTypeTotals: totals,
      totalAwards: json['total_awards'] is num ? (json['total_awards'] as num).toInt() : 0,
      firstAwardAt: parseDateTime(json['first_award_at']),
      lastAwardAt: parseDateTime(json['last_award_at']),
      qrToCamTransitionCount: json['qr_to_cam_transition_count'] is num
          ? (json['qr_to_cam_transition_count'] as num).toInt()
          : 0,
      qrToCamTransitionWindowMinutes: json['qr_to_cam_transition_window_minutes'] is num
          ? (json['qr_to_cam_transition_window_minutes'] as num).toInt()
          : 10,
        qrToCamContributingSessionUuids: (json['qr_to_cam_contributing_session_uuids'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .where((value) => value.isNotEmpty)
          .toList(),
    );
  }
}

class PresenceUserDayAwardPage {
  final List<PresenceUserDayAwardSummary> items;
  final int total;
  final int returned;
  final int limit;
  final int offset;
  final bool hasMore;
  final List<String> availableUsers;

  const PresenceUserDayAwardPage({
    required this.items,
    required this.total,
    required this.returned,
    required this.limit,
    required this.offset,
    required this.hasMore,
    required this.availableUsers,
  });

  factory PresenceUserDayAwardPage.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'];
    final items = rawItems is List
        ? rawItems
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .map(PresenceUserDayAwardSummary.fromJson)
            .toList()
        : const <PresenceUserDayAwardSummary>[];

    int readInt(String key, int fallback) {
      final value = json[key];
      return value is num ? value.toInt() : fallback;
    }

    final rawUsers = json['available_users'];
    final availableUsers = rawUsers is List
        ? rawUsers.map((entry) => entry.toString()).where((entry) => entry.isNotEmpty).toList()
        : const <String>[];

    return PresenceUserDayAwardPage(
      items: items,
      total: readInt('total', items.length),
      returned: readInt('returned', items.length),
      limit: readInt('limit', items.length),
      offset: readInt('offset', 0),
      hasMore: json['has_more'] == true,
      availableUsers: availableUsers,
    );
  }
}

class PresenceExternalAssets {
  final String? individualGroupId;
  final String? triggerUuid;
  final String? actionUuid;

  const PresenceExternalAssets({
    this.individualGroupId,
    this.triggerUuid,
    this.actionUuid,
  });

  factory PresenceExternalAssets.fromJson(Map<String, dynamic> json) {
    return PresenceExternalAssets(
      individualGroupId: json['individual_group_id']?.toString(),
      triggerUuid: json['trigger_uuid']?.toString(),
      actionUuid: json['action_uuid']?.toString(),
    );
  }
}

class PresenceTriggerObservation {
  final String? triggerUuid;
  final List<String> configuredActionUuids;
  final List<String> configuredActionNames;
  final String? lastFiredAt;
  final String? lastMatchedAt;
  final String? pplMatchGroupId;

  const PresenceTriggerObservation({
    this.triggerUuid,
    required this.configuredActionUuids,
    required this.configuredActionNames,
    this.lastFiredAt,
    this.lastMatchedAt,
    this.pplMatchGroupId,
  });

  factory PresenceTriggerObservation.fromJson(Map<String, dynamic> json) {
    List<String> readList(String key) {
      final value = json[key];
      if (value is List) {
        return value.map((item) => item.toString()).toList();
      }
      return const [];
    }

    return PresenceTriggerObservation(
      triggerUuid: json['trigger_uuid']?.toString(),
      configuredActionUuids: readList('configured_action_uuids'),
      configuredActionNames: readList('configured_action_names'),
      lastFiredAt: json['last_fired_at']?.toString(),
      lastMatchedAt: json['last_matched_at']?.toString(),
      pplMatchGroupId: json['ppl_match_group_id']?.toString(),
    );
  }
}

class PresenceActionPlanDetails {
  final String sessionUuid;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String decision;
  final String? matchedGroupUuid;
  final String? policySource;
  final String? triggerType;
  final String? actionType;
  final String? actionExecutionStatus;
  final PresenceExternalAssets? externalAssets;
  final PresenceTriggerObservation? triggerObservation;

  const PresenceActionPlanDetails({
    required this.sessionUuid,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.decision,
    required this.matchedGroupUuid,
    required this.policySource,
    required this.triggerType,
    required this.actionType,
    required this.actionExecutionStatus,
    required this.externalAssets,
    required this.triggerObservation,
  });

  factory PresenceActionPlanDetails.fromJson(Map<String, dynamic> json) {
    return PresenceActionPlanDetails(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      decision: (json['decision'] ?? '').toString(),
      matchedGroupUuid: json['matched_group_uuid']?.toString(),
      policySource: json['policy_source']?.toString(),
      triggerType: json['trigger_type']?.toString(),
      actionType: json['action_type']?.toString(),
      actionExecutionStatus: json['action_execution_status']?.toString(),
      externalAssets: json['external_assets'] is Map<String, dynamic>
          ? PresenceExternalAssets.fromJson(json['external_assets'] as Map<String, dynamic>)
          : null,
      triggerObservation: json['trigger_observation'] is Map<String, dynamic>
          ? PresenceTriggerObservation.fromJson(json['trigger_observation'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PresenceDecisionRecordDetails {
  final String decisionUuid;
  final String sessionUuid;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String installationUuid;
  final String userUuid;
  final String deviceUuid;
  final String decision;
  final String reasonCode;
  final String? matchedGroupUuid;
  final String? policySource;
  final String? triggerType;
  final String? actionType;
  final String? actionExecutionStatus;
  final String? actionLogUuid;
  final String? createdAt;

  const PresenceDecisionRecordDetails({
    required this.decisionUuid,
    required this.sessionUuid,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.installationUuid,
    required this.userUuid,
    required this.deviceUuid,
    required this.decision,
    required this.reasonCode,
    required this.matchedGroupUuid,
    required this.policySource,
    required this.triggerType,
    required this.actionType,
    required this.actionExecutionStatus,
    required this.actionLogUuid,
    required this.createdAt,
  });

  factory PresenceDecisionRecordDetails.fromJson(Map<String, dynamic> json) {
    return PresenceDecisionRecordDetails(
      decisionUuid: (json['decision_uuid'] ?? '').toString(),
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      userUuid: (json['user_uuid'] ?? '').toString(),
      deviceUuid: (json['device_uuid'] ?? '').toString(),
      decision: (json['decision'] ?? '').toString(),
      reasonCode: (json['reason_code'] ?? '').toString(),
      matchedGroupUuid: json['matched_group_uuid']?.toString(),
      policySource: json['policy_source']?.toString(),
      triggerType: json['trigger_type']?.toString(),
      actionType: json['action_type']?.toString(),
      actionExecutionStatus: json['action_execution_status']?.toString(),
      actionLogUuid: json['action_log_uuid']?.toString(),
      createdAt: json['created_at']?.toString(),
    );
  }
}

class PresenceAuditLogTrace {
  final String? logUuid;
  final bool found;
  final Map<String, dynamic>? payload;
  final String? error;

  const PresenceAuditLogTrace({
    required this.logUuid,
    required this.found,
    required this.payload,
    required this.error,
  });

  factory PresenceAuditLogTrace.fromJson(Map<String, dynamic> json) {
    return PresenceAuditLogTrace(
      logUuid: json['log_uuid']?.toString(),
      found: json['found'] == true,
      payload: json['payload'] is Map<String, dynamic> ? json['payload'] as Map<String, dynamic> : null,
      error: json['error']?.toString(),
    );
  }
}

class PresenceSessionDetails {
  final String sessionUuid;
  final String status;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String decision;
  final String qrStatus;
  final String detectionStatus;
  final String? matchedGroupUuid;
  final String? policySource;
  final String? triggerType;
  final String? actionType;
  final String? actionExecutionStatus;
  final String? resolvedCameraUuid;
  final String? resolvedCollectionUuid;
  final String? createdAt;
  final PresenceExternalAssets? externalAssets;

  const PresenceSessionDetails({
    required this.sessionUuid,
    required this.status,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.decision,
    required this.qrStatus,
    required this.detectionStatus,
    required this.matchedGroupUuid,
    required this.policySource,
    required this.triggerType,
    required this.actionType,
    required this.actionExecutionStatus,
    required this.resolvedCameraUuid,
    required this.resolvedCollectionUuid,
    required this.createdAt,
    required this.externalAssets,
  });

  factory PresenceSessionDetails.fromJson(Map<String, dynamic> json) {
    return PresenceSessionDetails(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      decision: (json['decision'] ?? '').toString(),
      qrStatus: (json['qr_status'] ?? '').toString(),
      detectionStatus: (json['detection_status'] ?? '').toString(),
      matchedGroupUuid: json['matched_group_uuid']?.toString(),
      policySource: json['policy_source']?.toString(),
      triggerType: json['trigger_type']?.toString(),
      actionType: json['action_type']?.toString(),
      actionExecutionStatus: json['action_execution_status']?.toString(),
      resolvedCameraUuid: json['resolved_camera_uuid']?.toString(),
      resolvedCollectionUuid: json['resolved_collection_uuid']?.toString(),
      createdAt: json['created_at']?.toString(),
      externalAssets: json['external_assets'] is Map<String, dynamic>
          ? PresenceExternalAssets.fromJson(json['external_assets'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PresenceSessionTraceDetails {
  final PresenceSessionDetails session;
  final PresenceActionPlanDetails actionPlan;
  final List<PresenceDecisionRecordDetails> decisionHistory;
  final PresenceAuditLogTrace? auditLog;

  const PresenceSessionTraceDetails({
    required this.session,
    required this.actionPlan,
    required this.decisionHistory,
    required this.auditLog,
  });

  factory PresenceSessionTraceDetails.fromJson(Map<String, dynamic> json) {
    final decisionItems = (json['decision_history'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(PresenceDecisionRecordDetails.fromJson)
        .toList();

    return PresenceSessionTraceDetails(
      session: PresenceSessionDetails.fromJson((json['session'] as Map<String, dynamic>? ?? const {})),
      actionPlan: PresenceActionPlanDetails.fromJson((json['action_plan'] as Map<String, dynamic>? ?? const {})),
      decisionHistory: decisionItems,
      auditLog: json['audit_log'] is Map<String, dynamic>
          ? PresenceAuditLogTrace.fromJson(json['audit_log'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PresenceResultDetails {
  final String sessionUuid;
  final String status;
  final String decision;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String reasonCode;
  final String? policySource;
  final String? triggerType;
  final String? actionType;
  final String? actionExecutionStatus;
  final String? resolvedCameraUuid;
  final String? resolvedCollectionUuid;

  const PresenceResultDetails({
    required this.sessionUuid,
    required this.status,
    required this.decision,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.reasonCode,
    required this.policySource,
    required this.triggerType,
    required this.actionType,
    required this.actionExecutionStatus,
    required this.resolvedCameraUuid,
    required this.resolvedCollectionUuid,
  });

  factory PresenceResultDetails.fromJson(Map<String, dynamic> json) {
    return PresenceResultDetails(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      decision: (json['decision'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      reasonCode: (json['reason_code'] ?? '').toString(),
      policySource: json['policy_source']?.toString(),
      triggerType: json['trigger_type']?.toString(),
      actionType: json['action_type']?.toString(),
      actionExecutionStatus: json['action_execution_status']?.toString(),
      resolvedCameraUuid: json['resolved_camera_uuid']?.toString(),
      resolvedCollectionUuid: json['resolved_collection_uuid']?.toString(),
    );
  }
}

class PresenceLiveSession {
  final String sessionUuid;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String status;
  final String? decision;
  final String? failureReasonCode;
  final bool retryAllowed;
  final String? detectionStatus;
  final String? qrStatus;
  final String? resolvedCameraUuid;
  final String? resolvedCollectionUuid;
  final String? expiresAt;
  final PresenceExternalAssets? externalAssets;

  const PresenceLiveSession({
    required this.sessionUuid,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.status,
    required this.decision,
    required this.failureReasonCode,
    required this.retryAllowed,
    required this.detectionStatus,
    required this.qrStatus,
    required this.resolvedCameraUuid,
    required this.resolvedCollectionUuid,
    required this.expiresAt,
    required this.externalAssets,
  });

  factory PresenceLiveSession.fromJson(Map<String, dynamic> json) {
    return PresenceLiveSession(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      decision: json['decision']?.toString(),
      failureReasonCode: json['failure_reason_code']?.toString(),
      retryAllowed: json['retry_allowed'] == true,
      detectionStatus: json['detection_status']?.toString(),
      qrStatus: json['qr_status']?.toString(),
      resolvedCameraUuid: json['resolved_camera_uuid']?.toString(),
      resolvedCollectionUuid: json['resolved_collection_uuid']?.toString(),
      expiresAt: json['expires_at']?.toString(),
      externalAssets: json['external_assets'] is Map<String, dynamic>
          ? PresenceExternalAssets.fromJson(json['external_assets'] as Map<String, dynamic>)
          : null,
    );
  }
}

class PresenceQrPayload {
  final bool found;
  final String installationUuid;
  final String? deviceReference;
  final String? qrToken;
  final String? expiresAt;
  final String? sessionUuid;
  final String? sessionStatus;
  final String? qrStatus;
  final String? qrType;
  final Map<String, dynamic>? payload;

  const PresenceQrPayload({
    required this.found,
    required this.installationUuid,
    required this.deviceReference,
    required this.qrToken,
    required this.expiresAt,
    required this.sessionUuid,
    required this.sessionStatus,
    required this.qrStatus,
    required this.qrType,
    required this.payload,
  });

  factory PresenceQrPayload.fromJson(Map<String, dynamic> json) {
    return PresenceQrPayload(
      found: json['found'] == true,
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      deviceReference: json['device_reference']?.toString(),
      qrToken: json['qr_token']?.toString(),
      expiresAt: json['expires_at']?.toString(),
      sessionUuid: json['session_uuid']?.toString(),
      sessionStatus: json['session_status']?.toString(),
      qrStatus: json['qr_status']?.toString(),
      qrType: json['qr_type']?.toString() ?? (json['payload'] is Map<String, dynamic> ? (json['payload']['qr_type']?.toString()) : null),
      payload: json['payload'] is Map<String, dynamic> ? json['payload'] as Map<String, dynamic> : null,
    );
  }
}

class PresenceQrValidation {
  final bool valid;
  final String? sessionUuid;
  final String? installationUuid;
  final String? qrType;
  final String? referenceSource;

  const PresenceQrValidation({
    required this.valid,
    required this.sessionUuid,
    required this.installationUuid,
    required this.qrType,
    required this.referenceSource,
  });

  factory PresenceQrValidation.fromJson(Map<String, dynamic> json) {
    return PresenceQrValidation(
      valid: json['valid'] == true,
      sessionUuid: json['session_uuid']?.toString(),
      installationUuid: json['installation_uuid']?.toString(),
      qrType: json['qr_type']?.toString(),
      referenceSource: json['reference_source']?.toString(),
    );
  }
}