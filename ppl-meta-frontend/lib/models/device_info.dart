import 'package:json_annotation/json_annotation.dart';
import 'package:flutter/material.dart';
import 'dart:io';

part 'device_info.g.dart';

/// Device information model for media uploads
@JsonSerializable()
class DeviceInfo {
  @JsonKey(name: 'device_name')
  final String deviceName;
  
  @JsonKey(name: 'device_manufacturer')
  final String deviceManufacturer;
  
  @JsonKey(name: 'device_model')
  final String deviceModel;
  
  @JsonKey(name: 'device_os')
  final String deviceOs;
  
  @JsonKey(name: 'app_name')
  final String appName;
  
  @JsonKey(name: 'app_version')
  final String appVersion;
  
  const DeviceInfo({
    required this.deviceName,
    required this.deviceManufacturer,
    required this.deviceModel,
    required this.deviceOs,
    required this.appName,
    required this.appVersion,
  });
  
  factory DeviceInfo.fromJson(Map<String, dynamic> json) => _$DeviceInfoFromJson(json);
  Map<String, dynamic> toJson() => _$DeviceInfoToJson(this);
  
  /// Create device info for current platform
  factory DeviceInfo.current() {
    return DeviceInfo(
      deviceName: _getDeviceName(),
      deviceManufacturer: _getDeviceManufacturer(),
      deviceModel: _getDeviceModel(),
      deviceOs: _getDeviceOs(),
      appName: 'PPL Meta Frontend',
      appVersion: '1.0.0',
    );
  }
  
  /// Get device name based on platform
  static String _getDeviceName() {
    if (Platform.isAndroid) return 'Android Device';
    if (Platform.isIOS) return 'iOS Device';
    if (Platform.isMacOS) return 'Mac';
    if (Platform.isWindows) return 'Windows PC';
    if (Platform.isLinux) return 'Linux PC';
    return 'Unknown Device';
  }
  
  /// Get device manufacturer
  static String _getDeviceManufacturer() {
    if (Platform.isAndroid) return 'Android';
    if (Platform.isIOS || Platform.isMacOS) return 'Apple';
    if (Platform.isWindows) return 'Microsoft';
    if (Platform.isLinux) return 'Linux';
    return 'Unknown';
  }
  
  /// Get device model
  static String _getDeviceModel() {
    if (Platform.isAndroid) return 'Android Device';
    if (Platform.isIOS) return 'iPhone/iPad';
    if (Platform.isMacOS) return 'Mac';
    if (Platform.isWindows) return 'Windows';
    if (Platform.isLinux) return 'Linux';
    return 'Unknown';
  }
  
  /// Get device OS
  static String _getDeviceOs() {
    if (Platform.isAndroid) return 'Android ${Platform.operatingSystemVersion}';
    if (Platform.isIOS) return 'iOS ${Platform.operatingSystemVersion}';
    if (Platform.isMacOS) return 'macOS ${Platform.operatingSystemVersion}';
    if (Platform.isWindows) return 'Windows ${Platform.operatingSystemVersion}';
    if (Platform.isLinux) return 'Linux ${Platform.operatingSystemVersion}';
    return 'Unknown OS';
  }
  
  /// Get display name for the device
  String get displayName {
    if (deviceManufacturer == 'Unknown' || deviceModel == 'Unknown') {
      return deviceName;
    }
    return '$deviceManufacturer $deviceModel';
  }
  
  /// Get short OS name
  String get shortOs {
    if (deviceOs.toLowerCase().contains('android')) return 'Android';
    if (deviceOs.toLowerCase().contains('ios')) return 'iOS';
    if (deviceOs.toLowerCase().contains('macos')) return 'macOS';
    if (deviceOs.toLowerCase().contains('windows')) return 'Windows';
    if (deviceOs.toLowerCase().contains('linux')) return 'Linux';
    return 'Unknown';
  }
  
  /// Check if device is mobile (Android or iOS)
  bool get isMobile {
    return Platform.isAndroid || Platform.isIOS;
  }
  
  /// Check if device supports drag and drop
  bool get supportsDragDrop {
    return Platform.isMacOS || Platform.isWindows || Platform.isLinux;
  }
  
  /// Get platform-specific icon
  IconData get platformIcon {
    if (Platform.isAndroid) return Icons.android;
    if (Platform.isIOS) return Icons.phone_iphone;
    if (Platform.isMacOS) return Icons.laptop_mac;
    if (Platform.isWindows) return Icons.desktop_windows;
    if (Platform.isLinux) return Icons.computer;
    return Icons.device_unknown;
  }
}
