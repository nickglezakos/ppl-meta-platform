/// Simple automation models for Phase 1 implementation
/// Using basic classes instead of Freezed for quick iteration

/// Automation rule model
class AutomationRule {
  final String id;
  final String name;
  final String description;
  final String triggerType;
  final List<String> actions;
  final bool isActive;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final DateTime? lastExecuted;
  final int executionCount;
  final double successRate;

  // Getter for compatibility with workflow widgets
  bool get isEnabled => isActive;

  const AutomationRule({
    required this.id,
    required this.name,
    required this.description,
    required this.triggerType,
    required this.actions,
    required this.isActive,
    required this.createdAt,
    this.updatedAt,
    this.lastExecuted,
    this.executionCount = 0,
    this.successRate = 0.0,
  });

  factory AutomationRule.fromJson(Map<String, dynamic> json) {
    return AutomationRule(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      triggerType: json['triggerType'] as String,
      actions: List<String>.from(json['actions'] as List),
      isActive: json['isActive'] as bool,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: json['updatedAt'] != null 
          ? DateTime.parse(json['updatedAt'] as String) 
          : null,
      lastExecuted: json['lastExecuted'] != null 
          ? DateTime.parse(json['lastExecuted'] as String) 
          : null,
      executionCount: json['executionCount'] as int? ?? 0,
      successRate: (json['successRate'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'triggerType': triggerType,
      'actions': actions,
      'isActive': isActive,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt?.toIso8601String(),
      'lastExecuted': lastExecuted?.toIso8601String(),
      'executionCount': executionCount,
      'successRate': successRate,
    };
  }
}

/// Automation execution record
class AutomationExecution {
  final String id;
  final String ruleId;
  final String ruleName;
  final DateTime startedAt;
  final DateTime? completedAt;
  final String status;
  final String? errorMessage;
  final Map<String, dynamic>? executionContext;

  // Getters for compatibility with workflow widgets
  DateTime get executedAt => startedAt;
  String get trigger => 'Automation trigger';
  String? get result => status == 'completed' ? 'Success' : errorMessage;
  Duration? get duration => completedAt?.difference(startedAt);

  const AutomationExecution({
    required this.id,
    required this.ruleId,
    required this.ruleName,
    required this.startedAt,
    this.completedAt,
    required this.status,
    this.errorMessage,
    this.executionContext,
  });

  factory AutomationExecution.fromJson(Map<String, dynamic> json) {
    return AutomationExecution(
      id: json['id'] as String,
      ruleId: json['ruleId'] as String,
      ruleName: json['ruleName'] as String,
      startedAt: DateTime.parse(json['startedAt'] as String),
      completedAt: json['completedAt'] != null 
          ? DateTime.parse(json['completedAt'] as String) 
          : null,
      status: json['status'] as String,
      errorMessage: json['errorMessage'] as String?,
      executionContext: json['executionContext'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'ruleId': ruleId,
      'ruleName': ruleName,
      'startedAt': startedAt.toIso8601String(),
      'completedAt': completedAt?.toIso8601String(),
      'status': status,
      'errorMessage': errorMessage,
      'executionContext': executionContext,
    };
  }
}

/// Automation metrics
class AutomationMetrics {
  final int activeRulesCount;
  final int executionsToday;
  final double successRate;
  final int totalExecutions;
  final DateTime? lastExecution;

  // Getters for compatibility with workflow widgets
  int get totalRules => totalExecutions > 0 ? (activeRulesCount * 2) : activeRulesCount;
  int get activeRules => activeRulesCount;

  const AutomationMetrics({
    required this.activeRulesCount,
    required this.executionsToday,
    required this.successRate,
    required this.totalExecutions,
    this.lastExecution,
  });

  factory AutomationMetrics.fromJson(Map<String, dynamic> json) {
    return AutomationMetrics(
      activeRulesCount: json['activeRulesCount'] as int,
      executionsToday: json['executionsToday'] as int,
      successRate: (json['successRate'] as num).toDouble(),
      totalExecutions: json['totalExecutions'] as int,
      lastExecution: json['lastExecution'] != null 
          ? DateTime.parse(json['lastExecution'] as String) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'activeRulesCount': activeRulesCount,
      'executionsToday': executionsToday,
      'successRate': successRate,
      'totalExecutions': totalExecutions,
      'lastExecution': lastExecution?.toIso8601String(),
    };
  }
}

/// Automation engine status
class AutomationEngineStatus {
  final bool isRunning;
  final String version;
  final DateTime? lastStartup;
  final int processedEvents;

  const AutomationEngineStatus({
    required this.isRunning,
    required this.version,
    this.lastStartup,
    required this.processedEvents,
  });

  factory AutomationEngineStatus.fromJson(Map<String, dynamic> json) {
    return AutomationEngineStatus(
      isRunning: json['isRunning'] as bool,
      version: json['version'] as String,
      lastStartup: json['lastStartup'] != null 
          ? DateTime.parse(json['lastStartup'] as String) 
          : null,
      processedEvents: json['processedEvents'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'isRunning': isRunning,
      'version': version,
      'lastStartup': lastStartup?.toIso8601String(),
      'processedEvents': processedEvents,
    };
  }
}

/// Real-time automation event
class AutomationEvent {
  final String id;
  final String type;
  final DateTime timestamp;
  final String? ruleId;
  final String? executionId;
  final Map<String, dynamic>? data;

  const AutomationEvent({
    required this.id,
    required this.type,
    required this.timestamp,
    this.ruleId,
    this.executionId,
    this.data,
  });

  factory AutomationEvent.fromJson(Map<String, dynamic> json) {
    return AutomationEvent(
      id: json['id'] as String,
      type: json['type'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      ruleId: json['ruleId'] as String?,
      executionId: json['executionId'] as String?,
      data: json['data'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'timestamp': timestamp.toIso8601String(),
      'ruleId': ruleId,
      'executionId': executionId,
      'data': data,
    };
  }
}