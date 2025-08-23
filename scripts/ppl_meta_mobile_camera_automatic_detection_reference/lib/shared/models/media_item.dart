/// Media type enumeration for photos, videos, and other media
enum MediaType {
  photo,
  video,
  other,
}

/// Represents a media item (photo or video) in the gallery
class MediaItem {
  final String id;
  final String name;
  final String path;
  final String? thumbnailPath;
  final MediaType type;
  final DateTime createdAt;
  final int? duration; // Duration in seconds for videos
  final int? fileSize; // File size in bytes
  final Map<String, dynamic>? metadata;

  // Aliases for compatibility with existing services
  String get filePath => path;
  DateTime get timestamp => createdAt;

  const MediaItem({
    required this.id,
    required this.name,
    required this.path,
    this.thumbnailPath,
    required this.type,
    required this.createdAt,
    this.duration,
    this.fileSize,
    this.metadata,
  });

  /// Create MediaItem from JSON
  factory MediaItem.fromJson(Map<String, dynamic> json) {
    return MediaItem(
      id: json['id'] as String,
      name: json['name'] as String,
      path: json['path'] as String,
      thumbnailPath: json['thumbnailPath'] as String?,
      type: MediaType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => MediaType.other,
      ),
      createdAt: DateTime.parse(json['createdAt'] as String),
      duration: json['duration'] as int?,
      fileSize: json['fileSize'] as int?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  /// Convert MediaItem to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'path': path,
      'thumbnailPath': thumbnailPath,
      'type': type.name,
      'createdAt': createdAt.toIso8601String(),
      'duration': duration,
      'fileSize': fileSize,
      'metadata': metadata,
    };
  }

  /// Create a copy with modified properties
  MediaItem copyWith({
    String? id,
    String? name,
    String? path,
    String? thumbnailPath,
    MediaType? type,
    DateTime? createdAt,
    int? duration,
    int? fileSize,
    Map<String, dynamic>? metadata,
  }) {
    return MediaItem(
      id: id ?? this.id,
      name: name ?? this.name,
      path: path ?? this.path,
      thumbnailPath: thumbnailPath ?? this.thumbnailPath,
      type: type ?? this.type,
      createdAt: createdAt ?? this.createdAt,
      duration: duration ?? this.duration,
      fileSize: fileSize ?? this.fileSize,
      metadata: metadata ?? this.metadata,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is MediaItem && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'MediaItem(id: $id, name: $name, type: $type)';
  }
}
