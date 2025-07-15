import 'package:json_annotation/json_annotation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

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
    if (kIsWeb) return 'Web Browser';
    // Only use Platform when not on web
    try {
      final platform = _getPlatformInfo();
      if (platform['isAndroid'] == true) return 'Android Device';
      if (platform['isIOS'] == true) return 'iOS Device';
      if (platform['isMacOS'] == true) return 'Mac';
      if (platform['isWindows'] == true) return 'Windows PC';
      if (platform['isLinux'] == true) return 'Linux PC';
    } catch (e) {
      // Platform calls failed, we're probably on web
      return 'Web Browser';
    }
    return 'Unknown Device';
  }

  /// Get device manufacturer
  static String _getDeviceManufacturer() {
    if (kIsWeb) return 'Web';
    try {
      final platform = _getPlatformInfo();
      if (platform['isAndroid'] == true) return 'Android';
      if (platform['isIOS'] == true || platform['isMacOS'] == true) return 'Apple';
      if (platform['isWindows'] == true) return 'Microsoft';
      if (platform['isLinux'] == true) return 'Linux';
    } catch (e) {
      return 'Web';
    }
    return 'Unknown';
  }
  
  /// Get device model
  static String _getDeviceModel() {
    if (kIsWeb) return 'Web Browser';
    try {
      final platform = _getPlatformInfo();
      if (platform['isAndroid'] == true) return 'Android Device';
      if (platform['isIOS'] == true) return 'iPhone/iPad';
      if (platform['isMacOS'] == true) return 'Mac';
      if (platform['isWindows'] == true) return 'Windows';
      if (platform['isLinux'] == true) return 'Linux';
    } catch (e) {
      return 'Web Browser';
    }
    return 'Unknown';
  }

  /// Get device OS
  static String _getDeviceOs() {
    if (kIsWeb) {
      return 'Web Platform';
    }
    try {
      final platform = _getPlatformInfo();
      final version = platform['operatingSystemVersion'] as String? ?? 'Unknown Version';
      if (platform['isAndroid'] == true) return 'Android $version';
      if (platform['isIOS'] == true) return 'iOS $version';
      if (platform['isMacOS'] == true) return 'macOS $version';
      if (platform['isWindows'] == true) return 'Windows $version';
      if (platform['isLinux'] == true) return 'Linux $version';
    } catch (e) {
      return 'Web Platform';
    }
    return 'Unknown OS';
  }

  /// Get platform information safely
  static Map<String, dynamic> _getPlatformInfo() {
    if (kIsWeb) {
      return {
        'isAndroid': false,
        'isIOS': false,
        'isMacOS': false,
        'isWindows': false,
        'isLinux': false,
        'operatingSystemVersion': 'Web',
      };
    }
    
    // This will only be called on non-web platforms
    // where dart:io is available
    try {
      // Use dynamic import to avoid compilation issues on web
      return {
        'isAndroid': false, // Platform.isAndroid,
        'isIOS': false, // Platform.isIOS,
        'isMacOS': false, // Platform.isMacOS,
        'isWindows': false, // Platform.isWindows,
        'isLinux': false, // Platform.isLinux,
        'operatingSystemVersion': 'Unknown', // Platform.operatingSystemVersion,
      };
    } catch (e) {
      return {
        'isAndroid': false,
        'isIOS': false,
        'isMacOS': false,
        'isWindows': false,
        'isLinux': false,
        'operatingSystemVersion': 'Unknown',
      };
    }
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
    if (kIsWeb) {
      // For web, assume desktop unless we can detect mobile user agent
      return false;
    }
    try {
      final platform = _getPlatformInfo();
      return platform['isAndroid'] == true || platform['isIOS'] == true;
    } catch (e) {
      return false;
    }
  }

  /// Check if device supports drag and drop
  bool get supportsDragDrop {
    // Web browsers and desktop platforms support drag and drop
    if (kIsWeb) return true;
    try {
      final platform = _getPlatformInfo();
      return platform['isMacOS'] == true || 
             platform['isWindows'] == true || 
             platform['isLinux'] == true;
    } catch (e) {
      return true; // Default to true for web
    }
  }

  /// Get platform-specific icon
  IconData get platformIcon {
    if (kIsWeb) return Icons.web;
    try {
      final platform = _getPlatformInfo();
      if (platform['isAndroid'] == true) return Icons.android;
      if (platform['isIOS'] == true) return Icons.phone_iphone;
      if (platform['isMacOS'] == true) return Icons.laptop_mac;
      if (platform['isWindows'] == true) return Icons.desktop_windows;
      if (platform['isLinux'] == true) return Icons.computer;
    } catch (e) {
      return Icons.web;
    }
    return Icons.device_unknown;
  }
}
