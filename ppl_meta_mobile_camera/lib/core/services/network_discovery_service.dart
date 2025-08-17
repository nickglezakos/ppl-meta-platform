import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';
import '../models/mobile_camera.dart';

/// Service for discovering PPL Meta Platform on the network
class NetworkDiscoveryService {
  static NetworkDiscoveryService? _instance;
  static NetworkDiscoveryService get instance => _instance ??= NetworkDiscoveryService._();
  NetworkDiscoveryService._();

  static const List<int> commonPorts = [8005, 8080, 8000, 8001, 8002, 8003];
  static const Duration discoveryTimeout = Duration(seconds: 3);
  static const Duration scanTimeout = Duration(minutes: 2);

  /// Discover PPL Meta Platform on the local network
  Future<List<PlatformDiscoveryResult>> discoverPlatform({
    List<int>? ports,
    Duration? timeout,
  }) async {
    final scanPorts = ports ?? commonPorts;
    final scanTimeout = timeout ?? discoveryTimeout;
    
    print('Starting platform discovery on ports: $scanPorts');
    
    // Get local network info and prioritize local network
    final networkRanges = await _getNetworkRanges();
    
    // Prioritize local network (192.168.1.x) first
    final prioritizedRanges = <String>[];
    final wifiNetwork = networkRanges.firstWhere(
      (range) => range.startsWith('192.168.1'),
      orElse: () => '',
    );
    if (wifiNetwork.isNotEmpty) {
      prioritizedRanges.add(wifiNetwork);
      networkRanges.remove(wifiNetwork);
    }
    prioritizedRanges.addAll(networkRanges);
    
    print('Scanning prioritized network ranges: $prioritizedRanges');
    
    final results = <PlatformDiscoveryResult>[];
    
    // Scan each network range and port combination
    // Stop early if we find platforms in the local network
    for (final range in prioritizedRanges) {
      for (final port in scanPorts) {
        final rangeResults = await _scanNetworkRange(range, port, scanTimeout);
        results.addAll(rangeResults);
        
        // If we found platforms in local network, stop scanning other ranges
        if (results.isNotEmpty && range.startsWith('192.168.1')) {
          print('Found platforms in local network, stopping discovery');
          break;
        }
      }
      
      // If we found platforms in any range, consider stopping
      if (results.length >= 3) {
        print('Found sufficient platforms, stopping discovery');
        break;
      }
    }
    
    // Sort by response time (fastest first)
    results.sort((a, b) {
      if (!a.isReachable && !b.isReachable) return 0;
      if (!a.isReachable) return 1;
      if (!b.isReachable) return -1;
      
      final aTime = a.responseTime?.inMilliseconds ?? 9999;
      final bTime = b.responseTime?.inMilliseconds ?? 9999;
      return aTime.compareTo(bTime);
    });
    
    print('Discovery complete. Found ${results.where((r) => r.isReachable).length} reachable platforms');
    return results;
  }

  /// Test if a specific IP and port hosts PPL Meta Platform
  Future<PlatformDiscoveryResult> testPlatformEndpoint(
    String ipAddress,
    int port, {
    Duration? timeout,
  }) async {
    final testTimeout = timeout ?? discoveryTimeout;
    
    try {
      final stopwatch = Stopwatch()..start();
      
      // Test the cameras service health endpoint
      final response = await http.get(
        Uri.parse('http://$ipAddress:$port/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(testTimeout);
      
      stopwatch.stop();
      
      if (response.statusCode == 200) {
        try {
          final healthData = json.decode(response.body) as Map<String, dynamic>;
          
          // Check if this looks like PPL Meta Platform
          if (_isPPLMetaPlatform(healthData)) {
            return PlatformDiscoveryResult.reachable(
              ipAddress: ipAddress,
              port: port,
              responseTime: stopwatch.elapsed,
              healthData: healthData,
            );
          }
        } catch (e) {
          print('Error parsing health response from $ipAddress:$port - $e');
        }
      }
      
      return PlatformDiscoveryResult.unreachable(ipAddress, port);
    } catch (e) {
      return PlatformDiscoveryResult.unreachable(ipAddress, port);
    }
  }

  /// Get network ranges to scan based on local IP
  Future<List<String>> _getNetworkRanges() async {
    final ranges = <String>[];
    
    try {
      final info = NetworkInfo();
      final wifiIP = await info.getWifiIP();
      
      if (wifiIP != null && wifiIP.isNotEmpty) {
        // Add local WiFi network range
        final parts = wifiIP.split('.');
        if (parts.length == 4) {
          final networkBase = '${parts[0]}.${parts[1]}.${parts[2]}';
          ranges.add(networkBase);
        }
      }
      
      // Add common VPN ranges (Tailscale, WireGuard, etc.)
      ranges.addAll([
        '100.64', // Tailscale range 100.64.0.0/16
        '100.65',
        '100.66',
        '100.67',
        '10.0.0',   // Common private networks
        '10.0.1',
        '192.168.0',
        '192.168.1',
        '192.168.2',
        '172.16.0',
      ]);
      
      // Get network interfaces for additional ranges
      for (final interface in await NetworkInterface.list()) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            final parts = addr.address.split('.');
            if (parts.length == 4) {
              final networkBase = '${parts[0]}.${parts[1]}.${parts[2]}';
              if (!ranges.contains(networkBase)) {
                ranges.add(networkBase);
              }
            }
          }
        }
      }
    } catch (e) {
      print('Error getting network ranges: $e');
      // Fallback to common ranges
      ranges.addAll(['192.168.1', '192.168.0', '10.0.0', '100.64']);
    }
    
