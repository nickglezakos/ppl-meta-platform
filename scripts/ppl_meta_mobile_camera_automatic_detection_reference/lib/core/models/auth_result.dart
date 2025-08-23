/// Authentication result model for PPL Meta platform login
class AuthResult {
  final bool success;
  final String? token;
  final String? tokenType;
  final String? error;
  final int? statusCode;

  const AuthResult({
    required this.success,
    this.token,
    this.tokenType,
    this.error,
    this.statusCode,
  });

  /// Create successful authentication result
  factory AuthResult.success(String token, {String tokenType = 'bearer'}) {
    return AuthResult(
      success: true,
      token: token,
      tokenType: tokenType,
    );
  }

  /// Create failed authentication result
  factory AuthResult.failure(String error, {int? statusCode}) {
    return AuthResult(
      success: false,
      error: error,
      statusCode: statusCode,
    );
  }

  @override
  String toString() {
    if (success) {
      return 'AuthResult.success(token: ${token?.substring(0, 20)}...)';
    } else {
      return 'AuthResult.failure(error: $error, statusCode: $statusCode)';
    }
  }
}
