/// Generic API response wrapper
class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? error;
  final String? message;
  final int? statusCode;
  
  const ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.message,
    this.statusCode,
  });
  
  /// Create successful response
  factory ApiResponse.success(T data, {String? message}) {
    return ApiResponse(
      success: true,
      data: data,
      message: message,
    );
  }
  
  /// Create error response
  factory ApiResponse.error(String error, {int? statusCode, String? message}) {
    return ApiResponse(
      success: false,
      error: error,
      statusCode: statusCode,
      message: message,
    );
  }
  
  /// Check if response has data
  bool get hasData => data != null;
  
  /// Check if response has error
  bool get hasError => error != null;
  
  /// Alternative getter for success (for backward compatibility)
  bool get isSuccess => success;
}

/// Loading state for UI components
enum LoadingState {
  idle,
  loading,
  success,
  error,
}

/// Result wrapper for async operations
class Result<T> {
  final T? data;
  final String? error;
  final bool isSuccess;
  
  const Result._({
    this.data,
    this.error,
    required this.isSuccess,
  });
  
  /// Create successful result
  factory Result.success(T data) {
    return Result._(
      data: data,
      isSuccess: true,
    );
  }
  
  /// Create error result
  factory Result.error(String error) {
    return Result._(
      error: error,
      isSuccess: false,
    );
  }
  
  /// Check if result is error
  bool get isError => !isSuccess;
  
  /// Get data or throw error
  T get dataOrThrow {
    if (isSuccess && data != null) {
      return data!;
    }
    throw Exception(error ?? 'Unknown error');
  }
  
  /// Transform result data
  Result<U> map<U>(U Function(T) mapper) {
    if (isSuccess && data != null) {
      try {
        return Result.success(mapper(data!));
      } catch (e) {
        return Result.error(e.toString());
      }
    }
    return Result.error(error ?? 'No data to map');
  }
  
  /// Handle result with callbacks
  U when<U>({
    required U Function(T data) success,
    required U Function(String error) error,
  }) {
    if (isSuccess && data != null) {
      return success(data!);
    }
    return error(this.error ?? 'Unknown error');
  }
}
