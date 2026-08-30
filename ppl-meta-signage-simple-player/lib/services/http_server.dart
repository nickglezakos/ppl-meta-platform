import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:shelf/shelf.dart';
import 'package:shelf/shelf_io.dart' as shelf_io;
import 'package:shelf_router/shelf_router.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:signage_simple_player/config/app_config.dart';
import 'package:signage_simple_player/services/config_service.dart';

/// Embedded HTTP server for local signage control and monitoring
/// 
/// Provides REST API endpoints for:
/// - Health checks
/// - Playback status queries
/// - Playback history
/// - Local control commands
class SignageHttpServer {
  final PlaylistDatabase _database;
  final SignagePlayerEngine _playerEngine;
  final ConfigService _configService;
  final Logger _logger;
  final String _deviceId;
  final int port;

  HttpServer? _server;
  bool _isRunning = false;

  SignageHttpServer({
    required PlaylistDatabase database,
    required SignagePlayerEngine playerEngine,
    required ConfigService configService,
    required Logger logger,
    required String deviceId,
    this.port = AppConfig.httpServerPort,
  })  : _database = database,
        _playerEngine = playerEngine,
        _configService = configService,
        _logger = logger,
        _deviceId = deviceId;

  bool get isRunning => _isRunning;

  /// Start the HTTP server
  Future<void> start() async {
    if (_isRunning) {
      _logger.w('HTTP server already running on port $port');
      return;
    }

    try {
      _logger.i('Starting HTTP server on port $port...');

      final handler = Pipeline()
          .addMiddleware(_loggingMiddleware())
          .addMiddleware(_corsMiddleware())
          .addMiddleware(_errorHandlingMiddleware())
          .addHandler(_createRouter().call);

      _server = await shelf_io.serve(
        handler,
        InternetAddress.anyIPv4,
        port,
      );

      _isRunning = true;
      _logger.i('HTTP server started successfully on http://${_server!.address.host}:${_server!.port}');
    } catch (e, stack) {
      _logger.e('Failed to start HTTP server', error: e, stackTrace: stack);
      rethrow;
    }
  }

  /// Stop the HTTP server
  Future<void> stop() async {
    if (!_isRunning || _server == null) {
      return;
    }

    try {
      _logger.i('Stopping HTTP server...');
      await _server!.close(force: true);
      _server = null;
      _isRunning = false;
      _logger.i('HTTP server stopped');
    } catch (e, stack) {
      _logger.e('Error stopping HTTP server', error: e, stackTrace: stack);
    }
  }

  /// Create the router with all endpoints
  Router _createRouter() {
    final router = Router();

    // Health check endpoint
    router.get('/health', _handleHealth);

    // Status endpoint
    router.get('/api/v1/status', _handleStatus);

    // History endpoints
    router.get('/api/v1/history', _handleHistoryQuery);
    router.get('/api/v1/history/summary', _handleHistorySummary);

    // Control endpoint
    router.post('/api/v1/control', _handleControl);

    // Sync endpoint
    router.post('/api/v1/sync', _handleSync);

    // Assets / manifest endpoint (delta-sync support)
    router.get('/api/v1/assets', _handleAssets);

    // Configuration endpoints (for remote setup)
    router.get('/api/v1/config', _handleGetConfig);
    router.post('/api/v1/config', _handleSetConfig);

    // Catch-all for 404
    router.all('/<ignored|.*>', _handle404);

    return router;
  }

  /// Health check endpoint
  Future<Response> _handleHealth(Request request) async {
    return Response.ok(
      jsonEncode({
        'status': 'healthy',
        'service': AppConfig.serviceName,
        'version': AppConfig.version,
        'device_id': _deviceId,
        'timestamp': DateTime.now().toIso8601String(),
      }),
      headers: {'Content-Type': 'application/json'},
    );
  }

