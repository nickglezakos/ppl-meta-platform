// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_action_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserActionModel _$UserActionModelFromJson(Map<String, dynamic> json) =>
    UserActionModel(
      id: (json['id'] as num).toInt(),
      uuid: json['uuid'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      actionType: json['action_type'] as String,
      actionConfig: json['action_config'] as String?,
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      createdBy: json['created_by'] as String?,
    );

Map<String, dynamic> _$UserActionModelToJson(UserActionModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'uuid': instance.uuid,
      'name': instance.name,
      'description': instance.description,
      'action_type': instance.actionType,
      'action_config': instance.actionConfig,
      'is_active': instance.isActive,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'created_by': instance.createdBy,
    };

UserActionCreateRequest _$UserActionCreateRequestFromJson(
        Map<String, dynamic> json) =>
    UserActionCreateRequest(
      name: json['name'] as String,
      description: json['description'] as String?,
      actionType: json['action_type'] as String,
      actionConfig: json['action_config'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      createdBy: json['created_by'] as String?,
    );

Map<String, dynamic> _$UserActionCreateRequestToJson(
        UserActionCreateRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'action_type': instance.actionType,
      'action_config': instance.actionConfig,
      'is_active': instance.isActive,
      'created_by': instance.createdBy,
    };

UserActionListResponse _$UserActionListResponseFromJson(
        Map<String, dynamic> json) =>
    UserActionListResponse(
      actions: (json['actions'] as List<dynamic>)
          .map((e) => UserActionModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
    );

Map<String, dynamic> _$UserActionListResponseToJson(
        UserActionListResponse instance) =>
    <String, dynamic>{
      'actions': instance.actions.map((e) => e.toJson()).toList(),
      'total': instance.total,
      'page': instance.page,
      'page_size': instance.pageSize,
      'total_pages': instance.totalPages,
    };

UserActionStatsResponse _$UserActionStatsResponseFromJson(
        Map<String, dynamic> json) =>
    UserActionStatsResponse(
      total: (json['total'] as num).toInt(),
      active: (json['active'] as num).toInt(),
      inactive: (json['inactive'] as num).toInt(),
      byType: Map<String, int>.from(json['by_type'] as Map),
    );

Map<String, dynamic> _$UserActionStatsResponseToJson(
        UserActionStatsResponse instance) =>
    <String, dynamic>{
      'total': instance.total,
      'active': instance.active,
      'inactive': instance.inactive,
      'by_type': instance.byType,
    };
