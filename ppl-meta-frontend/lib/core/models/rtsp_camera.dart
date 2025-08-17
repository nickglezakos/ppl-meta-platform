/// RTSP Camera configuration model for network cameras

import 'camera.dart';

class RTSPCamera {
  final String id;
  final String name;
  final String host;
  final int port;
  final String username;
  final String password;
  final String streamPath;
  final RTSPTransport transport;
  final RTSPProfile profile;
  final bool isActive;
  final DateTime? lastConnected;
  final Map<String, dynamic>? capabilities;

  const RTSPCamera({
    required this.id,
    required this.name,
    required this.host,
    this.port = 554, // Default RTSP port
    required this.username,
    required this.password,
    this.streamPath = '/stream',
    this.transport = RTSPTransport.tcp,
    this.profile = RTSPProfile.main,
    this.isActive = false,
    this.lastConnected,
    this.capabilities,
  });

  /// Generate RTSP URL from configuration
  String get rtspUrl {
    final auth = '$username:$password';
    final portStr = port != 554 ? ':$port' : '';
    return 'rtsp://$auth@$host$portStr$streamPath';
  }

  /// Generate camera device ID for RTSP cameras
  String get deviceId => 'rtsp_${host.replaceAll('.', '_')}_$port';

  /// Convert to Camera model for compatibility
  Camera toCamera() {
    return Camera(
      id: id,
      name: name,
      deviceId: deviceId,
      manufacturer: 'Network Camera',
      model: 'RTSP',
      resolution: capabilities?['resolution'] as String?,
      status: isActive ? 'connected' : 'disconnected',
      isActive: isActive,
      lastSeen: lastConnected,
      streamUrl: rtspUrl,
      metadata: {
        'type': 'rtsp',
        'host': host,
        'port': port,
        'transport': transport.name,
        'profile': profile.name,
        ...?capabilities,
      },
    );
  }

  factory RTSPCamera.fromJson(Map<String, dynamic> json) {
    return RTSPCamera(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      host: json['host']?.toString() ?? '',
      port: json['port'] as int? ?? 554,
      username: json['username']?.toString() ?? '',
      password: json['password']?.toString() ?? '',
      streamPath: json['stream_path']?.toString() ?? '/stream',
      transport: RTSPTransport.values.firstWhere(
        (t) => t.name == json['transport']?.toString(),
        orElse: () => RTSPTransport.tcp,
      ),
      profile: RTSPProfile.values.firstWhere(
        (p) => p.name == json['profile']?.toString(),
        orElse: () => RTSPProfile.main,
      ),
      isActive: json['is_active'] as bool? ?? false,
      lastConnected: json['last_connected'] != null
          ? DateTime.tryParse(json['last_connected'].toString())
          : null,
      capabilities: json['capabilities'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'host': host,
      'port': port,
      'username': username,
      'password': password,
      'stream_path': streamPath,
      'transport': transport.name,
      'profile': profile.name,
      'is_active': isActive,
      'last_connected': lastConnected?.toIso8601String(),
      'capabilities': capabilities,
    };
  }

  RTSPCamera copyWith({
    String? id,
    String? name,
    String? host,
    int? port,
    String? username,
    String? password,
    String? streamPath,
    RTSPTransport? transport,
    RTSPProfile? profile,
    bool? isActive,
    DateTime? lastConnected,
    Map<String, dynamic>? capabilities,
  }) {
    return RTSPCamera(
      id: id ?? this.id,
      name: name ?? this.name,
      host: host ?? this.host,
      port: port ?? this.port,
      username: username ?? this.username,
      password: password ?? this.password,
      streamPath: streamPath ?? this.streamPath,
      transport: transport ?? this.transport,
      profile: profile ?? this.profile,
      isActive: isActive ?? this.isActive,
      lastConnected: lastConnected ?? this.lastConnected,
      capabilities: capabilities ?? this.capabilities,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is RTSPCamera &&
        other.id == id &&
        other.host == host &&
        other.port == port;
  }

  @override
  int get hashCode => Object.hash(id, host, port);
}

/// RTSP transport protocol options
enum RTSPTransport {
  tcp('TCP'),
  udp('UDP'),
  http('HTTP');

  const RTSPTransport(this.displayName);
  final String displayName;
}

/// RTSP stream profile options
enum RTSPProfile {
  main('Main'),
  sub('Sub'),
  third('Third');

  const RTSPProfile(this.displayName);
  final String displayName;
}
