import 'package:flutter/material.dart';
import 'package:json_annotation/json_annotation.dart';

part 'user_action_model.g.dart';

/// User-defined trigger action model
/// 
/// Represents a custom action that can be assigned to triggers.
/// Unlike system workflows (read-only), these are CRUD-able by users.
@JsonSerializable(explicitToJson: true)
class UserActionModel {
  final int id;
  final String uuid;
  final String name;
  final String? description;
  
  @JsonKey(name: 'action_type')
  final String actionType;
  
  @JsonKey(name: 'action_config')
  final String? actionConfig;
  
  @JsonKey(name: 'is_active')
  final bool isActive;
  
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  
  @JsonKey(name: 'created_by')
  final String? createdBy;

  UserActionModel({
    required this.id,
    required this.uuid,
    required this.name,
    this.description,
    required this.actionType,
    this.actionConfig,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
    this.createdBy,
  });

  factory UserActionModel.fromJson(Map<String, dynamic> json) =>
      _$UserActionModelFromJson(json);

  Map<String, dynamic> toJson() => _$UserActionModelToJson(this);

  UserActionModel copyWith({
    int? id,
    String? uuid,
    String? name,
    String? description,
    String? actionType,
    String? actionConfig,
    bool? isActive,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? createdBy,
  }) {
    return UserActionModel(
      id: id ?? this.id,
      uuid: uuid ?? this.uuid,
      name: name ?? this.name,
      description: description ?? this.description,
      actionType: actionType ?? this.actionType,
      actionConfig: actionConfig ?? this.actionConfig,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdBy: createdBy ?? this.createdBy,
    );
  }

  /// Get display name for action type
  String get actionTypeDisplay {
    switch (actionType) {
      case 'alert':
        return 'Alert';
      case 'email':
        return 'Email';
      case 'webhook':
        return 'Webhook';
      case 'log':
        return 'Log';
      case 'digital_signage':
        return 'Digital Signage';
      case 'messaging_app':
        return 'Messaging App';
      default:
        return actionType.toUpperCase();
    }
  }
  
  /// Get icon for action type
  IconData get actionTypeIcon {
    switch (actionType) {
      case 'alert':
        return Icons.notifications;
      case 'email':
        return Icons.email;
      case 'webhook':
        return Icons.webhook;
      case 'log':
        return Icons.description;
      case 'digital_signage':
        return Icons.smart_display;
      case 'messaging_app':
        return Icons.chat_bubble;
      default:
        return Icons.settings;
    }
  }
  
  /// Get color for action type
  Color get actionTypeColor {
    switch (actionType) {
      case 'alert':
        return Colors.orange;
      case 'email':
        return Colors.blue;
      case 'webhook':
        return Colors.purple;
      case 'log':
        return Colors.grey;
      case 'digital_signage':
        return Colors.green;
      case 'messaging_app':
        return Colors.teal;
      default:
        return Colors.white;
    }
  }
}

/// Request model for creating/updating user actions
@JsonSerializable(explicitToJson: true)
class UserActionCreateRequest {
  final String name;
  final String? description;
  
  @JsonKey(name: 'action_type')
  final String actionType;
  
  @JsonKey(name: 'action_config')
  final String? actionConfig;
  
  @JsonKey(name: 'is_active')
  final bool isActive;
  
  @JsonKey(name: 'created_by')
  final String? createdBy;

  UserActionCreateRequest({
    required this.name,
    this.description,
    required this.actionType,
    this.actionConfig,
    this.isActive = true,
    this.createdBy,
  });

  factory UserActionCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$UserActionCreateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$UserActionCreateRequestToJson(this);
}

/// Paginated list response
@JsonSerializable(explicitToJson: true)
class UserActionListResponse {
  final List<UserActionModel> actions;
  final int total;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  @JsonKey(name: 'total_pages')
  final int totalPages;

  UserActionListResponse({
    required this.actions,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  factory UserActionListResponse.fromJson(Map<String, dynamic> json) =>
      _$UserActionListResponseFromJson(json);

  Map<String, dynamic> toJson() => _$UserActionListResponseToJson(this);
}

/// Statistics response
@JsonSerializable(explicitToJson: true)
class UserActionStatsResponse {
  final int total;
  final int active;
  final int inactive;
  @JsonKey(name: 'by_type')
  final Map<String, int> byType;

  UserActionStatsResponse({
    required this.total,
    required this.active,
    required this.inactive,
    required this.byType,
  });

  factory UserActionStatsResponse.fromJson(Map<String, dynamic> json) =>
      _$UserActionStatsResponseFromJson(json);

  Map<String, dynamic> toJson() => _$UserActionStatsResponseToJson(this);
}
