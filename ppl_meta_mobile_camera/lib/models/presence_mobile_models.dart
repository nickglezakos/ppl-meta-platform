class PresenceMobileSession {
  final String sessionUuid;
  final String sessionMode;
  final String assuranceLevel;
  final String grantType;
  final String status;
  final String qrStatus;
  final String detectionStatus;
  final bool retryAllowed;
  final String? decision;
  final String? expiresAt;
  final String? failureReasonCode;

  const PresenceMobileSession({
    required this.sessionUuid,
    required this.sessionMode,
    required this.assuranceLevel,
    required this.grantType,
    required this.status,
    required this.qrStatus,
    required this.detectionStatus,
    required this.retryAllowed,
    required this.decision,
    required this.expiresAt,
    required this.failureReasonCode,
  });

  factory PresenceMobileSession.fromJson(Map<String, dynamic> json) {
    return PresenceMobileSession(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      sessionMode: (json['session_mode'] ?? '').toString(),
      assuranceLevel: (json['assurance_level'] ?? '').toString(),
      grantType: (json['grant_type'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      qrStatus: (json['qr_status'] ?? '').toString(),
      detectionStatus: (json['detection_status'] ?? '').toString(),
      retryAllowed: json['retry_allowed'] == true,
      decision: json['decision']?.toString(),
      expiresAt: json['expires_at']?.toString(),
      failureReasonCode: json['failure_reason_code']?.toString(),
    );
  }
}

class PresenceMobileDetectionAttempt {
  final String attemptUuid;
  final int attemptIndex;
  final String status;
  final String capturePhase;

  const PresenceMobileDetectionAttempt({
    required this.attemptUuid,
    required this.attemptIndex,
    required this.status,
    required this.capturePhase,
  });

  factory PresenceMobileDetectionAttempt.fromJson(Map<String, dynamic> json) {
    return PresenceMobileDetectionAttempt(
      attemptUuid: (json['attempt_uuid'] ?? '').toString(),
      attemptIndex: json['attempt_index'] is num ? (json['attempt_index'] as num).toInt() : 0,
      status: (json['status'] ?? json['instant_detection_status'] ?? '').toString(),
      capturePhase: (json['capture_phase'] ?? '').toString(),
    );
  }
}

class PresenceMobileResult {
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

  const PresenceMobileResult({
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
  });

  bool get isTerminal => status == 'completed' || decision == 'granted' || decision == 'denied' || decision == 'failed';

  factory PresenceMobileResult.fromJson(Map<String, dynamic> json) {
    return PresenceMobileResult(
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
    );
  }
}

class PresenceMobileDetectionStatus {
  final String sessionUuid;
  final int latestAttemptIndex;
  final String instantDetectionStatus;
  final String presenceDecisionState;
  final String? instantDetectionRequestId;

  const PresenceMobileDetectionStatus({
    required this.sessionUuid,
    required this.latestAttemptIndex,
    required this.instantDetectionStatus,
    required this.presenceDecisionState,
    required this.instantDetectionRequestId,
  });

  bool get requiresRetry => presenceDecisionState == 'retry_required';
  bool get detectionCompleted => instantDetectionStatus == 'completed';

  factory PresenceMobileDetectionStatus.fromJson(Map<String, dynamic> json) {
    return PresenceMobileDetectionStatus(
      sessionUuid: (json['session_uuid'] ?? '').toString(),
      latestAttemptIndex: json['latest_attempt_index'] is num ? (json['latest_attempt_index'] as num).toInt() : 0,
      instantDetectionStatus: (json['instant_detection_status'] ?? '').toString(),
      presenceDecisionState: (json['presence_decision_state'] ?? '').toString(),
      instantDetectionRequestId: json['instant_detection_request_id']?.toString(),
    );
  }
}

class PresenceMobileQrPayload {
  final bool found;
  final String installationUuid;
  final String? deviceReference;
  final String? qrToken;
  final String? expiresAt;
  final String? sessionUuid;
  final String? sessionStatus;
  final String? qrStatus;
  final Map<String, dynamic>? payload;

  const PresenceMobileQrPayload({
    required this.found,
    required this.installationUuid,
    required this.deviceReference,
    required this.qrToken,
    required this.expiresAt,
    required this.sessionUuid,
    required this.sessionStatus,
    required this.qrStatus,
    required this.payload,
  });

  factory PresenceMobileQrPayload.fromJson(Map<String, dynamic> json) {
    return PresenceMobileQrPayload(
      found: json['found'] == true,
      installationUuid: (json['installation_uuid'] ?? '').toString(),
      deviceReference: json['device_reference']?.toString(),
      qrToken: json['qr_token']?.toString(),
      expiresAt: json['expires_at']?.toString(),
      sessionUuid: json['session_uuid']?.toString(),
      sessionStatus: json['session_status']?.toString(),
      qrStatus: json['qr_status']?.toString(),
      payload: json['payload'] is Map<String, dynamic> ? json['payload'] as Map<String, dynamic> : null,
    );
  }
}