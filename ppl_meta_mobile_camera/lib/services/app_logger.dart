import 'dart:io';
import 'package:logging/logging.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;

/// Centralized logging service for PPL Meta Mobile Camera
/// Provides structured logging with file output and console output
class AppLogger {
  static AppLogger? _instance;
  static AppLogger get instance => _instance ??= AppLogger._();
  AppLogger._();

  late final Logger _rootLogger;
  File? _logFile;
  bool _isInitialized = false;

  /// Initialize the logging system
  Future<void> initialize() async {
    if (_isInitialized) return;

    // Configure logging level
    Logger.root.level = Level.INFO;
    
    // Set up log file
    await _setupLogFile();
    
    // Configure log output
    Logger.root.onRecord.listen((record) {
      final message = _formatLogRecord(record);
      
      // Console output
      // ignore: avoid_print
      print(message);
      
      // File output
      _writeToFile(message);
    });

    _rootLogger = Logger('PPLMetaCamera');
    _isInitialized = true;
    
    info('🚀 AppLogger initialized successfully');
  }

  /// Set up log file in app documents directory
  Future<void> _setupLogFile() async {
    try {
      final documentsDir = await getApplicationDocumentsDirectory();
      final logDir = Directory(path.join(documentsDir.path, 'logs'));
      
      if (!await logDir.exists()) {
        await logDir.create(recursive: true);
      }
      
      final fileName = 'ppl_meta_camera_${DateTime.now().toIso8601String().split('T').first}.log';
      _logFile = File(path.join(logDir.path, fileName));
      
      // Create file if it doesn't exist
      if (!await _logFile!.exists()) {
        await _logFile!.create();
      }
    } catch (e) {
      // Fallback: log to console only
      // ignore: avoid_print
      print('⚠️ Failed to setup log file: $e');
    }
  }

  /// Format log record for output
  String _formatLogRecord(LogRecord record) {
    final timestamp = record.time.toIso8601String();
    final level = record.level.name.padRight(7);
    final logger = record.loggerName.padRight(15);
    return '[$timestamp] $level [$logger] ${record.message}';
  }

  /// Write message to log file
  Future<void> _writeToFile(String message) async {
    try {
      if (_logFile != null) {
        await _logFile!.writeAsString('$message\n', mode: FileMode.append);
      }
    } catch (e) {
      // Ignore file write errors to prevent logging loops
    }
  }

  /// Get logger for specific component
  Logger getLogger(String name) {
    return Logger(name);
  }

  // Convenience methods for common log levels
  void debug(String message) => _rootLogger.fine('🔍 $message');
  void info(String message) => _rootLogger.info('ℹ️ $message');
  void warning(String message) => _rootLogger.warning('⚠️ $message');
  void error(String message, [Object? error, StackTrace? stackTrace]) {
    _rootLogger.severe('❌ $message', error, stackTrace);
  }
  void success(String message) => _rootLogger.info('✅ $message');
  
  /// Get current log file path (for debugging)
  String? get logFilePath => _logFile?.path;
  
  /// Clear old log files (keep last 7 days)
  Future<void> cleanupOldLogs() async {
    try {
      if (_logFile == null) return;
      
      final logDir = _logFile!.parent;
      final cutoffDate = DateTime.now().subtract(const Duration(days: 7));
      
      await for (final entity in logDir.list()) {
        if (entity is File && entity.path.endsWith('.log')) {
          final stat = await entity.stat();
          if (stat.modified.isBefore(cutoffDate)) {
            await entity.delete();
          }
        }
      }
    } catch (e) {
      warning('Failed to cleanup old logs: $e');
    }
  }
}

/// Specialized loggers for different components
class AutoRegistrationLogger {
  static final Logger _logger = Logger('AutoRegistration');
  
  static void step(String stepNumber, String description) {
    _logger.info('🔧 Step $stepNumber: $description');
  }
  
  static void success(String message) {
    _logger.info('✅ $message');
  }
  
  static void error(String message, [Object? error]) {
    _logger.severe('❌ $message', error);
  }
  
  static void debug(String message) {
    _logger.fine('🔍 $message');
  }
  
  static void apiCall(String method, String url, int? statusCode) {
    _logger.info('📡 $method $url → ${statusCode ?? 'pending'}');
  }
  
  static void deviceInfo(String key, dynamic value) {
    _logger.info('📱 $key: $value');
  }
}

class CameraLogger {
  static final Logger _logger = Logger('Camera');
  
  static void debug(String message) {
    _logger.fine('🔍 $message');
  }
  
  static void info(String message) {
    _logger.info('ℹ️ $message');
  }
  
  static void warning(String message) {
    _logger.warning('⚠️ $message');
  }
  
  static void success(String message) {
    _logger.info('✅ $message');
  }
  
  static void step(String stepNumber, String description) {
    _logger.info('🔧 Step $stepNumber: $description');
  }
  
  static void setup(String message) {
    _logger.info('🎬 $message');
  }
  
  static void streaming(String message) {
    _logger.info('📹 $message');
  }
  
  static void error(String message, [Object? error]) {
    _logger.severe('❌ $message', error);
  }
}

class AuthLogger {
  static final Logger _logger = Logger('Authentication');
  
  static void login(String message) {
    _logger.info('🔐 $message');
  }
  
  static void discovery(String message) {
    _logger.info('🔍 $message');
  }
  
  static void error(String message, [Object? error]) {
    _logger.severe('❌ $message', error);
  }
}
