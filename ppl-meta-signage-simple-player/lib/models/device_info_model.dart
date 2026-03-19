import 'package:json_annotation/json_annotation.dart';

part 'device_info_model.g.dart';

/// Device information model
@JsonSerializable()
class DeviceInfoModel {
  @JsonKey(name: 'device_id')
  final String deviceId;
  @JsonKey(name: 'device_name')
  final String deviceName;
  @JsonKey(name: 'platform')
  final String platform;
  @JsonKey(name: 'platform_version')
  final String platformVersion;
  @JsonKey(name: 'app_version')
  final String appVersion;
  @JsonKey(name: 'screen_width')
  final int screenWidth;
  @JsonKey(name: 'screen_height')
  final int screenHeight;
  final List<String> capabilities;
  @JsonKey(name: 'max_video_resolution')
  final String maxVideoResolution;
  @JsonKey(name: 'supported_codecs')
  final List<String> supportedCodecs;

  DeviceInfoModel({
    required this.deviceId,
    required this.deviceName,
    required this.platform,
    required this.platformVersion,
    required this.appVersion,
    required this.screenWidth,
    required this.screenHeight,
    required this.capabilities,
    required this.maxVideoResolution,
    required this.supportedCodecs,
  });

  factory DeviceInfoModel.fromJson(Map<String, dynamic> json) =>
      _$DeviceInfoModelFromJson(json);

  Map<String, dynamic> toJson() => _$DeviceInfoModelToJson(this);
}

/// Service registration model
@JsonSerializable()
class ServiceRegistration {
  final String name;
  @JsonKey(name: 'service_type')
  final String serviceType;
  final String host;
  final int port;
  final Map<String, dynamic> metadata;
  @JsonKey(name: 'health_check_endpoint')
  final String healthCheckEndpoint;
  final String version;

  ServiceRegistration({
    required this.name,
    required this.serviceType,
    required this.host,
    required this.port,
    required this.metadata,
    this.healthCheckEndpoint = '/health',
    required this.version,
  });

  factory ServiceRegistration.fromJson(Map<String, dynamic> json) =>
      _$ServiceRegistrationFromJson(json);

  Map<String, dynamic> toJson() => _$ServiceRegistrationToJson(this);
}
