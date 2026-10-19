import 'package:uuid/uuid.dart';

import '../../services/safe_shared_preferences.dart';

/// Soft install id for Presence sessions — not a cameras-console device.
class SoftDeviceId {
  SoftDeviceId._();
  static final SoftDeviceId instance = SoftDeviceId._();

  static const _key = 'authenticator_soft_device_uuid';

  Future<String> getOrCreate() async {
    final prefs = await SafeSharedPreferences.getInstance();
    final existing = prefs.getString(_key);
    if (existing != null && existing.isNotEmpty) return existing;
    final id = const Uuid().v4();
    await prefs.setString(_key, id);
    return id;
  }
}
