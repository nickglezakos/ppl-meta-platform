/// Platform services configuration model
class PlatformServices {
  final ServiceEndpoint nodeService;
  final ServiceEndpoint mediaService;
  final ServiceEndpoint cameraService;
  final ServiceEndpoint gatewayService;
  final ServiceEndpoint orchestratorService;
  final ServiceEndpoint? visionService;

  PlatformServices({
    required this.nodeService,
    required this.mediaService,
    required this.cameraService,
    required this.gatewayService,
    required this.orchestratorService,
    this.visionService,
  });

  /// Create from JSON data
  factory PlatformServices.fromJson(Map<String, dynamic> json) {
    final microservices = json['microservices'] as Map<String, dynamic>? ?? {};
    
    return PlatformServices(
      nodeService: ServiceEndpoint.fromJson(microservices['node'] ?? {}),
      mediaService: ServiceEndpoint.fromJson(microservices['media'] ?? {}),
      cameraService: ServiceEndpoint.fromJson(microservices['cameras'] ?? {}),
      gatewayService: ServiceEndpoint.fromJson(microservices['gateway'] ?? {}),
      orchestratorService: ServiceEndpoint.fromJson(microservices['orchestrator'] ?? {}),
      visionService: microservices['vision'] != null 
          ? ServiceEndpoint.fromJson(microservices['vision'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'microservices': {
        'node': nodeService.toJson(),
        'media': mediaService.toJson(),
        'cameras': cameraService.toJson(),
        'gateway': gatewayService.toJson(),
        'orchestrator': orchestratorService.toJson(),
        if (visionService != null) 'vision': visionService!.toJson(),
      }
    };
  }
}

/// Service endpoint configuration
class ServiceEndpoint {
  final String endpoint;
  final String? description;
  final bool isAvailable;

  ServiceEndpoint({
    required this.endpoint,
    this.description,
    this.isAvailable = true,
  });

  factory ServiceEndpoint.fromJson(Map<String, dynamic> json) {
    return ServiceEndpoint(
      endpoint: json['endpoint'] as String? ?? '',
      description: json['description'] as String?,
      isAvailable: json['is_available'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'endpoint': endpoint,
      if (description != null) 'description': description,
      'is_available': isAvailable,
    };
  }
}
