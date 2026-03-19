// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_info_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DeviceInfoModel _$DeviceInfoModelFromJson(Map<String, dynamic> json) =>
    DeviceInfoModel(
      deviceId: json['device_id'] as String,
      deviceName: json['device_name'] as String,
      platform: json['platform'] as String,
      platformVersion: json['platform_version'] as String,
      appVersion: json['app_version'] as String,
      screenWidth: (json['screen_width'] as num).toInt(),
      screenHeight: (json['screen_height'] as num).toInt(),
      capabilities: (json['capabilities'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      maxVideoResolution: json['max_video_resolution'] as String,
      supportedCodecs: (json['supported_codecs'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$DeviceInfoModelToJson(DeviceInfoModel instance) =>
    <String, dynamic>{
      'device_id': instance.deviceId,
      'device_name': instance.deviceName,
      'platform': instance.platform,
      'platform_version': instance.platformVersion,
      'app_version': instance.appVersion,
      'screen_width': instance.screenWidth,
      'screen_height': instance.screenHeight,
      'capabilities': instance.capabilities,
      'max_video_resolution': instance.maxVideoResolution,
      'supported_codecs': instance.supportedCodecs,
    };

ServiceRegistration _$ServiceRegistrationFromJson(Map<String, dynamic> json) =>
    ServiceRegistration(
      name: json['name'] as String,
      serviceType: json['service_type'] as String,
      host: json['host'] as String,
      port: (json['port'] as num).toInt(),
      metadata: json['metadata'] as Map<String, dynamic>,
      healthCheckEndpoint:
          json['health_check_endpoint'] as String? ?? '/health',
      version: json['version'] as String,
    );

Map<String, dynamic> _$ServiceRegistrationToJson(
  ServiceRegistration instance,
) => <String, dynamic>{
  'name': instance.name,
  'service_type': instance.serviceType,
  'host': instance.host,
  'port': instance.port,
  'metadata': instance.metadata,
  'health_check_endpoint': instance.healthCheckEndpoint,
  'version': instance.version,
};
