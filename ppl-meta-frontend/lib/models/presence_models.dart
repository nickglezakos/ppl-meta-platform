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

    return PresenceAnalyticsSummary(
      totalSessions: readInt(['total_sessions', 'sessions_total']),
      completedSessions: readInt(['completed_sessions', 'sessions_completed']),
      pendingSessions: readInt(['pending_sessions', 'sessions_pending']),
      grantedSessions: readInt(['granted_sessions', 'sessions_granted']),
      deniedSessions: readInt(['denied_sessions', 'sessions_denied']),
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

  const PresenceSessionSettings({
    required this.sessionTimeoutSeconds,
    required this.maxUnsuccessfulAttempts,
    required this.allowConcurrentTriggerOperations,
  });

  const PresenceSessionSettings.defaults()
      : sessionTimeoutSeconds = 300,
        maxUnsuccessfulAttempts = 3,
        allowConcurrentTriggerOperations = true;

  Map<String, dynamic> toJson() => {
        'session_timeout_seconds': sessionTimeoutSeconds,
        'max_unsuccessful_attempts': maxUnsuccessfulAttempts,
        'allow_concurrent_trigger_operations': allowConcurrentTriggerOperations,
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

class PresenceGroupSummary {
  final String groupUuid;
  final String installationUuid;
  final String? userUuid;
  final String displayName;
  final String status;
  final PresenceGroupPolicy? groupPolicy;

  const PresenceGroupSummary({
    required this.groupUuid,
    required this.installationUuid,
    required this.userUuid,
    required this.displayName,
    required this.status,
    required this.groupPolicy,
  });

  factory PresenceGroupSummary.fromJson(Map<String, dynamic> json) {
    return PresenceGroupSummary(
      groupUuid: (json['group_uuid'] ?? '').toString(),
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      userUuid: json['user_uuid']?.toString(),
      displayName: (json['display_name'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      groupPolicy: json['group_policy'] is Map<String, dynamic>
          ? PresenceGroupPolicy.fromJson(json['group_policy'] as Map<String, dynamic>)
          : null,
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
    final rawCount = json['count'] ?? json['sessions'] ?? 0;

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
  final DateTime? createdAt;
  final DateTime? completedAt;

  const PresenceSessionTraceSummary({
    required this.sessionUuid,
    required this.status,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.qrStatus,
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
      createdAt: parseDate('created_at'),
      completedAt: parseDate('completed_at'),
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