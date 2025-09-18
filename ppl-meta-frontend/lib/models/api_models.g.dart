// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'api_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LoginRequest _$LoginRequestFromJson(Map<String, dynamic> json) => LoginRequest(
      username: json['username'] as String,
      password: json['password'] as String,
    );

Map<String, dynamic> _$LoginRequestToJson(LoginRequest instance) =>
    <String, dynamic>{
      'username': instance.username,
      'password': instance.password,
    };

AuthResponse _$AuthResponseFromJson(Map<String, dynamic> json) => AuthResponse(
      token: json['token'] as String,
      tokenType: json['tokenType'] as String,
      expiresIn: (json['expiresIn'] as num).toInt(),
      user: UserProfile.fromJson(json['user'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$AuthResponseToJson(AuthResponse instance) =>
    <String, dynamic>{
      'token': instance.token,
      'tokenType': instance.tokenType,
      'expiresIn': instance.expiresIn,
      'user': instance.user,
    };

UserProfile _$UserProfileFromJson(Map<String, dynamic> json) => UserProfile(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      roles: (json['roles'] as List<dynamic>).map((e) => e as String).toList(),
    );

Map<String, dynamic> _$UserProfileToJson(UserProfile instance) =>
    <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'email': instance.email,
      'roles': instance.roles,
    };

CameraDevice _$CameraDeviceFromJson(Map<String, dynamic> json) => CameraDevice(
      id: json['id'] as String,
      name: json['name'] as String,
      type: json['type'] as String,
      status: json['status'] as String,
      ipAddress: json['ipAddress'] as String?,
      streamUrl: json['streamUrl'] as String?,
      settings:
          CameraSettings.fromJson(json['settings'] as Map<String, dynamic>),
      lastSeen: DateTime.parse(json['lastSeen'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$CameraDeviceToJson(CameraDevice instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'type': instance.type,
      'status': instance.status,
      'ipAddress': instance.ipAddress,
      'streamUrl': instance.streamUrl,
      'settings': instance.settings,
      'lastSeen': instance.lastSeen.toIso8601String(),
      'metadata': instance.metadata,
    };

CameraSettings _$CameraSettingsFromJson(Map<String, dynamic> json) =>
    CameraSettings(
      resolution: json['resolution'] as String,
      frameRate: (json['frameRate'] as num).toInt(),
      format: json['format'] as String,
      quality: (json['quality'] as num).toInt(),
      autoExposure: json['autoExposure'] as bool,
      exposure: (json['exposure'] as num?)?.toInt(),
      autoWhiteBalance: json['autoWhiteBalance'] as bool,
      whiteBalance: json['whiteBalance'] as String?,
    );

Map<String, dynamic> _$CameraSettingsToJson(CameraSettings instance) =>
    <String, dynamic>{
      'resolution': instance.resolution,
      'frameRate': instance.frameRate,
      'format': instance.format,
      'quality': instance.quality,
      'autoExposure': instance.autoExposure,
      'exposure': instance.exposure,
      'autoWhiteBalance': instance.autoWhiteBalance,
      'whiteBalance': instance.whiteBalance,
    };

CameraUpdateRequest _$CameraUpdateRequestFromJson(Map<String, dynamic> json) =>
    CameraUpdateRequest(
      name: json['name'] as String?,
      settings: json['settings'] == null
          ? null
          : CameraSettings.fromJson(json['settings'] as Map<String, dynamic>),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$CameraUpdateRequestToJson(
        CameraUpdateRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'settings': instance.settings,
      'metadata': instance.metadata,
    };

RecordingRequest _$RecordingRequestFromJson(Map<String, dynamic> json) =>
    RecordingRequest(
      filename: json['filename'] as String?,
      duration: (json['duration'] as num?)?.toInt(),
      format: json['format'] as String?,
      settings: json['settings'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$RecordingRequestToJson(RecordingRequest instance) =>
    <String, dynamic>{
      'filename': instance.filename,
      'duration': instance.duration,
      'format': instance.format,
      'settings': instance.settings,
    };

RecordingSession _$RecordingSessionFromJson(Map<String, dynamic> json) =>
    RecordingSession(
      id: json['id'] as String,
      cameraId: json['cameraId'] as String,
      filename: json['filename'] as String,
      status: json['status'] as String,
      startTime: DateTime.parse(json['startTime'] as String),
      endTime: json['endTime'] == null
          ? null
          : DateTime.parse(json['endTime'] as String),
      duration: (json['duration'] as num?)?.toInt(),
      fileSize: (json['fileSize'] as num?)?.toInt(),
      format: json['format'] as String?,
    );

Map<String, dynamic> _$RecordingSessionToJson(RecordingSession instance) =>
    <String, dynamic>{
      'id': instance.id,
      'cameraId': instance.cameraId,
      'filename': instance.filename,
      'status': instance.status,
      'startTime': instance.startTime.toIso8601String(),
      'endTime': instance.endTime?.toIso8601String(),
      'duration': instance.duration,
      'fileSize': instance.fileSize,
      'format': instance.format,
    };

FaceDetectionRequest _$FaceDetectionRequestFromJson(
        Map<String, dynamic> json) =>
    FaceDetectionRequest(
      method: json['method'] as String?,
      confidenceThreshold: (json['confidenceThreshold'] as num?)?.toDouble(),
      saveResult: json['saveResult'] as bool?,
      options: json['options'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$FaceDetectionRequestToJson(
        FaceDetectionRequest instance) =>
    <String, dynamic>{
      'method': instance.method,
      'confidenceThreshold': instance.confidenceThreshold,
      'saveResult': instance.saveResult,
      'options': instance.options,
    };

FaceDetectionResult _$FaceDetectionResultFromJson(Map<String, dynamic> json) =>
    FaceDetectionResult(
      id: json['id'] as String,
      cameraId: json['cameraId'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      faces: (json['faces'] as List<dynamic>)
          .map((e) => DetectedFace.fromJson(e as Map<String, dynamic>))
          .toList(),
      imageUrl: json['imageUrl'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$FaceDetectionResultToJson(
        FaceDetectionResult instance) =>
    <String, dynamic>{
      'id': instance.id,
      'cameraId': instance.cameraId,
      'timestamp': instance.timestamp.toIso8601String(),
      'faces': instance.faces,
      'imageUrl': instance.imageUrl,
      'metadata': instance.metadata,
    };

DetectedFace _$DetectedFaceFromJson(Map<String, dynamic> json) => DetectedFace(
      boundingBox:
          FaceBox.fromJson(json['boundingBox'] as Map<String, dynamic>),
      confidence: (json['confidence'] as num).toDouble(),
      landmarks: json['landmarks'] as Map<String, dynamic>?,
      attributes: json['attributes'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$DetectedFaceToJson(DetectedFace instance) =>
    <String, dynamic>{
      'boundingBox': instance.boundingBox,
      'confidence': instance.confidence,
      'landmarks': instance.landmarks,
      'attributes': instance.attributes,
    };

FaceBox _$FaceBoxFromJson(Map<String, dynamic> json) => FaceBox(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      width: (json['width'] as num).toDouble(),
      height: (json['height'] as num).toDouble(),
    );

Map<String, dynamic> _$FaceBoxToJson(FaceBox instance) => <String, dynamic>{
      'x': instance.x,
      'y': instance.y,
      'width': instance.width,
      'height': instance.height,
    };

WorkflowTemplate _$WorkflowTemplateFromJson(Map<String, dynamic> json) =>
    WorkflowTemplate(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      steps: (json['steps'] as List<dynamic>)
          .map((e) => WorkflowStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      defaultParams: json['defaultParams'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['createdAt'] as String),
    );

Map<String, dynamic> _$WorkflowTemplateToJson(WorkflowTemplate instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'steps': instance.steps,
      'defaultParams': instance.defaultParams,
      'createdAt': instance.createdAt.toIso8601String(),
    };

WorkflowStep _$WorkflowStepFromJson(Map<String, dynamic> json) => WorkflowStep(
      id: json['id'] as String,
      type: json['type'] as String,
      name: json['name'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
      dependencies: (json['dependencies'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$WorkflowStepToJson(WorkflowStep instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'name': instance.name,
      'parameters': instance.parameters,
      'dependencies': instance.dependencies,
    };

WorkflowCreateRequest _$WorkflowCreateRequestFromJson(
        Map<String, dynamic> json) =>
    WorkflowCreateRequest(
      templateId: json['templateId'] as String,
      name: json['name'] as String?,
      parameters: json['parameters'] as Map<String, dynamic>?,
      scheduledTime: json['scheduledTime'] == null
          ? null
          : DateTime.parse(json['scheduledTime'] as String),
    );

Map<String, dynamic> _$WorkflowCreateRequestToJson(
        WorkflowCreateRequest instance) =>
    <String, dynamic>{
      'templateId': instance.templateId,
      'name': instance.name,
      'parameters': instance.parameters,
      'scheduledTime': instance.scheduledTime?.toIso8601String(),
    };

WorkflowExecution _$WorkflowExecutionFromJson(Map<String, dynamic> json) =>
    WorkflowExecution(
      id: json['id'] as String,
      templateId: json['templateId'] as String,
      name: json['name'] as String,
      status: $enumDecode(_$WorkflowStatusEnumMap, json['status']),
      createdAt: DateTime.parse(json['createdAt'] as String),
      startedAt: json['startedAt'] == null
          ? null
          : DateTime.parse(json['startedAt'] as String),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      steps: (json['steps'] as List<dynamic>)
          .map((e) => StepExecution.fromJson(e as Map<String, dynamic>))
          .toList(),
      result: json['result'] as Map<String, dynamic>?,
      error: json['error'] as String?,
    );

Map<String, dynamic> _$WorkflowExecutionToJson(WorkflowExecution instance) =>
    <String, dynamic>{
      'id': instance.id,
      'templateId': instance.templateId,
      'name': instance.name,
      'status': _$WorkflowStatusEnumMap[instance.status]!,
      'createdAt': instance.createdAt.toIso8601String(),
      'startedAt': instance.startedAt?.toIso8601String(),
      'completedAt': instance.completedAt?.toIso8601String(),
      'steps': instance.steps,
      'result': instance.result,
      'error': instance.error,
    };

const _$WorkflowStatusEnumMap = {
  WorkflowStatus.pending: 'pending',
  WorkflowStatus.running: 'running',
  WorkflowStatus.completed: 'completed',
  WorkflowStatus.failed: 'failed',
  WorkflowStatus.cancelled: 'cancelled',
};

StepExecution _$StepExecutionFromJson(Map<String, dynamic> json) =>
    StepExecution(
      id: json['id'] as String,
      stepId: json['stepId'] as String,
      name: json['name'] as String,
      status: $enumDecode(_$StepStatusEnumMap, json['status']),
      startedAt: json['startedAt'] == null
          ? null
          : DateTime.parse(json['startedAt'] as String),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      result: json['result'] as Map<String, dynamic>?,
      error: json['error'] as String?,
    );

Map<String, dynamic> _$StepExecutionToJson(StepExecution instance) =>
    <String, dynamic>{
      'id': instance.id,
      'stepId': instance.stepId,
      'name': instance.name,
      'status': _$StepStatusEnumMap[instance.status]!,
      'startedAt': instance.startedAt?.toIso8601String(),
      'completedAt': instance.completedAt?.toIso8601String(),
      'result': instance.result,
      'error': instance.error,
    };

const _$StepStatusEnumMap = {
  StepStatus.pending: 'pending',
  StepStatus.running: 'running',
  StepStatus.completed: 'completed',
  StepStatus.failed: 'failed',
  StepStatus.skipped: 'skipped',
};

AutomationRule _$AutomationRuleFromJson(Map<String, dynamic> json) =>
    AutomationRule(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      enabled: json['enabled'] as bool,
      trigger: RuleTrigger.fromJson(json['trigger'] as Map<String, dynamic>),
      conditions: (json['conditions'] as List<dynamic>)
          .map((e) => RuleCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      actions: (json['actions'] as List<dynamic>)
          .map((e) => RuleAction.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['createdAt'] as String),
      lastExecuted: json['lastExecuted'] == null
          ? null
          : DateTime.parse(json['lastExecuted'] as String),
      executionCount: (json['executionCount'] as num).toInt(),
    );

Map<String, dynamic> _$AutomationRuleToJson(AutomationRule instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'enabled': instance.enabled,
      'trigger': instance.trigger,
      'conditions': instance.conditions,
      'actions': instance.actions,
      'createdAt': instance.createdAt.toIso8601String(),
      'lastExecuted': instance.lastExecuted?.toIso8601String(),
      'executionCount': instance.executionCount,
    };

RuleTrigger _$RuleTriggerFromJson(Map<String, dynamic> json) => RuleTrigger(
      type: json['type'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$RuleTriggerToJson(RuleTrigger instance) =>
    <String, dynamic>{
      'type': instance.type,
      'parameters': instance.parameters,
    };

RuleCondition _$RuleConditionFromJson(Map<String, dynamic> json) =>
    RuleCondition(
      type: json['type'] as String,
      operator: json['operator'] as String,
      value: json['value'],
      parameters: json['parameters'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$RuleConditionToJson(RuleCondition instance) =>
    <String, dynamic>{
      'type': instance.type,
      'operator': instance.operator,
      'value': instance.value,
      'parameters': instance.parameters,
    };

RuleAction _$RuleActionFromJson(Map<String, dynamic> json) => RuleAction(
      type: json['type'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$RuleActionToJson(RuleAction instance) =>
    <String, dynamic>{
      'type': instance.type,
      'parameters': instance.parameters,
    };

AutomationRuleCreateRequest _$AutomationRuleCreateRequestFromJson(
        Map<String, dynamic> json) =>
    AutomationRuleCreateRequest(
      name: json['name'] as String,
      description: json['description'] as String,
      enabled: json['enabled'] as bool,
      trigger: RuleTrigger.fromJson(json['trigger'] as Map<String, dynamic>),
      conditions: (json['conditions'] as List<dynamic>)
          .map((e) => RuleCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      actions: (json['actions'] as List<dynamic>)
          .map((e) => RuleAction.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$AutomationRuleCreateRequestToJson(
        AutomationRuleCreateRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'enabled': instance.enabled,
      'trigger': instance.trigger,
      'conditions': instance.conditions,
      'actions': instance.actions,
    };

AutomationRuleUpdateRequest _$AutomationRuleUpdateRequestFromJson(
        Map<String, dynamic> json) =>
    AutomationRuleUpdateRequest(
      name: json['name'] as String?,
      description: json['description'] as String?,
      enabled: json['enabled'] as bool?,
      trigger: json['trigger'] == null
          ? null
          : RuleTrigger.fromJson(json['trigger'] as Map<String, dynamic>),
      conditions: (json['conditions'] as List<dynamic>?)
          ?.map((e) => RuleCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      actions: (json['actions'] as List<dynamic>?)
          ?.map((e) => RuleAction.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$AutomationRuleUpdateRequestToJson(
        AutomationRuleUpdateRequest instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'enabled': instance.enabled,
      'trigger': instance.trigger,
      'conditions': instance.conditions,
      'actions': instance.actions,
    };

AutomationExecution _$AutomationExecutionFromJson(Map<String, dynamic> json) =>
    AutomationExecution(
      id: json['id'] as String,
      ruleId: json['ruleId'] as String,
      ruleName: json['ruleName'] as String,
      executedAt: DateTime.parse(json['executedAt'] as String),
      successful: json['successful'] as bool,
      error: json['error'] as String?,
      result: json['result'] as Map<String, dynamic>?,
      duration: Duration(microseconds: (json['duration'] as num).toInt()),
    );

Map<String, dynamic> _$AutomationExecutionToJson(
        AutomationExecution instance) =>
    <String, dynamic>{
      'id': instance.id,
      'ruleId': instance.ruleId,
      'ruleName': instance.ruleName,
      'executedAt': instance.executedAt.toIso8601String(),
      'successful': instance.successful,
      'error': instance.error,
      'result': instance.result,
      'duration': instance.duration.inMicroseconds,
    };

AnalyticsOverview _$AnalyticsOverviewFromJson(Map<String, dynamic> json) =>
    AnalyticsOverview(
      totalDetections: (json['totalDetections'] as num).toInt(),
      totalCameras: (json['totalCameras'] as num).toInt(),
      activeWorkflows: (json['activeWorkflows'] as num).toInt(),
      automationRules: (json['automationRules'] as num).toInt(),
      avgConfidence: (json['avgConfidence'] as num).toDouble(),
      periodStart: DateTime.parse(json['periodStart'] as String),
      periodEnd: DateTime.parse(json['periodEnd'] as String),
    );

Map<String, dynamic> _$AnalyticsOverviewToJson(AnalyticsOverview instance) =>
    <String, dynamic>{
      'totalDetections': instance.totalDetections,
      'totalCameras': instance.totalCameras,
      'activeWorkflows': instance.activeWorkflows,
      'automationRules': instance.automationRules,
      'avgConfidence': instance.avgConfidence,
      'periodStart': instance.periodStart.toIso8601String(),
      'periodEnd': instance.periodEnd.toIso8601String(),
    };

DetectionTrend _$DetectionTrendFromJson(Map<String, dynamic> json) =>
    DetectionTrend(
      timestamp: DateTime.parse(json['timestamp'] as String),
      detectionCount: (json['detectionCount'] as num).toInt(),
      avgConfidence: (json['avgConfidence'] as num).toDouble(),
      cameraId: json['cameraId'] as String?,
    );

Map<String, dynamic> _$DetectionTrendToJson(DetectionTrend instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp.toIso8601String(),
      'detectionCount': instance.detectionCount,
      'avgConfidence': instance.avgConfidence,
      'cameraId': instance.cameraId,
    };

SystemMetrics _$SystemMetricsFromJson(Map<String, dynamic> json) =>
    SystemMetrics(
      cpuUsage: (json['cpuUsage'] as num).toDouble(),
      memoryUsage: (json['memoryUsage'] as num).toDouble(),
      diskUsage: (json['diskUsage'] as num).toDouble(),
      queueLength: (json['queueLength'] as num).toInt(),
      avgProcessingTime: (json['avgProcessingTime'] as num).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] as String),
    );

Map<String, dynamic> _$SystemMetricsToJson(SystemMetrics instance) =>
    <String, dynamic>{
      'cpuUsage': instance.cpuUsage,
      'memoryUsage': instance.memoryUsage,
      'diskUsage': instance.diskUsage,
      'queueLength': instance.queueLength,
      'avgProcessingTime': instance.avgProcessingTime,
      'timestamp': instance.timestamp.toIso8601String(),
    };

HealthStatus _$HealthStatusFromJson(Map<String, dynamic> json) => HealthStatus(
      status: json['status'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      services: (json['services'] as Map<String, dynamic>).map(
        (k, e) =>
            MapEntry(k, ServiceHealth.fromJson(e as Map<String, dynamic>)),
      ),
    );

Map<String, dynamic> _$HealthStatusToJson(HealthStatus instance) =>
    <String, dynamic>{
      'status': instance.status,
      'timestamp': instance.timestamp.toIso8601String(),
      'services': instance.services,
    };

ServiceHealth _$ServiceHealthFromJson(Map<String, dynamic> json) =>
    ServiceHealth(
      status: json['status'] as String,
      message: json['message'] as String?,
      lastCheck: json['lastCheck'] == null
          ? null
          : DateTime.parse(json['lastCheck'] as String),
    );

Map<String, dynamic> _$ServiceHealthToJson(ServiceHealth instance) =>
    <String, dynamic>{
      'status': instance.status,
      'message': instance.message,
      'lastCheck': instance.lastCheck?.toIso8601String(),
    };
