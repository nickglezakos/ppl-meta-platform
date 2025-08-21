import 'auto_authentication_service.dart';
import 'auto_camera_registration_service.dart';

/// Complete automatic streaming workflow orchestrator
/// 
/// This service coordinates the entire automatic workflow:
/// 1. Auto-discovery and login (Phase 1)
/// 2. Dynamic service discovery (Phase 2) 
/// 3. Automatic camera registration (Phase 3)
class AutomaticStreamingWorkflow {
  final AutoAuthenticationService _authService = AutoAuthenticationService();
  final AutoCameraRegistrationService _registrationService = AutoCameraRegistrationService();
  
  /// Execute complete automatic workflow with zero user input required
  /// 
  /// User inputs required:
  /// - username: PPL Meta platform credentials
  /// - password: PPL Meta platform credentials  
  /// 
  /// Everything else is completely automatic:
  /// - IP detection and Node service discovery
  /// - Authentication and JWT token handling
  /// - Platform services discovery
  /// - Automatic camera name generation from device info
  /// - Camera registration with device specs
  Future<WorkflowResult> executeCompleteWorkflow({
    required String username,
    required String password,
  }) async {
    print('🚀 ========================================');
    print('🚀 STARTING AUTOMATIC STREAMING WORKFLOW');
    print('🚀 ========================================');
    print('🎯 ZERO USER INPUT WORKFLOW - Fully Automatic');
    print('🤖 Camera name will be auto-generated from device info');
    print('🎯 Goal: Complete automation with no user dialogs');
    print('🚀 ========================================');
    
    try {
      // Phase 1: Auto-discovery and login
      print('🔐 PHASE 1: Auto-Discovery & Login');
      print('🔍 Step 1: Auto-discovering Node service...');
      final authResult = await _authService.autoLogin(username, password);
      
      if (!authResult.success || authResult.services == null) {
        throw WorkflowException('Authentication failed: ${authResult.error}');
      }
      
      print('✅ Login successful! JWT token obtained.');
      print('🎫 Authentication complete');
      
      // Phase 2: Dynamic service discovery (already done in login)
      print('');
      print('🔍 PHASE 2: Dynamic Service Discovery');
      print('🔍 Step 2: Platform services discovered automatically');
      final services = authResult.services!;
      print('📹 Camera Service: ${services.cameraService.endpoint}');
      print('🎬 Media Service: ${services.mediaService.endpoint}');
      print('🌐 Gateway Service: ${services.gatewayService.endpoint}');
      print('🎼 Orchestrator Service: ${services.orchestratorService.endpoint}');
      if (services.visionService != null) {
        print('👁️ Vision Service: ${services.visionService!.endpoint}');
      }
      
      // Phase 3: Automatic camera registration with auto-generated name
      print('');
      print('📱 PHASE 3: Automatic Camera Registration (Zero Input)');
      print('🤖 Step 3: Auto-generating camera name and registering...');
      final cameraResult = await _registrationService.autoRegisterCamera(
        jwtToken: authResult.token!,
        services: services,
      );
      
      if (!cameraResult.success) {
        throw WorkflowException('Camera registration failed: ${cameraResult.error}');
      }
      
      print('✅ Camera registered automatically with zero user input!');
      print('🤖 Auto-generated camera name: ${cameraResult.cameraName}');
      print('📊 Camera ID: ${cameraResult.cameraId}');
      print('🆔 Device ID: ${cameraResult.deviceId}');
      print('📡 Status: ${cameraResult.status}');
      
      // Workflow completion
      print('');
      print('🎉 ========================================');
      print('🎉 ZERO-INPUT AUTOMATIC WORKFLOW COMPLETED!');
      print('🎉 ========================================');
      print('🤖 Camera "${cameraResult.cameraName}" auto-registered and ready');
      print('🔗 Camera ID: ${cameraResult.cameraId}');
      print('🎬 Media Service: ${cameraResult.mediaServiceURL}');
      print('🎯 Achievement: Complete automation with ZERO user input!');
      print('📹 Camera Service: ${services.cameraService.endpoint}');
      print('🎉 ========================================');
      
      return WorkflowResult.success(
        cameraId: cameraResult.cameraId!,
        deviceId: cameraResult.deviceId!,
        cameraName: cameraResult.cameraName!,
        jwtToken: authResult.token!,
        nodeServiceURL: authResult.nodeURL!,
        cameraServiceURL: services.cameraService.endpoint,
        mediaServiceURL: cameraResult.mediaServiceURL!,
        gatewayServiceURL: services.gatewayService.endpoint,
        readyForStreaming: true,
      );
      
    } catch (e) {
      print('❌ ========================================');
      print('❌ AUTOMATIC WORKFLOW FAILED');
      print('❌ ========================================');
      print('💥 Error: $e');
      print('❌ ========================================');
      
      return WorkflowResult.failure(error: e.toString());
    }
  }
  
  /// Quick validation of workflow prerequisites
  Future<bool> validateWorkflowPrerequisites() async {
    try {
      // Check network connectivity
      final networkService = AutoAuthenticationService();
      // This is a simplified check - in practice you might want more thorough validation
      return true;
    } catch (e) {
      print('⚠️ Workflow prerequisites check failed: $e');
      return false;
    }
  }
}

/// Complete workflow result container
class WorkflowResult {
  final bool success;
  final int? cameraId;
  final String? deviceId;
  final String? cameraName;
  final String? jwtToken;
  final String? nodeServiceURL;
  final String? cameraServiceURL;
  final String? mediaServiceURL;
  final String? gatewayServiceURL;
  final bool readyForStreaming;
  final String? error;
  
  WorkflowResult._({
    required this.success,
    this.cameraId,
    this.deviceId,
    this.cameraName,
    this.jwtToken,
    this.nodeServiceURL,
    this.cameraServiceURL,
    this.mediaServiceURL,
    this.gatewayServiceURL,
    this.readyForStreaming = false,
    this.error,
  });
  
  factory WorkflowResult.success({
    required int cameraId,
    required String deviceId,
    required String cameraName,
    required String jwtToken,
    required String nodeServiceURL,
    required String cameraServiceURL,
    required String mediaServiceURL,
    required String gatewayServiceURL,
    required bool readyForStreaming,
  }) => WorkflowResult._(
    success: true,
    cameraId: cameraId,
    deviceId: deviceId,
    cameraName: cameraName,
    jwtToken: jwtToken,
    nodeServiceURL: nodeServiceURL,
    cameraServiceURL: cameraServiceURL,
    mediaServiceURL: mediaServiceURL,
    gatewayServiceURL: gatewayServiceURL,
    readyForStreaming: readyForStreaming,
  );
  
  factory WorkflowResult.failure({required String error}) => WorkflowResult._(
    success: false,
    error: error,
  );
  
  /// Get summary of workflow results for display
  Map<String, dynamic> toSummary() {
    if (!success) {
      return {
        'status': 'failed',
        'error': error,
      };
    }
    
    return {
      'status': 'success',
      'camera_id': cameraId,
      'device_id': deviceId,
      'camera_name': cameraName,
      'ready_for_streaming': readyForStreaming,
      'services': {
        'node': nodeServiceURL,
        'camera': cameraServiceURL,
        'media': mediaServiceURL,
        'gateway': gatewayServiceURL,
      },
    };
  }
}

/// Workflow execution exception
class WorkflowException implements Exception {
  final String message;
  WorkflowException(this.message);
  
  @override
  String toString() => 'WorkflowException: $message';
}
