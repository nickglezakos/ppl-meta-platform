import 'dart:convert';
import 'dart:developer' as developer;
import 'package:http/http.dart' as http;
import 'package:connectivity_plus/connectivity_plus.dart';
import 'dart:async';
import 'simplified_discovery_client.dart';

/// Service for managing dynamic IP updates for mobile cameras
/// Handles network changes and automatically updates the backend when IP changes
class MobileCameraIPUpdateService {
  static const String _logTag = 'IPUpdateService';
  
  // Network monitoring
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  String? _lastKnownIP;
  String? _currentDeviceId;
  String? _authToken;
  String? _cameraServiceUrl;
  Timer? _ipCheckTimer;
  
  // Discovery client for IP detection
  final SimplifiedDiscoveryClient _discoveryClient = SimplifiedDiscoveryClient();
  
  bool _isInitialized = false;
  bool _isUpdating = false;

  /// Initialize the IP update service
  Future<bool> initialize({
    required String deviceId,
    required String authToken,
    required String cameraServiceUrl,
  }) async {
    if (_isInitialized) return true;
    
    try {
      developer.log('Initializing IP Update Service for device: $deviceId', name: _logTag);
      
      _currentDeviceId = deviceId;
      _authToken = authToken;
      _cameraServiceUrl = cameraServiceUrl;
      
      // Get initial IP address
      _lastKnownIP = await _discoveryClient.getMyIPAddress();
      developer.log('Initial IP detected: $_lastKnownIP', name: _logTag);
      
      // Setup network connectivity monitoring
      _connectivitySubscription = Connectivity().onConnectivityChanged.listen(
        (List<ConnectivityResult> results) async {
          await _onConnectivityChanged(results.isNotEmpty ? results.first : ConnectivityResult.none);
        },
      );
      
      // Setup periodic IP verification (every 2 minutes)
      _ipCheckTimer = Timer.periodic(const Duration(minutes: 2), (timer) async {
        await _checkAndUpdateIP();
      });
      
      _isInitialized = true;
      developer.log('IP Update Service initialized successfully', name: _logTag);
      return true;
      
    } catch (e) {
      developer.log('Failed to initialize IP Update Service: $e', name: _logTag, level: 1000);
      return false;
    }
  }

  /// Handle network connectivity changes
  Future<void> _onConnectivityChanged(ConnectivityResult result) async {
    developer.log('Network connectivity changed: ${result.name}', name: _logTag);
    
    if (result == ConnectivityResult.wifi || result == ConnectivityResult.ethernet) {
      // WiFi connected - wait a bit for IP assignment then check
      await Future.delayed(const Duration(seconds: 3));
      await _checkAndUpdateIP();
    }
  }

  /// Check current IP and update backend if changed
  Future<bool> _checkAndUpdateIP() async {
    if (!_isInitialized || _isUpdating) return false;
    
    try {
      _isUpdating = true;
      
      // Get current IP address
      final currentIP = await _discoveryClient.getMyIPAddress();
      
      if (currentIP == null) {
        developer.log('Could not detect current IP address', name: _logTag, level: 900);
        return false;
      }
      
      // Check if IP has changed
      if (currentIP != _lastKnownIP) {
        developer.log('IP address changed: $_lastKnownIP -> $currentIP', name: _logTag);
        
        final success = await _updateBackendIP(currentIP);
        if (success) {
          _lastKnownIP = currentIP;
          developer.log('Backend IP updated successfully', name: _logTag);
          return true;
        } else {
          developer.log('Failed to update backend IP', name: _logTag, level: 900);
          return false;
        }
      }
      
      return true; // No change needed
      
    } catch (e) {
      developer.log('Error checking IP: $e', name: _logTag, level: 1000);
      return false;
    } finally {
      _isUpdating = false;
    }
  }

  /// Update the backend with new IP address using the quick update endpoint
  Future<bool> _updateBackendIP(String newIP) async {
    if (_currentDeviceId == null || _authToken == null || _cameraServiceUrl == null) {
      developer.log('Missing required parameters for IP update', name: _logTag, level: 1000);
      return false;
    }
    
    try {
      developer.log('Updating backend with new IP: $newIP', name: _logTag);
      
      final url = '$_cameraServiceUrl/api/v1/cameras/mobile/$_currentDeviceId/update-ip';
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: json.encode({
          'ip_address': newIP,
          'port': 8554, // Default RTSP port for mobile cameras
        }),
      );
      
      developer.log('IP update response: ${response.statusCode}', name: _logTag);
      
      if (response.statusCode == 200) {
        final responseData = json.decode(response.body);
        developer.log('IP update successful: ${responseData['message']}', name: _logTag);
        developer.log('New connection: ${responseData['new_connection']}', name: _logTag);
        return true;
      } else {
        developer.log('IP update failed: ${response.statusCode} - ${response.body}', name: _logTag, level: 900);
        return false;
      }
      
    } catch (e) {
      developer.log('Exception during IP update: $e', name: _logTag, level: 1000);
      return false;
    }
  }

  /// Manually trigger an IP check and update
  Future<bool> forceIPUpdate() async {
    developer.log('Forcing IP update check', name: _logTag);
    return await _checkAndUpdateIP();
  }

  /// Get the current known IP address
  String? get currentIP => _lastKnownIP;

  /// Check if the service is monitoring
  bool get isMonitoring => _isInitialized;

  /// Dispose of the service and cleanup resources
  Future<void> dispose() async {
    developer.log('Disposing IP Update Service', name: _logTag);
    
    _isInitialized = false;
    _isUpdating = false;
    
    await _connectivitySubscription?.cancel();
    _connectivitySubscription = null;
    
    _ipCheckTimer?.cancel();
    _ipCheckTimer = null;
    
    _currentDeviceId = null;
    _authToken = null;
    _cameraServiceUrl = null;
    _lastKnownIP = null;
    
    developer.log('IP Update Service disposed', name: _logTag);
  }
}
