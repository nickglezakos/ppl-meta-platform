// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'communication_log_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CommunicationLog _$CommunicationLogFromJson(Map<String, dynamic> json) =>
    CommunicationLog(
      id: (json['id'] as num).toInt(),
      uuid: json['uuid'] as String,
      communicationType: json['type'] as String,
      status: json['status'] as String,
      recipient: json['recipient'] as String,
      subjectLine: json['subject'] as String?,
      content: json['content'] as String?,
      payload: json['payload'] as Map<String, dynamic>?,
      triggeredBy: json['triggered_by'] as String?,
      triggerType: json['trigger_type'] as String?,
      triggerId: json['trigger_id'] as String?,
      installationId: json['installation_id'] as String?,
      tenantName: json['tenant_name'] as String?,
      attempts: (json['attempts'] as num).toInt(),
      lastAttemptAt: json['last_attempt_at'] as String?,
      deliveredAt: json['delivered_at'] as String?,
      failedAt: json['failed_at'] as String?,
      errorMessage: json['error_message'] as String?,
      responseStatusCode: (json['response_status_code'] as num?)?.toInt(),
      responseBody: json['response_body'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );

Map<String, dynamic> _$CommunicationLogToJson(CommunicationLog instance) =>
    <String, dynamic>{
      'id': instance.id,
      'uuid': instance.uuid,
      'type': instance.communicationType,
      'status': instance.status,
      'recipient': instance.recipient,
      'subject': instance.subjectLine,
      'content': instance.content,
      'payload': instance.payload,
      'triggered_by': instance.triggeredBy,
      'trigger_type': instance.triggerType,
      'trigger_id': instance.triggerId,
      'installation_id': instance.installationId,
      'tenant_name': instance.tenantName,
      'attempts': instance.attempts,
      'last_attempt_at': instance.lastAttemptAt,
      'delivered_at': instance.deliveredAt,
      'failed_at': instance.failedAt,
      'error_message': instance.errorMessage,
      'response_status_code': instance.responseStatusCode,
      'response_body': instance.responseBody,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

CommunicationLogListResponse _$CommunicationLogListResponseFromJson(
        Map<String, dynamic> json) =>
    CommunicationLogListResponse(
      total: (json['total'] as num).toInt(),
      currentPage: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
      logs: (json['logs'] as List<dynamic>)
          .map((e) => CommunicationLog.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$CommunicationLogListResponseToJson(
        CommunicationLogListResponse instance) =>
    <String, dynamic>{
      'total': instance.total,
      'page': instance.currentPage,
      'page_size': instance.pageSize,
      'total_pages': instance.totalPages,
      'logs': instance.logs.map((e) => e.toJson()).toList(),
    };
