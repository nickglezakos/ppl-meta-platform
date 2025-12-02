import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/services/http_server.dart';
import 'package:signage_simple_player/models/playback_models.dart';
import 'package:signage_simple_player/models/playback_history.dart';
import 'package:signage_simple_player/models/video_list.dart' show VideoItem, LoopMode;

@GenerateMocks([PlaylistDatabase, SignagePlayerEngine])
import 'http_server_test.mocks.dart';

void main() {
  late SignageHttpServer server;
  late MockPlaylistDatabase mockDatabase;
  late MockSignagePlayerEngine mockPlayerEngine;
  late Logger logger;

  const testDeviceId = 'test-device-123';
  const testPort = 8999; // Use different port for testing

  setUp(() {
    mockDatabase = MockPlaylistDatabase();
    mockPlayerEngine = MockSignagePlayerEngine();
    logger = Logger(level: Level.off);

    server = SignageHttpServer(
      database: mockDatabase,
      playerEngine: mockPlayerEngine,
      logger: logger,
      deviceId: testDeviceId,
      port: testPort,
    );
  });

  tearDown(() async {
    if (server.isRunning) {
      await server.stop();
    }
  });

  group('Server Lifecycle', () {
    test('starts and stops successfully', () async {
      expect(server.isRunning, false);

      await server.start();
      expect(server.isRunning, true);

      await server.stop();
      expect(server.isRunning, false);
    });

    test('does not start twice', () async {
      await server.start();
      expect(server.isRunning, true);

      // Second start should not throw
      await server.start();
      expect(server.isRunning, true);
    });

    test('stop is idempotent', () async {
      await server.start();
      await server.stop();

      // Second stop should not throw
      await server.stop();
      expect(server.isRunning, false);
    });
  });

  group('Health Endpoint', () {
    test('returns healthy status', () async {
      await server.start();

      final response = await _makeHttpRequest('GET', '/health');
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['status'], 'healthy');
      expect(body['device_id'], testDeviceId);
      expect(body['service'], isNotNull);
      expect(body['version'], isNotNull);
      expect(body['timestamp'], isNotNull);
    });
  });

  group('Status Endpoint', () {
    test('returns current playback status', () async {
      final mockStatus = PlaybackStatus(
        deviceId: testDeviceId,
        playbackState: PlaybackState.playing,
      );

      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(mockStatus);

      await server.start();

      final response = await _makeHttpRequest('GET', '/api/v1/status');
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['device_id'], testDeviceId);
      expect(body['playback_state'], 'playing');
    });
  });

  group('History Query Endpoint', () {
    test('returns history with default parameters', () async {
      final mockHistory = [
        PlaybackHistoryEntry(
          id: '1',
          deviceId: testDeviceId,
          videoId: 'video-1',
          videoTitle: 'Test Video',
          playlistId: 'playlist-1',
          startedAt: DateTime.now(),
          completedAt: DateTime.now().add(const Duration(minutes: 2)),
          durationPlayedMs: 120000,
          completionPercent: 100.0,
          createdAt: DateTime.now(),
        ),
      ];

      when(mockDatabase.queryHistory(
        limit: 50,
        offset: 0,
      )).thenAnswer((_) async => <PlaybackHistoryEntry>[...mockHistory]);

      when(mockDatabase.countHistory()).thenAnswer((_) async => 1);

      await server.start();

      final response = await _makeHttpRequest('GET', '/api/v1/history');
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['history'], hasLength(1));
      expect(body['count'], 1);
      expect(body['limit'], 50);
      expect(body['offset'], 0);
    });

    test('handles query parameters', () async {
      when(mockDatabase.queryHistory(
        videoId: 'video-1',
        playlistId: 'playlist-1',
        limit: 10,
        offset: 5,
      )).thenAnswer((_) async => []);

      when(mockDatabase.countHistory(
        videoId: 'video-1',
        playlistId: 'playlist-1',
      )).thenAnswer((_) async => 0);

      await server.start();

      final response = await _makeHttpRequest(
        'GET',
        '/api/v1/history?video_id=video-1&playlist_id=playlist-1&limit=10&offset=5',
      );
      expect(response.statusCode, 200);

      verify(mockDatabase.queryHistory(
        videoId: 'video-1',
        playlistId: 'playlist-1',
        limit: 10,
        offset: 5,
      )).called(1);
    });
  });

  group('History Summary Endpoint', () {
    test('returns playback summary', () async {
      final mockSummary = PlaybackSummary(
        totalPlaybackTimeMs: 12000000,
        uniqueVideosPlayed: 25,
        averageCompletionRate: 95.5,
      );

      when(mockDatabase.getPlaybackSummary()).thenAnswer((_) async => mockSummary);

      await server.start();

      final response = await _makeHttpRequest('GET', '/api/v1/history/summary');
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['unique_videos_played'], 25);
      expect(body['average_completion_rate'], 95.5);
    });
  });

  group('Control Endpoint - Basic Commands', () {
    test('handles play command', () async {
      when(mockPlayerEngine.play()).thenAnswer((_) async => true);
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'play'},
      );
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['success'], true);
      expect(body['command'], 'play');
      expect(body['message'], contains('started'));

      verify(mockPlayerEngine.play()).called(1);
    });

    test('handles pause command', () async {
      when(mockPlayerEngine.pause()).thenAnswer((_) async {});
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'pause'},
      );
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['success'], true);
      expect(body['command'], 'pause');

      verify(mockPlayerEngine.pause()).called(1);
    });

    test('handles resume command', () async {
      when(mockPlayerEngine.resume()).thenAnswer((_) async {});
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'resume'},
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.resume()).called(1);
    });

    test('handles stop command', () async {
      when(mockPlayerEngine.stop()).thenAnswer((_) async {});
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'stop'},
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.stop()).called(1);
    });

    test('handles next command', () async {
      when(mockPlayerEngine.next()).thenAnswer((_) async => true);
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'next'},
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.next()).called(1);
    });

    test('handles previous command', () async {
      when(mockPlayerEngine.previous()).thenAnswer((_) async => true);
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'previous'},
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.previous()).called(1);
    });
  });

  group('Control Endpoint - Advanced Commands', () {
    test('handles load_playlist command', () async {
      when(mockPlayerEngine.loadPlaylist('playlist-1'))
          .thenAnswer((_) async => true);
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {
          'command': 'load_playlist',
          'playlist_id': 'playlist-1',
        },
      );
      expect(response.statusCode, 200);

      final body = jsonDecode(response.body);
      expect(body['success'], true);

      verify(mockPlayerEngine.loadPlaylist('playlist-1')).called(1);
    });

    test('load_playlist requires playlist_id', () async {
      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'load_playlist'},
      );
      expect(response.statusCode, 400);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('playlist_id'));
    });

    test('handles seek command', () async {
      when(mockPlayerEngine.seekTo(any)).thenAnswer((_) async {});
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {
          'command': 'seek',
          'position_ms': 30000,
        },
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.seekTo(const Duration(milliseconds: 30000)))
          .called(1);
    });

    test('seek requires position_ms', () async {
      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'seek'},
      );
      expect(response.statusCode, 400);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('position_ms'));
    });

    test('handles set_loop_mode command', () async {
      when(mockPlayerEngine.setLoopMode(any)).thenAnswer((_) {});
      when(mockPlayerEngine.getPlaybackStatus(testDeviceId))
          .thenReturn(_mockStatus());

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {
          'command': 'set_loop_mode',
          'loop_mode': 'continuous',
        },
      );
      expect(response.statusCode, 200);

      verify(mockPlayerEngine.setLoopMode(LoopMode.continuous)).called(1);
    });

    test('set_loop_mode validates mode values', () async {
      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {
          'command': 'set_loop_mode',
          'loop_mode': 'invalid_mode',
        },
      );
      expect(response.statusCode, 400);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('Invalid loop_mode'));
    });
  });

  group('Control Endpoint - Error Handling', () {
    test('requires command field', () async {
      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {},
      );
      expect(response.statusCode, 400);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('command'));
    });

    test('rejects unknown commands', () async {
      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'unknown_command'},
      );
      expect(response.statusCode, 400);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('Unknown command'));
      expect(body['supported_commands'], isNotNull);
    });

    test('handles player engine errors gracefully', () async {
      when(mockPlayerEngine.play())
          .thenThrow(Exception('Player engine failure'));

      await server.start();

      final response = await _makeHttpRequest(
        'POST',
        '/api/v1/control',
        body: {'command': 'play'},
      );
      expect(response.statusCode, 500);

      final body = jsonDecode(response.body);
      expect(body['error'], isNotNull);
    });
  });

  group('Error Handling', () {
    test('returns 404 for unknown paths', () async {
      await server.start();

      final response = await _makeHttpRequest('GET', '/unknown/path');
      expect(response.statusCode, 404);

      final body = jsonDecode(response.body);
      expect(body['error'], 'Not found');
      expect(body['path'], 'unknown/path');
    });

    test('handles database errors in history query', () async {
      when(mockDatabase.queryHistory(limit: anyNamed('limit'), offset: anyNamed('offset')))
          .thenThrow(Exception('Database error'));

      await server.start();

      final response = await _makeHttpRequest('GET', '/api/v1/history');
      expect(response.statusCode, 500);

      final body = jsonDecode(response.body);
      expect(body['error'], contains('Failed to query history'));
    });
  });
}

/// Helper function to make HTTP requests to the server
Future<HttpResponse> _makeHttpRequest(String method, String path, {Map<String, dynamic>? body}) async {
  const port = 8999; // Test port
  final client = HttpClient();
  try {
    final uri = Uri.parse('http://localhost:$port$path');
    late HttpClientRequest request;
    
    switch (method.toUpperCase()) {
      case 'GET':
        request = await client.getUrl(uri);
        break;
      case 'POST':
        request = await client.postUrl(uri);
        if (body != null) {
          request.headers.contentType = ContentType.json;
          request.write(jsonEncode(body));
        }
        break;
      default:
        throw UnsupportedError('Method $method not supported');
    }
    
    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();
    
    return HttpResponse(
      statusCode: response.statusCode,
      body: responseBody,
    );
  } finally {
    client.close();
  }
}

/// Simple HTTP response wrapper
class HttpResponse {
  final int statusCode;
  final String body;
  
  HttpResponse({required this.statusCode, required this.body});
}

/// Helper to create a mock playback status
PlaybackStatus _mockStatus() {
  const deviceId = 'test-device-123'; // Test device ID
  return PlaybackStatus(
    deviceId: deviceId,
    playbackState: PlaybackState.playing,
  );
}
