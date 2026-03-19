import 'package:device_info_plus/device_info_plus.dart';
import 'package:uuid/uuid.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../models/device_info_model.dart';
import '../config/app_config.dart';

// Platform-specific imports
import 'dart:io' if (dart.library.html) 'platform_stub.dart';

/// Helper class to gather device information
class DeviceInfoHelper {
  static final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();
  static String? _cachedDeviceId;

  /// Get unique device ID
  static Future<String> getDeviceId() async {
    if (_cachedDeviceId != null) return _cachedDeviceId!;

    try {
      if (kIsWeb) {
        // For web, use browser info or generate UUID
        final webInfo = await _deviceInfo.webBrowserInfo;
        _cachedDeviceId = 'web-${webInfo.userAgent?.hashCode ?? const Uuid().v4()}';
      } else if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        _cachedDeviceId = 'android-${androidInfo.id}';
      } else if (Platform.isMacOS) {
        final macInfo = await _deviceInfo.macOsInfo;
        _cachedDeviceId = 'macos-${macInfo.systemGUID ?? const Uuid().v4()}';
      } else if (Platform.isIOS) {
        final iosInfo = await _deviceInfo.iosInfo;
        _cachedDeviceId = 'ios-${iosInfo.identifierForVendor ?? const Uuid().v4()}';
      } else {
        _cachedDeviceId = 'unknown-${const Uuid().v4()}';
      }
    } catch (e) {
      _cachedDeviceId = 'fallback-${const Uuid().v4()}';
    }

    return _cachedDeviceId!;
  }

  /// Get complete device information
  static Future<DeviceInfoModel> getDeviceInfo() async {
    final deviceId = await getDeviceId();
    
    try {
      if (kIsWeb) {
        final webInfo = await _deviceInfo.webBrowserInfo;
        return DeviceInfoModel(
          deviceId: deviceId,
          deviceName: 'Web Browser - ${webInfo.browserName}',
          platform: 'web',
          platformVersion: webInfo.platform ?? 'unknown',
          appVersion: AppConfig.version,
          screenWidth: 1920, // Web default, can be updated from window
          screenHeight: 1080,
          capabilities: AppConfig.capabilities,
          maxVideoResolution: AppConfig.maxVideoResolution,
          supportedCodecs: AppConfig.supportedCodecs,
        );
      } else if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        return DeviceInfoModel(
          deviceId: deviceId,
          deviceName: '${androidInfo.brand} ${androidInfo.model}',
          platform: 'android',
          platformVersion: 'Android ${androidInfo.version.release}',
          appVersion: AppConfig.version,
          screenWidth: 1920,
          screenHeight: 1080,
          capabilities: AppConfig.capabilities,
          maxVideoResolution: AppConfig.maxVideoResolution,
          supportedCodecs: AppConfig.supportedCodecs,
        );
      } else if (Platform.isMacOS) {
        final macInfo = await _deviceInfo.macOsInfo;
        return DeviceInfoModel(
          deviceId: deviceId,
          deviceName: macInfo.computerName,
          platform: 'macos',
          platformVersion: 'macOS ${macInfo.osRelease}',
          appVersion: AppConfig.version,
          screenWidth: 1920,
          screenHeight: 1080,
          capabilities: AppConfig.capabilities,
          maxVideoResolution: AppConfig.maxVideoResolution,
          supportedCodecs: AppConfig.supportedCodecs,
        );
      } else {
        return DeviceInfoModel(
          deviceId: deviceId,
          deviceName: 'Unknown Device',
          platform: 'unknown',
          platformVersion: 'unknown',
          appVersion: AppConfig.version,
          screenWidth: 1920,
          screenHeight: 1080,
          capabilities: AppConfig.capabilities,
          maxVideoResolution: AppConfig.maxVideoResolution,
          supportedCodecs: AppConfig.supportedCodecs,
        );
      }
    } catch (e) {
      // Fallback device info
      return DeviceInfoModel(
        deviceId: deviceId,
        deviceName: 'Signage Device',
        platform: 'unknown',
        platformVersion: 'unknown',
        appVersion: AppConfig.version,
        screenWidth: 1920,
        screenHeight: 1080,
        capabilities: AppConfig.capabilities,
        maxVideoResolution: AppConfig.maxVideoResolution,
        supportedCodecs: AppConfig.supportedCodecs,
      );
    }
  }

  /// Get local IP address (best effort)
  /// Prioritizes Tailscale IPs (100.x.x.x) over subnet routes (10.x.x.x)
  static Future<String> getLocalIpAddress() async {
    try {
      if (kIsWeb) {
        return 'localhost'; // Web uses localhost
      }
      
      // For native platforms, try to get network interfaces
      if (!kIsWeb) {
        final interfaces = await NetworkInterface.list();
        String? tailscaleIp; // Prefer 100.x.x.x (direct Tailscale IP)
        String? fallbackIp; // Fallback to first non-loopback IPv4
        
        for (var interface in interfaces) {
          for (var addr in interface.addresses) {
            if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
              // Check if this is a Tailscale direct IP (100.x.x.x)
              if (addr.address.startsWith('100.')) {
                return addr.address; // Found Tailscale IP, use it immediately
              }
              // Save first non-loopback as fallback
              if (fallbackIp == null) {
                fallbackIp = addr.address;
              }
            }
          }
        }
        
        // Return fallback if Tailscale IP not found
        if (fallbackIp != null) {
          return fallbackIp;
        }
      }
      return '127.0.0.1';
    } catch (e) {
      return '127.0.0.1';
    }
  }
}
