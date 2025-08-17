// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_info.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DeviceInfo _$DeviceInfoFromJson(Map<String, dynamic> json) => DeviceInfo(
      deviceName: json['device_name'] as String,
      deviceManufacturer: json['device_manufacturer'] as String,
      deviceModel: json['device_model'] as String,
      deviceOs: json['device_os'] as String,
      appName: json['app_name'] as String,
      appVersion: json['app_version'] as String,
    );

Map<String, dynamic> _$DeviceInfoToJson(DeviceInfo instance) =>
    <String, dynamic>{
      'device_name': instance.deviceName,
      'device_manufacturer': instance.deviceManufacturer,
      'device_model': instance.deviceModel,
      'device_os': instance.deviceOs,
      'app_name': instance.appName,
      'app_version': instance.appVersion,
    };
