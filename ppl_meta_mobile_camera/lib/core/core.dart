// Core exports for PPL Meta Mobile Camera

// Interfaces
export 'interfaces/camera_interface.dart';

// Models
export 'models/camera_config.dart';
export 'models/mobile_camera.dart';

// Services
export 'services/camera_service.dart';
export 'services/gallery_service.dart';
export 'services/streaming_service.dart';
export 'services/authentication_service.dart';
export 'services/mjpeg_streaming_service.dart';
export 'services/network_discovery_service.dart';

// Discovery Service Integration
export '../../services/ppl_meta_discovery_client.dart' hide ServiceInfo, DiscoveryException;
export '../../services/simplified_discovery_client.dart';
export '../../services/discovery_based_authentication_service.dart';
export '../../services/auto_camera_registration_service.dart';

// Legacy services (for backward compatibility)  
export '../../services/auto_authentication_service.dart' hide AuthResult, PlatformServices, AuthException;

// Providers
export 'providers/camera_provider.dart';
export 'providers/gallery_provider.dart';
export 'providers/streaming_provider.dart';
export 'providers/authentication_provider.dart';
