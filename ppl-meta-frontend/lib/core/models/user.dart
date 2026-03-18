import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';

/// User model representing a user in the PPL Meta Platform
@JsonSerializable()
class User {
  final int id;
  final String username;
  final String email;
  @JsonKey(name: 'email_verified')
  final bool emailVerified;
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;
  @JsonKey(defaultValue: <String>[])
  final List<String> roles;
  @JsonKey(defaultValue: <String>[])
  final List<String> capabilities;

  const User({
    required this.id,
    required this.username,
    required this.email,
    this.emailVerified = false,
    this.createdAt,
    this.updatedAt,
    this.roles = const [],
    this.capabilities = const [],
  });

  bool get isAdmin => roles.contains('admin');
  bool get canViewMedia => capabilities.contains('media:view');

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);

  User copyWith({
    int? id,
    String? username,
    String? email,
    bool? emailVerified,
    DateTime? createdAt,
    DateTime? updatedAt,
    List<String>? roles,
    List<String>? capabilities,
  }) {
    return User(
      id: id ?? this.id,
      username: username ?? this.username,
      email: email ?? this.email,
      emailVerified: emailVerified ?? this.emailVerified,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      roles: roles ?? this.roles,
      capabilities: capabilities ?? this.capabilities,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is User && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() {
    return 'User(id: $id, username: $username, email: $email, emailVerified: $emailVerified)';
  }
}

/// Login request model
@JsonSerializable()
class LoginRequest {
  final String username; // Email is used as username in backend
  final String password;

  const LoginRequest({
    required this.username,
    required this.password,
  });

  factory LoginRequest.fromJson(Map<String, dynamic> json) => _$LoginRequestFromJson(json);
  Map<String, dynamic> toJson() => _$LoginRequestToJson(this);
}

/// Registration request model
@JsonSerializable()
class RegisterRequest {
  final String username;
  final String email;
  final String password;

  const RegisterRequest({
    required this.username,
    required this.email,
    required this.password,
  });

  factory RegisterRequest.fromJson(Map<String, dynamic> json) => _$RegisterRequestFromJson(json);
  Map<String, dynamic> toJson() => _$RegisterRequestToJson(this);
}

/// Authentication response model
@JsonSerializable()
class AuthResponse {
  @JsonKey(name: 'access_token')
  final String accessToken;
  @JsonKey(name: 'token_type')
  final String tokenType;
  final User? user;

  const AuthResponse({
    required this.accessToken,
    required this.tokenType,
    this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) => _$AuthResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AuthResponseToJson(this);
}

/// Error response model
@JsonSerializable()
class ApiError {
  final String detail;
  final String? type;

  const ApiError({
    required this.detail,
    this.type,
  });

  factory ApiError.fromJson(Map<String, dynamic> json) => _$ApiErrorFromJson(json);
  Map<String, dynamic> toJson() => _$ApiErrorToJson(this);

  @override
  String toString() => detail;
}
