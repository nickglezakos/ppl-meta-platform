import 'package:json_annotation/json_annotation.dart';

part 'communication_log_model.g.dart';

/// Communication log model for tracking all communications sent via triggers
@JsonSerializable(explicitToJson: true)
class CommunicationLog {
  final int id;
  final String uuid;
  
  @JsonKey(name: 'type')
  final String communicationType;
  
  final String status;
  final String recipient;
  
  @JsonKey(name: 'subject')
  final String? subjectLine;
  
  final String? content;
  final Map<String, dynamic>? payload;
  
  @JsonKey(name: 'triggered_by')
  final String? triggeredBy;
  
  @JsonKey(name: 'trigger_type')
  final String? triggerType;
  
  @JsonKey(name: 'trigger_id')
  final String? triggerId;
  
  @JsonKey(name: 'installation_id')
  final String? installationId;
  
  @JsonKey(name: 'tenant_name')
  final String? tenantName;
  
  final int attempts;
  
  @JsonKey(name: 'last_attempt_at')
  final String? lastAttemptAt;
  
  @JsonKey(name: 'delivered_at')
  final String? deliveredAt;
  
  @JsonKey(name: 'failed_at')
  final String? failedAt;
  
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  
  @JsonKey(name: 'response_status_code')
  final int? responseStatusCode;
  
  @JsonKey(name: 'response_body')
  final String? responseBody;
  
  @JsonKey(name: 'created_at')
  final String createdAt;
  
  @JsonKey(name: 'updated_at')
  final String updatedAt;

  CommunicationLog({
    required this.id,
    required this.uuid,
    required this.communicationType,
    required this.status,
    required this.recipient,
    this.subjectLine,
    this.content,
    this.payload,
    this.triggeredBy,
    this.triggerType,
    this.triggerId,
    this.installationId,
    this.tenantName,
    required this.attempts,
    this.lastAttemptAt,
    this.deliveredAt,
    this.failedAt,
    this.errorMessage,
    this.responseStatusCode,
    this.responseBody,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CommunicationLog.fromJson(Map<String, dynamic> json) =>
      _$CommunicationLogFromJson(json);

  Map<String, dynamic> toJson() => _$CommunicationLogToJson(this);
  
  /// Get color for communication type
  String get typeColor {
    switch (communicationType.toLowerCase()) {
      case 'email':
        return '#4CAF50';
      case 'webhook':
        return '#2196F3';
      case 'audit':
      case 'audit_log':
        return '#FF9800';
      case 'push_notification':
        return '#9C27B0';
      case 'sms':
        return '#009688';
      default:
        return '#9E9E9E';
    }
  }
  
  /// Get icon name for communication type
  String get typeIcon {
    switch (communicationType.toLowerCase()) {
      case 'email':
        return 'mail';
      case 'webhook':
        return 'webhook';
      case 'audit':
      case 'audit_log':
        return 'article';
      case 'push_notification':
        return 'notifications';
      case 'sms':
        return 'sms';
      default:
        return 'info';
    }
  }
  
  /// Get color for status
  String get statusColor {
    switch (status.toLowerCase()) {
      case 'sent':
      case 'delivered':
        return '#4CAF50';
      case 'pending':
        return '#FF9800';
      case 'failed':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  }
}

/// Response model for paginated communication logs
@JsonSerializable(explicitToJson: true)
class CommunicationLogListResponse {
  final int total;
  
  @JsonKey(name: 'page')
  final int currentPage;
  
  @JsonKey(name: 'page_size')
  final int pageSize;
  
  @JsonKey(name: 'total_pages')
  final int totalPages;
  
  final List<CommunicationLog> logs;

  CommunicationLogListResponse({
    required this.total,
    required this.currentPage,
    required this.pageSize,
    required this.totalPages,
    required this.logs,
  });

  factory CommunicationLogListResponse.fromJson(Map<String, dynamic> json) =>
      _$CommunicationLogListResponseFromJson(json);

  Map<String, dynamic> toJson() => _$CommunicationLogListResponseToJson(this);
}
