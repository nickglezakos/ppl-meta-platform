// Workflow Action Model for PPL Meta Platform
// Represents orchestrator workflows that can be executed from triggers

class WorkflowParameter {
  final String name;
  final String type;
  final String description;
  final bool required;
  final dynamic defaultValue;

  WorkflowParameter({
    required this.name,
    required this.type,
    required this.description,
    this.required = false,
    this.defaultValue,
  });

  factory WorkflowParameter.fromJson(Map<String, dynamic> json) {
    return WorkflowParameter(
      name: json['name'] as String,
      type: json['type'] as String,
      description: json['description'] as String,
      required: json['required'] as bool? ?? false,
      defaultValue: json['default'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'type': type,
      'description': description,
      'required': required,
      'default': defaultValue,
    };
  }
}

class WorkflowAction {
  final String id;
  final String name;
  final String description;
  final String category;
  final String workflowType;
  final bool isActive;
  final int executionCount;
  final double successRate;
  final double? averageDurationSeconds;
  final List<WorkflowParameter> parameters;
  final bool requiresAuth;
  final bool supportsBatch;
  final bool supportsRealtime;
  final String? createdAt;
  final String? updatedAt;

  WorkflowAction({
    required this.id,
    required this.name,
    required this.description,
    required this.category,
    required this.workflowType,
    this.isActive = true,
    this.executionCount = 0,
    this.successRate = 0.0,
    this.averageDurationSeconds,
    this.parameters = const [],
    this.requiresAuth = true,
    this.supportsBatch = false,
    this.supportsRealtime = false,
    this.createdAt,
    this.updatedAt,
  });

  factory WorkflowAction.fromJson(Map<String, dynamic> json) {
    return WorkflowAction(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      category: json['category'] as String,
      workflowType: json['workflow_type'] as String,
      isActive: json['is_active'] as bool? ?? true,
      executionCount: json['execution_count'] as int? ?? 0,
      successRate: (json['success_rate'] as num?)?.toDouble() ?? 0.0,
      averageDurationSeconds:
          (json['average_duration_seconds'] as num?)?.toDouble(),
      parameters: (json['parameters'] as List<dynamic>?)
              ?.map((p) => WorkflowParameter.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      requiresAuth: json['requires_auth'] as bool? ?? true,
      supportsBatch: json['supports_batch'] as bool? ?? false,
      supportsRealtime: json['supports_realtime'] as bool? ?? false,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'category': category,
      'workflow_type': workflowType,
      'is_active': isActive,
      'execution_count': executionCount,
      'success_rate': successRate,
      'average_duration_seconds': averageDurationSeconds,
      'parameters': parameters.map((p) => p.toJson()).toList(),
      'requires_auth': requiresAuth,
      'supports_batch': supportsBatch,
      'supports_realtime': supportsRealtime,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }

  WorkflowAction copyWith({
    String? id,
    String? name,
    String? description,
    String? category,
    String? workflowType,
    bool? isActive,
    int? executionCount,
    double? successRate,
    double? averageDurationSeconds,
    List<WorkflowParameter>? parameters,
    bool? requiresAuth,
    bool? supportsBatch,
    bool? supportsRealtime,
    String? createdAt,
    String? updatedAt,
  }) {
    return WorkflowAction(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      category: category ?? this.category,
      workflowType: workflowType ?? this.workflowType,
      isActive: isActive ?? this.isActive,
      executionCount: executionCount ?? this.executionCount,
      successRate: successRate ?? this.successRate,
      averageDurationSeconds:
          averageDurationSeconds ?? this.averageDurationSeconds,
      parameters: parameters ?? this.parameters,
      requiresAuth: requiresAuth ?? this.requiresAuth,
      supportsBatch: supportsBatch ?? this.supportsBatch,
      supportsRealtime: supportsRealtime ?? this.supportsRealtime,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
