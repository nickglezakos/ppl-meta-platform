import 'dart:io';
import 'dart:convert';

/// Test script to verify the simplified discovery service approach
/// This simulates what the mobile app will do:
/// 1. Detect device IP (e.g., 192.168.200.67)
/// 2. Extract network prefix (192.168.200)
/// 3. Take user input (host: 107, port: 8006)
/// 4. Construct URL: http://192.168.200.107:8006/api/v1/services

Future<void> main() async {
  print('🧪 Testing Simplified Discovery Service with User Input');
  print('=======================================================');
  print('');
  
  // Simulate device IP detection
  final deviceIP = await getDeviceIP();
  if (deviceIP == null) {
    print('❌ Failed to detect device IP');
    return;
  }
  
  print('📱 Device IP detected: $deviceIP');
  
  // Extract network prefix (first 3 parts)
  final parts = deviceIP.split('.');
  if (parts.length != 4) {
    print('❌ Invalid IP format: $deviceIP');
    return;
  }
  
  final networkPrefix = '${parts[0]}.${parts[1]}.${parts[2]}';
  print('🌐 Network prefix: $networkPrefix');
  
  // Simulate user input
  const userHostIP = '107';  // User enters this
  const userPort = '8006';   // User enters this
  
  print('👤 User input - Host IP: $userHostIP, Port: $userPort');
  
  // Construct discovery service URL
  final discoveryUrl = 'http://$networkPrefix.$userHostIP:$userPort/api/v1/services';
  print('🎯 Constructed Discovery URL: $discoveryUrl');
  print('');
  
  // Test the URL (if services are running)
  print('🩺 Testing Discovery Service...');
  try {
    final httpClient = HttpClient();
    final request = await httpClient.getUrl(Uri.parse(discoveryUrl));
    request.headers.set('Accept', 'application/json');
    
    final response = await request.close();
    
    if (response.statusCode == 200) {
      final body = await response.transform(utf8.decoder).join();
      final data = body.contains('"services"');
      
      if (data) {
        print('✅ Discovery Service is working!');
        print('📊 Response contains services data');
      } else {
        print('❌ Invalid response format');
      }
    } else {
      print('❌ HTTP ${response.statusCode}');
    }
    
    httpClient.close();
    
  } catch (e) {
    print('❌ Connection failed: $e');
    print('💡 Make sure Discovery Service is running at $discoveryUrl');
  }
  
  print('');
  print('✅ Test complete!');
  print('');
  print('📋 Summary:');
  print('• Device IP: $deviceIP');
  print('• Network: $networkPrefix.x');
  print('• User input: $userHostIP:$userPort');
  print('• Target URL: $discoveryUrl');
}

/// Detect device IP using socket connection method
Future<String?> getDeviceIP() async {
  try {
    // Method 1: Socket-based detection
    final socket = await Socket.connect('8.8.8.8', 80);
    final localIP = socket.address.address;
    socket.destroy();
    return localIP;
  } catch (e) {
    print('❌ Socket method failed: $e');
    
    // Method 2: Network interface scanning
    try {
      final interfaces = await NetworkInterface.list();
      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && 
              !addr.isLoopback && 
              !addr.address.startsWith('169.254')) {
            return addr.address;
          }
        }
      }
    } catch (e2) {
      print('❌ Interface method failed: $e2');
    }
    
    return null;
  }
}
