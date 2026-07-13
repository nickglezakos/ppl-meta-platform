import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

const String _channelId = 'eyenet_vpn_channel';
const String _channelName = 'EyeNet VPN';
const String _channelDescription = 'Persistent notification while VPN is connected';

final FlutterLocalNotificationsPlugin _notificationsPlugin =
    FlutterLocalNotificationsPlugin();

/// Initializes and controls the Android foreground service that keeps
/// the EyeNet VPN app alive in the background.
///
/// Without a foreground service, Android kills the Flutter app process
/// within minutes of the user leaving the app, even though the Tailscale
/// system VPN tunnel itself survives at the OS level.
class VpnBackgroundService {
  /// Call once at app startup (before runApp).
  static Future<void> init() async {
    // Create the notification channel BEFORE the foreground service starts.
    // Android requires the channel to exist before calling startForeground().
    const androidChannel = AndroidNotificationChannel(
      _channelId,
      _channelName,
      description: _channelDescription,
      importance: Importance.low,
    );
    final platform = _notificationsPlugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await platform?.createNotificationChannel(androidChannel);

    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _notificationsPlugin.initialize(initSettings);
  }

  /// Start the foreground service with an "VPN Connected" notification.
  /// Call after a successful VPN connection.
  static Future<void> start({String? vpnIp}) async {
    final service = FlutterBackgroundService();
    final ipText = vpnIp ?? 'Connected';

    await service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: _vpnBackgroundEntryPoint,
        autoStart: false,
        isForegroundMode: true,
        notificationChannelId: _channelId,
        initialNotificationTitle: 'EyeNet VPN',
        initialNotificationContent: ipText,
        foregroundServiceNotificationId: 8721,
        foregroundServiceTypes: [AndroidForegroundType.specialUse],
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
      ),
    );

    await service.startService();
  }

  /// Update the notification text with the current VPN IP.
  static Future<void> updateNotification(String text) async {
    final service = FlutterBackgroundService();
    service.invoke('updateNotification', {'content': text});
  }

  /// Stop the foreground service and dismiss the notification.
  /// Call when VPN disconnects.
  static Future<void> stop() async {
    final service = FlutterBackgroundService();
    service.invoke('stopService');
  }
}

/// Top-level entry point for the Android foreground service.
///
/// Must be a top-level function (not a class method) with @pragma so the
/// Dart AOT compiler doesn't tree-shake it in release builds.
@pragma('vm:entry-point')
Future<void> _vpnBackgroundEntryPoint(ServiceInstance service) async {
  const androidDetails = AndroidNotificationDetails(
    _channelId,
    _channelName,
    channelDescription: _channelDescription,
    importance: Importance.low,
    priority: Priority.low,
    ongoing: true,
    autoCancel: false,
    showWhen: false,
    icon: '@mipmap/ic_launcher',
  );
  const notificationDetails = NotificationDetails(android: androidDetails);

  service.on('updateNotification').listen((event) {
    if (event is Map<String, dynamic>) {
      final content = event['content'] as String? ?? 'Connected';
      _notificationsPlugin.show(
        8721,
        'EyeNet VPN',
        content,
        notificationDetails,
      );
    }
  });

  service.on('stopService').listen((event) {
    service.stopSelf();
  });

  // Show initial notification
  if (service is AndroidServiceInstance) {
    service.setAsForegroundService();
  }
}