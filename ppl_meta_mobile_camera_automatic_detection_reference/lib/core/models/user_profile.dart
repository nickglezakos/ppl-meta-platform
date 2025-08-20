/// User profile model from PPL Meta Node service
class UserProfile {
  final int id;
  final String guid;
  final String username;
  final String email;
  final bool emailVerified;
  final bool isActive;
  final DateTime createdAt;
  final DateTime? updatedAt;

  const UserProfile({
    required this.id,
    required this.guid,
    required this.username,
    required this.email,
    required this.emailVerified,
    required this.isActive,
    required this.createdAt,
    this.updatedAt,
  });

  /// Create UserProfile from JSON response
  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as int,
      guid: json['guid'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      emailVerified: json['email_verified'] as bool? ?? false,
      isActive: json['is_active'] as bool? ?? true,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null 
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'guid': guid,
      'username': username,
      'email': email,
      'email_verified': emailVerified,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  @override
  String toString() {
    return 'UserProfile(id: $id, username: $username, email: $email)';
  }
}
