/// Custom exceptions for API operations
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic error;

  ApiException(this.message, {this.statusCode, this.error});

  @override
  String toString() {
    if (statusCode != null) {
      return 'ApiException: $message (Status: $statusCode)';
    }
    return 'ApiException: $message';
  }
}

/// Network connectivity exception
class NetworkException extends ApiException {
  NetworkException(String message, {dynamic error})
      : super(message, error: error);

  @override
  String toString() => 'NetworkException: $message';
}

/// Server error exception (5xx)
class ServerException extends ApiException {
  ServerException(String message, {int? statusCode, dynamic error})
      : super(message, statusCode: statusCode, error: error);

  @override
  String toString() => 'ServerException: $message (Status: $statusCode)';
}

/// Client error exception (4xx)
class ClientException extends ApiException {
  ClientException(String message, {int? statusCode, dynamic error})
      : super(message, statusCode: statusCode, error: error);

  @override
  String toString() => 'ClientException: $message (Status: $statusCode)';
}

/// Authentication/authorization exception
class AuthException extends ApiException {
  AuthException(String message, {int? statusCode, dynamic error})
      : super(message, statusCode: statusCode, error: error);

  @override
  String toString() => 'AuthException: $message';
}

/// Timeout exception
class TimeoutException extends ApiException {
  TimeoutException(String message, {dynamic error})
      : super(message, error: error);

  @override
  String toString() => 'TimeoutException: $message';
}

/// Data parsing exception
class ParseException extends ApiException {
  ParseException(String message, {dynamic error})
      : super(message, error: error);

  @override
  String toString() => 'ParseException: $message';
}