    return ranges.toSet().toList(); // Remove duplicates
  }

  /// Scan a network range for PPL Platform
  Future<List<PlatformDiscoveryResult>> _scanNetworkRange(
    String networkBase,
    int port,
    Duration timeout,
  ) async {
    print('Scanning $networkBase.x:$port');
    
    final results = <PlatformDiscoveryResult>[];
    final futures = <Future<PlatformDiscoveryResult>>[];
    
    // Create scan tasks for IPs 1-254
    for (int i = 1; i <= 254; i++) {
      final ip = '$networkBase.$i';
      futures.add(testPlatformEndpoint(ip, port, timeout: timeout));
    }
    
    // Execute scans in batches to avoid overwhelming the network
    const batchSize = 20;
    for (int i = 0; i < futures.length; i += batchSize) {
      final batch = futures.skip(i).take(batchSize);
      final batchResults = await Future.wait(batch);
      results.addAll(batchResults.where((r) => r.isReachable));
      
      // Add small delay between batches
      if (i + batchSize < futures.length) {
        await Future.delayed(const Duration(milliseconds: 100));
      }
    }
    
    return results;
  }

  /// Check if health response indicates PPL Meta Platform
  bool _isPPLMetaPlatform(Map<String, dynamic> healthData) {
    // Look for PPL Meta specific indicators in health response
    final service = healthData['service']?.toString().toLowerCase() ?? '';
    final status = healthData['status']?.toString().toLowerCase() ?? '';
    final environment = healthData['environment']?.toString().toLowerCase() ?? '';
    
    // Check for PPL Meta service indicators
    return service.contains('ppl') ||
           service.contains('camera') ||
           environment.contains('ppl') ||
           (status == 'healthy' && healthData.containsKey('timestamp'));
  }

  /// Quick discovery - scan only most likely IPs first
  Future<PlatformDiscoveryResult?> quickDiscovery({
    List<int>? ports,
    Duration? timeout,
  }) async {
    final scanPorts = ports ?? [8005]; // Cameras service port
    final scanTimeout = timeout ?? const Duration(seconds: 2);
    
    print('Starting quick discovery on ports: $scanPorts');
    
    try {
      final info = NetworkInfo();
      final wifiIP = await info.getWifiIP();
      
      if (wifiIP != null && wifiIP.isNotEmpty) {
        final parts = wifiIP.split('.');
        if (parts.length == 4) {
          final networkBase = '${parts[0]}.${parts[1]}.${parts[2]}';
          
          // Try common gateway IPs first
          final quickIPs = [
            '$networkBase.1',   // Common router IP
            '$networkBase.100', // Common server IP
            '$networkBase.101',
            '$networkBase.10',
            '$networkBase.2',
          ];
          
          for (final ip in quickIPs) {
            for (final port in scanPorts) {
              final result = await testPlatformEndpoint(ip, port, timeout: scanTimeout);
              if (result.isReachable) {
                print('Quick discovery found platform at $ip:$port');
                return result;
              }
            }
          }
        }
      }
    } catch (e) {
      print('Error in quick discovery: $e');
    }
    
    return null;
  }

  /// Manual connection test
  Future<PlatformDiscoveryResult> testManualConnection(
    String ipAddress,
    int port,
  ) async {
    print('Testing manual connection to $ipAddress:$port');
    return await testPlatformEndpoint(ipAddress, port);
  }

  /// Get current network information
  Future<Map<String, String?>> getNetworkInfo() async {
    try {
      final info = NetworkInfo();
      
      return {
        'wifi_ip': await info.getWifiIP(),
        'wifi_name': await info.getWifiName(),
        'wifi_bssid': await info.getWifiBSSID(),
        'wifi_ipv6': await info.getWifiIPv6(),
      };
    } catch (e) {
      print('Error getting network info: $e');
      return {};
    }
  }
}
