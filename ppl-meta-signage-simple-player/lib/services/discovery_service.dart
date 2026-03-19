import 'dart:async';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../models/device_info_model.dart';
import '../config/app_config.dart';
import '../utils/device_info_helper.dart';
import 'config_service.dart';

/// Service for discovering and registering with ppl-meta-discovery
class SignageDiscoveryService {
  final Dio _dio;
  final Logger _logger;
  final ConfigService _configService;
  
  Timer? _heartbeatTimer;
  bool _isRegistered = false;
  String? _serviceId;
  DeviceInfoModel? _deviceInfo;
  String? _lastError;

  SignageDiscoveryService({
    Dio? dio,
    Logger? logger,
    required ConfigService configService,
  })  : _dio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 4),
                sendTimeout: const Duration(seconds: 4),
                receiveTimeout: const Duration(seconds: 6),
              ),
            ),
        _logger = logger ?? Logger(),
        _configService = configService;

  /// Initialize and register the service
  Future<bool> initialize() async {
    try {
      _lastError = null;
      _logger.i('Initializing Discovery Service...');
      
      // Get device information
      _deviceInfo = await DeviceInfoHelper.getDeviceInfo();
      _logger.d('Device ID: ${_deviceInfo!.deviceId}');
      _logger.d('Device Name: ${_deviceInfo!.deviceName}');
      
      // Register with discovery service
      final registered = await register();
      
      if (registered) {
        _startHeartbeat();
        _logger.i('Discovery Service initialized successfully');
      } else {
        _logger.w('Failed to register with discovery service');
      }
      
      return registered;
    } catch (e, stackTrace) {
      _lastError = 'Discovery initialization failed: $e';
      _logger.e('Failed to initialize discovery service', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Register service with ppl-meta-discovery
  Future<bool> register() async {
    if (_deviceInfo == null) {
      _logger.e('Device info not available for registration');
      return false;
    }

    try {
      _lastError = null;
      _logger.i('Registering with discovery service...');
      
      final localIp = await DeviceInfoHelper.getLocalIpAddress();
      
      final registration = ServiceRegistration(
        name: '${AppConfig.serviceName}-${_deviceInfo!.deviceId}',
        serviceType: AppConfig.serviceType,
        host: localIp,
        port: AppConfig.httpServerPort,
        metadata: _deviceInfo!.toJson(),
        healthCheckEndpoint: '/health',
        version: AppConfig.version,
      );

      final discoveryUrl = '${_configService.discoveryServiceUrl}/api/v1/services/register';
      _logger.d('Registering at: $discoveryUrl');
      
      final response = await _dio.post(
        discoveryUrl,
        data: registration.toJson(),
        options: Options(
          sendTimeout: const Duration(seconds: 4),
          receiveTimeout: const Duration(seconds: 6),
          headers: {
            'Content-Type': 'application/json',
          },
          validateStatus: (status) => status != null && status < 500,
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        _isRegistered = true;
        // Extract service_id from response
        final responseData = response.data as Map<String, dynamic>;
        _serviceId = responseData['service_id'] as String?;
        
        if (_serviceId == null) {
          _logger.w('No service_id in registration response, using service name as fallback');
          _serviceId = registration.name;
        }
        
        _logger.i('Successfully registered with discovery service');
        _logger.d('Service ID: $_serviceId');
        return true;
      } else if (response.statusCode == 401 || response.statusCode == 403) {
        _lastError = 'Authentication failed (credentials mismatch). Please verify backend credentials/configuration.';
        _logger.w('Discovery registration unauthorized: ${response.statusCode}');
        _logger.d('Response: ${response.data}');
        return false;
      } else {
        _lastError = 'Discovery registration failed (HTTP ${response.statusCode})';
        _logger.w('Registration failed with status: ${response.statusCode}');
        _logger.d('Response: ${response.data}');
        return false;
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        _lastError = 'Connection timeout to discovery service (${_configService.discoveryServiceUrl}).';
        _logger.w('Discovery service connection timeout - will retry with heartbeat');
      } else if (e.type == DioExceptionType.connectionError) {
        _lastError = 'Cannot connect to discovery service at ${_configService.discoveryServiceUrl}';
        _logger.w('Cannot connect to discovery service at ${_configService.discoveryServiceUrl}');
        _logger.w('Service will continue without registration');
      } else if (
          e.type == DioExceptionType.badResponse &&
          (e.response?.statusCode == 401 || e.response?.statusCode == 403)) {
        _lastError = 'Authentication failed (credentials mismatch). Please verify backend credentials/configuration.';
        _logger.w('Discovery registration unauthorized: ${e.response?.statusCode}');
      } else {
        _lastError = 'Discovery registration failed: ${e.message}';
        _logger.e('DioException during registration', error: e);
      }
      return false;
    } catch (e, stackTrace) {
      _lastError = 'Unexpected discovery registration error: $e';
      _logger.e('Unexpected error during registration', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Send heartbeat to discovery service
  Future<void> sendHeartbeat() async {
    if (!_isRegistered || _serviceId == null) {
      _logger.d('Not registered, attempting registration...');
      await register();
      return;
    }

    try {
      _logger.d('Sending heartbeat to discovery service...');
      
      final heartbeatUrl = '${_configService.discoveryServiceUrl}/api/v1/services/heartbeat';
      _logger.d('Heartbeat URL: $heartbeatUrl');
      _logger.d('Service ID: $_serviceId');
      
      final heartbeatData = {
        'service_id': _serviceId,
        'status': 'healthy',
        'metadata': {},
      };
      _logger.d('Heartbeat payload: $heartbeatData');
      
      final response = await _dio.post(
        heartbeatUrl,
        data: heartbeatData,
        options: Options(
          headers: {
            'Content-Type': 'application/json',
          },
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );

      if (response.statusCode == 200) {
        _logger.d('Heartbeat sent successfully');
      } else {
        _logger.w('Heartbeat failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout) {
        _logger.w('Heartbeat timeout - discovery service may be unavailable');
        _logger.w('Timeout details: ${e.message}');
      } else if (e.type == DioExceptionType.connectionError) {
        _logger.w('Heartbeat connection error - will retry on next interval');
        _logger.w('Connection error details: ${e.message}');
        _logger.w('Error type: ${e.type}');
        if (e.response != null) {
          _logger.w('Response status: ${e.response?.statusCode}');
          _logger.w('Response data: ${e.response?.data}');
        }
      } else {
        _logger.w('Heartbeat DioException type: ${e.type}');
        _logger.w('Heartbeat DioException message: ${e.message}');
        _logger.w('Heartbeat DioException response: ${e.response?.statusCode} - ${e.response?.data}');
      }
    } catch (e, stackTrace) {
      _logger.w('Heartbeat error: $e');
      _logger.w('Stack trace: $stackTrace');
    }
  }

  /// Start heartbeat timer
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(
      AppConfig.heartbeatInterval,
      (_) => sendHeartbeat(),
    );
    _logger.d('Heartbeat timer started (${AppConfig.heartbeatInterval.inSeconds}s interval)');
  }

  /// Deregister from discovery service
  Future<void> deregister() async {
    if (!_isRegistered || _serviceId == null) {
      _logger.d('Not registered, skipping deregistration');
      return;
    }

    try {
      _logger.i('Deregistering from discovery service...');
      
      final response = await _dio.delete(
        '${AppConfig.discoveryRegisterEndpoint}/$_serviceId',
        options: Options(
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );

      if (response.statusCode == 200 || response.statusCode == 204) {
        _logger.i('Successfully deregistered from discovery service');
      } else {
        _logger.w('Deregistration failed with status: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.w('Deregistration DioException: ${e.message}');
    } catch (e) {
      _logger.w('Deregistration error: $e');
    } finally {
      _isRegistered = false;
      _serviceId = null;
    }
  }

  /// Stop the heartbeat timer and deregister
  Future<void> dispose() async {
    _logger.i('Disposing Discovery Service...');
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    await deregister();
    _logger.i('Discovery Service disposed');
  }

  // Getters
  bool get isRegistered => _isRegistered;
  String? get serviceId => _serviceId;
  DeviceInfoModel? get deviceInfo => _deviceInfo;
  String? get lastError => _lastError;
}
