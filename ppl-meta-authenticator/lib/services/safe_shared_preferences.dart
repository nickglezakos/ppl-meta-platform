import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// SharedPreferences access with retries + clear errors for sideload devices.
///
/// Some Android installs briefly report MissingPluginException right after
/// cold start; a failed first [PlatformConfigService.getInstance] used to leave
/// a broken singleton with null prefs ("missing shared preferences" symptoms).
class SafeSharedPreferences {
  SafeSharedPreferences._();

  static SharedPreferences? _cached;

  static Future<SharedPreferences> getInstance({
    int attempts = 4,
    Duration pause = const Duration(milliseconds: 200),
  }) async {
    if (_cached != null) return _cached!;

    Object? lastError;
    for (var i = 0; i < attempts; i++) {
      try {
        final prefs = await SharedPreferences.getInstance();
        _cached = prefs;
        return prefs;
      } on MissingPluginException catch (e) {
        lastError = e;
        await Future<void>.delayed(pause * (i + 1));
      } catch (e) {
        lastError = e;
        await Future<void>.delayed(pause * (i + 1));
      }
    }

    throw StateError(
      'Shared preferences unavailable on this device '
      '(${lastError ?? 'unknown error'}). '
      'Uninstall EyeNet Authenticator completely, reboot the phone, '
      'reinstall the latest .apk from the wiki, then try again.',
    );
  }

  /// Test-only / recovery: drop the cached instance.
  static void resetCache() {
    _cached = null;
  }
}
