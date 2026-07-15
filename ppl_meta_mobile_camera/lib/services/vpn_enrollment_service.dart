import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'app_logger.dart';

/// Stores the VPN enrollment state for the mobile camera.
class VpnEnrollmentService {
  static const String _keyAuthKey = 'vpn_auth_key';
  static const String _keyHeadscaleServer = 'vpn_headscale_server';
  static const String _keyTailscaleIp = 'vpn_tailscale_ip';
  static const String _keyEnrolled = 'vpn_enrolled';
  static const String _keyDeepLink = 'vpn_deep_link';
  static const String _keyDiscoveryUrl = 'vpn_discovery_url';
  static const String _keyMagicDns = 'vpn_magic_dns';

  /// Fetch a pre-auth key from the node, using the node's own installation
  /// credentials. This requires the camera to already be connected to the
  /// platform (IP configured via setup screen).
  static Future<Map<String, dynamic>?> fetchKeyFromNode({
    required String nodeIp,
    required int nodePort,
  }) async {
    try {
      final url = Uri.parse('http://$nodeIp:$nodePort/node/vpn/enroll');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        AppLogger.instance.info('VPN key fetched from node: ${data['headscale_server']}');
        return data;
      } else {
        AppLogger.instance.warning(
          'VPN enrollment failed: HTTP ${response.statusCode} ${response.body}',
        );
        return null;
      }
    } catch (e) {
      AppLogger.instance.warning('VPN enrollment error: $e');
      return null;
    }
  }

  /// Store enrollment data locally.
  static Future<void> saveEnrollment({
    required String authKey,
    required String headscaleServer,
    String? tailscaleIp,
    String? deepLink,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyAuthKey, authKey);
    await prefs.setString(_keyHeadscaleServer, headscaleServer);
    await prefs.setBool(_keyEnrolled, true);
    if (tailscaleIp != null) {
      await prefs.setString(_keyTailscaleIp, tailscaleIp);
    }
    if (deepLink != null) {
      await prefs.setString(_keyDeepLink, deepLink);
    }
  }

  /// Get stored Tailscale deep link (opens Tailscale app with pre-filled server+key).
  static Future<String?> getDeepLink() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyDeepLink);
  }

  /// Check if this device has a stored VPN enrollment.
  static Future<bool> isEnrolled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyEnrolled) ?? false;
  }

  /// Get stored auth key (for display or re-enrollment).
  static Future<String?> getAuthKey() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyAuthKey);
  }

  /// Get stored headscale server URL.
  static Future<String?> getHeadscaleServer() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyHeadscaleServer);
  }

  /// Get stored tailscale IP.
  static Future<String?> getTailscaleIp() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyTailscaleIp);
  }

  /// Save the node's MagicDNS discovery URL for VPN-based service discovery.
  static Future<void> saveDiscoveryUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyDiscoveryUrl, url);
  }

  /// Get the stored discovery URL (e.g. http://eyenet-office.eyenet-vpn.local:8002).
  static Future<String?> getDiscoveryUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyDiscoveryUrl);
  }

  /// Save the node's MagicDNS hostname.
  static Future<void> saveMagicDns(String dns) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyMagicDns, dns);
  }

  /// Get the stored MagicDNS hostname.
  static Future<String?> getMagicDns() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyMagicDns);
  }

  /// Clear all VPN enrollment data (for reset/switch installations).
  static Future<void> clearEnrollment() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyAuthKey);
    await prefs.remove(_keyHeadscaleServer);
    await prefs.remove(_keyTailscaleIp);
    await prefs.remove(_keyEnrolled);
    await prefs.remove(_keyDiscoveryUrl);
    await prefs.remove(_keyMagicDns);
    AppLogger.instance.info('VPN enrollment cleared');
  }
}