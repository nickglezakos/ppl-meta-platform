import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:ppl_meta_mobile_camera/services/app_logger.dart';
import 'package:ppl_meta_mobile_camera/services/platform_config_service.dart';

Future<PlatformConfigService> _serviceWith(Map<String, Object> initial) async {
  SharedPreferences.setMockInitialValues(initial);
  PlatformConfigService.resetForTest();
  return PlatformConfigService.getInstance();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    await AppLogger.instance.initialize();
    SharedPreferences.resetStatic();
    PlatformConfigService.resetForTest();
  });

  group('platformHost precedence (LAN-first)', () {
    test('prefers platform_local_ip over mesh IP', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
      });
      expect(svc.platformHost, '192.168.1.50');
      expect(svc.preferVpnHost, isFalse);
    });

    test('falls back to mesh IP when prefer_vpn_host is set (remote)', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
        'prefer_vpn_host': true,
      });
      expect(svc.platformHost, '100.64.0.22');
    });

    test('uses manual backend IP when no mesh/local IP present', () async {
      final svc = await _serviceWith({
        'discovery_host': '192.168.1.100',
      });
      expect(svc.platformHost, '192.168.1.100');
    });

    test('local host resolved via markLanReachable / markLanUnreachable', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '10.0.0.5',
      });
      await svc.markLanUnreachable();
      expect(svc.platformHost, '100.64.0.22');
      await svc.markLanReachable();
      expect(svc.platformHost, '10.0.0.5');
    });
  });

  group('discovery / gateway URL', () {
    test('uses platform host for discovery service URL', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
      });
      expect(svc.discoveryServiceUrl, 'http://192.168.1.50:8006');
      expect(svc.gatewayUrl, 'http://192.168.1.50:8080');
    });

    test('vpnDiscoveryNodeIp prefers assigned platform mesh over legacy', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'vpn_primary_node_ip': '100.64.0.10',
      });
      expect(svc.vpnDiscoveryNodeIp, '100.64.0.22');
    });
  });

  group('rewriteUrlForReachability (remote media/stream rewrite)', () {
    test('rewrites LAN hosts to mesh when prefer_vpn_host is set', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
        'prefer_vpn_host': true,
      });
      expect(
        svc.rewriteUrlForReachability('http://192.168.1.50:8080/live'),
        'http://100.64.0.22:8080/live',
      );
      expect(
        svc.rewriteUrlForReachability('http://10.0.0.9:8000/stream.mjpeg'),
        'http://100.64.0.22:8000/stream.mjpeg',
      );
    });

    test('does not rewrite when prefer_vpn_host is false (on LAN)', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
      });
      expect(
        svc.rewriteUrlForReachability('http://192.168.1.50:8080/live'),
        'http://192.168.1.50:8080/live',
      );
    });

    test('leaves public hosts untouched even in remote mode', () async {
      final svc = await _serviceWith({
        'vpn_platform_tailscale_ip': '100.64.0.22',
        'platform_local_ip': '192.168.1.50',
        'prefer_vpn_host': true,
      });
      expect(
        svc.rewriteUrlForReachability('https://cdn.example.com/clip.mp4'),
        'https://cdn.example.com/clip.mp4',
      );
    });
  });

  group('skipOnboarding', () {
    test('true when VPN enrolled', () async {
      final svc = await _serviceWith({'vpn_enrolled': true});
      expect(svc.skipOnboarding, isTrue);
    });

    test('true when a concrete backend host exists', () async {
      final svc = await _serviceWith({'discovery_host': '192.168.1.100'});
      expect(svc.skipOnboarding, isTrue);
    });

    test('false when nothing usable', () async {
      final svc = await _serviceWith({});
      expect(svc.skipOnboarding, isFalse);
    });
  });
}