  /// Status endpoint - returns current playback status
  Future<Response> _handleStatus(Request request) async {
    try {
      final status = _playerEngine.getPlaybackStatus(_deviceId);

      return Response.ok(
        jsonEncode(status.toJson()),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error getting playback status', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to get playback status',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// History query endpoint
  Future<Response> _handleHistoryQuery(Request request) async {
    try {
      // Parse query parameters
      final params = request.url.queryParameters;
      final limit = int.tryParse(params['limit'] ?? '50') ?? 50;
      final offset = int.tryParse(params['offset'] ?? '0') ?? 0;
      final videoId = params['video_id'];
      final playlistId = params['playlist_id'];

      DateTime? startDate;
      DateTime? endDate;

      if (params['start_date'] != null) {
        startDate = DateTime.tryParse(params['start_date']!);
      }
      if (params['end_date'] != null) {
        endDate = DateTime.tryParse(params['end_date']!);
      }

      // Query history from database
      final history = await _database.queryHistory(
        videoId: videoId,
        playlistId: playlistId,
        startDate: startDate,
        endDate: endDate,
        limit: limit,
        offset: offset,
      );

      final count = await _database.countHistory(
        videoId: videoId,
        playlistId: playlistId,
        startDate: startDate,
        endDate: endDate,
      );

      return Response.ok(
        jsonEncode({
          'history': history.map((e) => e.toJson()).toList(),
          'count': count,
          'limit': limit,
          'offset': offset,
        }),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error querying history', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to query history',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// History summary endpoint
  Future<Response> _handleHistorySummary(Request request) async {
    try {
      final params = request.url.queryParameters;
      DateTime? startDate;
      DateTime? endDate;

      if (params['start_date'] != null) {
        startDate = DateTime.tryParse(params['start_date']!);
      }
      if (params['end_date'] != null) {
        endDate = DateTime.tryParse(params['end_date']!);
      }

      final summary = await _database.getPlaybackSummary(
        startDate: startDate,
        endDate: endDate,
      );

      return Response.ok(
        jsonEncode(summary),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error getting history summary', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to get history summary',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// Control endpoint - handles playback control commands
  Future<Response> _handleControl(Request request) async {
    try {
      final body = await request.readAsString();
      final data = jsonDecode(body) as Map<String, dynamic>;

      final command = data['command'] as String?;
      if (command == null || command.isEmpty) {
        return Response.badRequest(
          body: jsonEncode({
            'error': 'Missing required field: command',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }

      _logger.i('Received control command: $command');

      bool success = false;
      String? message;

      switch (command.toLowerCase()) {
        case 'play':
          success = await _playerEngine.play();
          message = success ? 'Playback started' : 'Failed to start playback';
          break;

        case 'start':  // Backend sends 'start' command with video_list_id
          final videoListId = data['video_list_id'] as String?;
          if (videoListId != null) {
            // Load playlist first, then start playing
            _logger.i('📱 Received playlist switch command: $videoListId');
            success = await _playerEngine.loadPlaylist(videoListId);
            if (success) {
              success = await _playerEngine.play();
              message = success ? 'Playlist loaded and playback started' : 'Playlist loaded but failed to start playback';
              _logger.i('✅ Playlist switch successful');
            } else {
              message = 'Failed to load playlist. It may not be synced to this device yet.';
              _logger.w('❌ Playlist switch failed: $message');
            }
          } else {
            // No playlist specified, just start playing current playlist
            success = await _playerEngine.play();
            message = success ? 'Playback started' : 'Failed to start playback';
          }
          break;

        case 'pause':
          await _playerEngine.pause();
          success = true;
          message = 'Playback paused';
          break;

        case 'resume':
          await _playerEngine.resume();
          success = true;
          message = 'Playback resumed';
          break;

        case 'stop':
          await _playerEngine.stop();
          success = true;
          message = 'Playback stopped';
          break;

        case 'next':
          success = await _playerEngine.next();
          message = success ? 'Skipped to next video' : 'No next video available';
          break;

        case 'previous':
          success = await _playerEngine.previous();
          message = success ? 'Skipped to previous video' : 'No previous video available';
          break;

        case 'load_playlist':
          final playlistId = data['playlist_id'] as String?;
          if (playlistId == null) {
            return Response.badRequest(
              body: jsonEncode({
                'error': 'Missing required field: playlist_id',
              }),
              headers: {'Content-Type': 'application/json'},
            );
          }
          success = await _playerEngine.loadPlaylist(playlistId);
          message = success ? 'Playlist loaded' : 'Failed to load playlist';
          break;

        case 'seek':
          final positionMs = data['position_ms'] as int?;
          if (positionMs == null) {
            return Response.badRequest(
              body: jsonEncode({
                'error': 'Missing required field: position_ms',
              }),
              headers: {'Content-Type': 'application/json'},
            );
          }
          await _playerEngine.seekTo(Duration(milliseconds: positionMs));
          success = true;
          message = 'Seeked to ${positionMs}ms';
          break;

        case 'set_loop_mode':
          final mode = data['loop_mode'] as String?;
          if (mode == null) {
            return Response.badRequest(
              body: jsonEncode({
                'error': 'Missing required field: loop_mode',
              }),
              headers: {'Content-Type': 'application/json'},
            );
          }
          
          LoopMode? loopMode;
          switch (mode.toLowerCase()) {
            case 'continuous':
              loopMode = LoopMode.continuous;
              break;
            case 'once':
              loopMode = LoopMode.once;
              break;
            case 'single':
              loopMode = LoopMode.single;
              break;
            default:
              return Response.badRequest(
                body: jsonEncode({
                  'error': 'Invalid loop_mode. Must be: continuous, once, or single',
                }),
                headers: {'Content-Type': 'application/json'},
              );
          }
          
          _playerEngine.setLoopMode(loopMode);
          success = true;
          message = 'Loop mode set to $mode';
          break;

        default:
          return Response.badRequest(
            body: jsonEncode({
              'error': 'Unknown command: $command',
              'supported_commands': [
                'play',
                'pause',
                'resume',
                'stop',
                'next',
                'previous',
                'load_playlist',
                'seek',
                'set_loop_mode',
              ],
            }),
            headers: {'Content-Type': 'application/json'},
          );
      }

      final status = _playerEngine.getPlaybackStatus(_deviceId);

      return Response.ok(
        jsonEncode({
          'success': success,
          'message': message,
          'command': command,
          'status': status.toJson(),
          'timestamp': DateTime.now().toIso8601String(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error processing control command', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to process control command',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// Sync endpoint - receives playlist notification from backend
  /// 
  /// Backend sends playlist metadata here as a push notification.
  /// The device acknowledges receipt and can optionally trigger a pull sync.
  /// 
  /// Note: The device uses a pull model for actual sync - it calls the backend
  /// API to download playlists. This endpoint is for push notifications only.
  Future<Response> _handleSync(Request request) async {
    try {
      final body = await request.readAsString();
      final data = jsonDecode(body) as Map<String, dynamic>;

      final videoListData = data['video_list'] as Map<String, dynamic>?;
      if (videoListData == null) {
        return Response.badRequest(
          body: jsonEncode({
            'error': 'Missing required field: video_list',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }

      final playlistId = videoListData['id'] as String?;
      final playlistName = videoListData['name'] as String?;
      final videos = videoListData['videos'] as List<dynamic>?;

      if (playlistId == null || playlistName == null) {
        return Response.badRequest(
          body: jsonEncode({
            'error': 'Invalid video_list format. Required: id, name',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }

      final videoCount = videos?.length ?? 0;
      _logger.i('🎬 Received sync for playlist: $playlistName ($videoCount videos)');

      // Log the videos received
      if (videos != null && videos.isNotEmpty) {
        _logger.i('📹 Videos in playlist:');
        for (var video in videos) {
          final filename = video['filename'] ?? 'unknown';
          final title = video['title'] ?? filename;
          _logger.i('  - $title');
        }
      }

      // Delta-sync no-op handling.
      //
      // The ETL sends an empty videos[] as a "content unchanged" confirmation
      // when this device's manifest already shows the same videos in the same
      // order (backends include "videos_noop": true to make this explicit).
      // A naive replace here would WIPE our stored playlist (upsertPlaylist
      // deletes existing playlist_videos rows) and leave nothing to play - the
      // classic "device shows synced but doesn't play" failure. So on a no-op
      // we MUST keep the existing content instead of overwriting with empty.
      //
      // The explicit marker is unambiguous. As a defensive fallback (older
      // backends that send empty videos[] without the marker), we also treat an
      // empty incoming list as a no-op when we already hold a non-empty
      // playlist for this id, rather than risk blanking the screen.
      final isExplicitNoop = videoListData['videos_noop'] == true;
      final hasIncomingVideos = videoCount > 0;

      if (!hasIncomingVideos || isExplicitNoop) {
        final existing = await _database.getPlaylist(playlistId);
        if (isExplicitNoop || (existing != null && existing.videos.isNotEmpty)) {
          _logger.i('🔄 Delta no-op: playlist `$playlistName` unchanged '
              '(${existing?.videos.length ?? 0} videos kept on device)');

          // Keep the stored content; just (re)load it so it plays.
          if (existing != null) {
            final loaded = await _playerEngine.loadPlaylist(playlistId);
            if (loaded) {
              _logger.i('✅ Kept existing playlist and loaded into player - ready to play!');
            } else {
              _logger.w('⚠️  Failed to (re)load existing playlist into player');
            }
          }

          return Response.ok(
            jsonEncode({
              'status': 'success',
              'message': 'Playlist unchanged - kept existing device content',
              'playlist_id': playlistId,
              'playlist_name': playlistName,
              'videos_count': existing?.videos.length ?? 0,
              'noop': true,
              'timestamp': DateTime.now().toIso8601String(),
            }),
            headers: {'Content-Type': 'application/json'},
          );
        }
      }

      // Convert the received data to VideoList model and save to database
      try {
        final videoItems = (videos ?? []).map((video) {
          final filename = video['filename'] ?? '';
          final filePath = video['file_path'] ?? '';
          final videoId = video['video_id']?.toString() ?? '';
          
          // Use the signage-specific streaming endpoint (no auth required)
          // Format: http://host:8000/api/v1/signage/stream/{media_id}
          final videoUrl = '${_configService.mediaServiceUrl}/api/v1/signage/stream/$videoId';
          
          return VideoItem(
            id: video['id']?.toString() ?? '',
            videoId: videoId,
            title: video['title']?.toString() ?? filename,
            url: videoUrl,
            sequenceOrder: video['sequence_order'] ?? 0,
            durationMs: video['duration_ms'] ?? 0,
            metadata: {
              'filename': filename,
              'file_path': filePath,
              'thumbnail_url': video['thumbnail_url'],
            },
          );
        }).toList();

        final playlist = VideoList(
          id: playlistId,
          name: playlistName,
          description: videoListData['description'] as String?,
          sourceListId: playlistId,
          lastSyncedAt: DateTime.now(),
          syncVersion: 1,
          isActive: true,
          loopMode: LoopMode.continuous,
          transitionDurationMs: videoListData['transition_duration'] ?? 0,
          videos: videoItems,
        );

        await _database.upsertPlaylist(playlist);
        _logger.i('✅ Playlist saved to database');

        // Auto-load the playlist into the player
        final loaded = await _playerEngine.loadPlaylist(playlistId);
        if (loaded) {
          _logger.i('✅ Playlist loaded into player - ready to play!');
        } else {
          _logger.w('⚠️  Failed to load playlist into player');
        }

      } catch (e, stack) {
        _logger.e('Error saving playlist to database', error: e, stackTrace: stack);
      }
      
      _logger.i('✅ Sync completed successfully');

      return Response.ok(
        jsonEncode({
          'status': 'success',
          'message': 'Playlist synced and loaded',
          'playlist_id': playlistId,
          'playlist_name': playlistName,
          'videos_count': videoCount,
          'timestamp': DateTime.now().toIso8601String(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error processing sync notification', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to process sync notification',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// Assets / manifest endpoint — returns the device's current stored playlist
  /// content (video IDs in sequence order) so the ETL can compute a delta and
  /// avoid re-pushing unchanged assets.
  Future<Response> _handleAssets(Request request) async {
    try {
      _logger.d('📦 Assets/manifest query received');

      final playlists = await _database.getAllPlaylists();
      final result = <String, dynamic>{
        'device_id': _deviceId,
        'playlists': playlists
            .map((pl) => {
                  'playlist_id': pl.sourceListId.isNotEmpty
                      ? pl.sourceListId
                      : pl.id,
                  'name': pl.name,
                  'sync_version': pl.syncVersion,
                  'videos': pl.videos
                      .map((v) => {
                            'video_id': v.videoId,
                            'sequence_order': v.sequenceOrder,
                          })
                      .toList(),
                })
            .toList(),
      };

      return Response.ok(
        jsonEncode(result),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error getting assets manifest', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to get assets manifest',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// Get current configuration endpoint
  Future<Response> _handleGetConfig(Request request) async {
    try {
      _logger.i('📋 Configuration query received');

      return Response.ok(
        jsonEncode({
          'status': 'success',
          'configuration': {
            'backend_ip': _configService.backendIP,
            'discovery_port': _configService.discoveryPort,
            'is_configured': _configService.isConfigured,
            'discovery_service_url': _configService.discoveryServiceUrl,
            'media_service_url': _configService.mediaServiceUrl,
            'gateway_url': _configService.gatewayUrl,
          },
          'device_id': _deviceId,
          'timestamp': DateTime.now().toIso8601String(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    } catch (e, stack) {
      _logger.e('Error getting configuration', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to get configuration',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// Set configuration remotely endpoint
  Future<Response> _handleSetConfig(Request request) async {
    try {
      final body = await request.readAsString();
      final data = jsonDecode(body) as Map<String, dynamic>;

      final backendIP = data['backend_ip'] as String?;
      final discoveryPort = data['discovery_port'] as int?;

      if (backendIP == null || backendIP.isEmpty) {
        return Response.badRequest(
          body: jsonEncode({
            'error': 'Missing required field: backend_ip',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }

      if (discoveryPort == null || discoveryPort < 1 || discoveryPort > 65535) {
        return Response.badRequest(
          body: jsonEncode({
            'error': 'Invalid or missing field: discovery_port (must be 1-65535)',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }

      _logger.i('🔧 Remote configuration update requested');
      _logger.i('   Backend IP: $backendIP');
      _logger.i('   Discovery Port: $discoveryPort');

      // Save the configuration
      final success = await _configService.saveConfiguration(
        backendIP: backendIP,
        discoveryPort: discoveryPort,
      );

      if (success) {
        _logger.i('✅ Configuration updated successfully');
        return Response.ok(
          jsonEncode({
            'status': 'success',
            'message': 'Configuration updated successfully. Please restart the application for changes to take effect.',
            'configuration': {
              'backend_ip': backendIP,
              'discovery_port': discoveryPort,
              'discovery_service_url': 'http://$backendIP:$discoveryPort',
              'media_service_url': 'http://$backendIP:8000',
              'gateway_url': 'http://$backendIP:8080',
            },
            'restart_required': true,
            'timestamp': DateTime.now().toIso8601String(),
          }),
          headers: {'Content-Type': 'application/json'},
        );
      } else {
        _logger.e('❌ Failed to save configuration');
        return Response.internalServerError(
          body: jsonEncode({
            'error': 'Failed to save configuration',
            'message': 'Configuration service returned false',
          }),
          headers: {'Content-Type': 'application/json'},
        );
      }
    } catch (e, stack) {
      _logger.e('Error setting configuration', error: e, stackTrace: stack);
      return Response.internalServerError(
        body: jsonEncode({
          'error': 'Failed to set configuration',
          'message': e.toString(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
    }
  }

  /// 404 handler
  Response _handle404(Request request) {
    return Response.notFound(
      jsonEncode({
        'error': 'Not found',
        'path': request.url.path,
      }),
      headers: {'Content-Type': 'application/json'},
    );
  }

  /// Logging middleware
  Middleware _loggingMiddleware() {
    return (Handler handler) {
      return (Request request) async {
        final startTime = DateTime.now();
        final response = await handler(request);
        final duration = DateTime.now().difference(startTime);

        _logger.d(
          '${request.method} ${request.url.path} -> ${response.statusCode} (${duration.inMilliseconds}ms)',
        );

        return response;
      };
    };
  }

  /// CORS middleware
  Middleware _corsMiddleware() {
    return createMiddleware(
      requestHandler: (Request request) {
        if (request.method == 'OPTIONS') {
          return Response.ok('', headers: _corsHeaders);
        }
        return null;
      },
      responseHandler: (Response response) {
        return response.change(headers: _corsHeaders);
      },
    );
  }

  Map<String, String> get _corsHeaders => {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Origin, Content-Type, Accept, Authorization',
      };

  /// Error handling middleware
  Middleware _errorHandlingMiddleware() {
    return (Handler handler) {
      return (Request request) async {
        try {
          return await handler(request);
        } catch (e, stack) {
          _logger.e('Unhandled error in HTTP handler', error: e, stackTrace: stack);
          return Response.internalServerError(
            body: jsonEncode({
              'error': 'Internal server error',
              'message': e.toString(),
            }),
            headers: {'Content-Type': 'application/json'},
          );
        }
      };
    };
  }
}
