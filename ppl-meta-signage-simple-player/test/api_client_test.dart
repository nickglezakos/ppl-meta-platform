import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:signage_simple_player/models/playback_history.dart';
import 'package:signage_simple_player/models/playback_models.dart';

@GenerateMocks([Dio])
import 'api_client_test.mocks.dart';

void main() {
  late SignageApiClient apiClient;
  late MockDio mockDio;
  late Logger logger;

  setUp(() {
    mockDio = MockDio();
    logger = Logger(level: Level.off); // Disable logging in tests
    apiClient = SignageApiClient(
      baseUrl: 'http://test-backend.com',
      deviceId: 'test-device-123',
      logger: logger,
      dio: mockDio,
    );
  });

  group('syncPlaylist', () {
    test('returns VideoList when playlist available', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/etl/sync'),
        statusCode: 200,
        data: {
          'version': '1.0',
          'videos': [
            {
              'id': 'video-1',
              'title': 'Test Video',
              'url': 'http://example.com/video.mp4',
              'duration_ms': 120000,
            }
          ],
        },
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final result = await apiClient.syncPlaylist();

      expect(result, isNotNull);
      expect(result!.videos, hasLength(1));
      expect(result.videos.first.id, equals('video-1'));
    });

    test('returns null when no playlist (304)', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/etl/sync'),
        statusCode: 304,
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final result = await apiClient.syncPlaylist();

      expect(result, isNull);
    });

    test('returns null on network error', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/api/v1/signage/etl/sync'),
        type: DioExceptionType.connectionTimeout,
      ));

      final result = await apiClient.syncPlaylist();

      expect(result, isNull);
    });
  });

  group('sendControlCommand', () {
    test('successfully sends control command', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/playback/control'),
        statusCode: 200,
        data: {
          'device_id': 'test-device-123',
          'playback_state': 'playing',
          'current_video': {
            'video_id': 'video-1',
            'title': 'Test Video',
            'position_ms': 0,
            'duration_ms': 120000,
            'progress_percent': 0.0,
          },
          'playlist': {
            'id': 'playlist-123',
            'name': 'Test Playlist',
            'current_index': 0,
            'total_videos': 5,
          },
          'history_count': 0,
          'upcoming_count': 4,
        },
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final result = await apiClient.sendControlCommand(
        command: 'play',
        parameters: {'playlist_id': 'playlist-123'},
      );

      expect(result.playbackState, equals(PlaybackState.playing));
      expect(result.currentVideo, isNotNull);
      expect(result.currentVideo!.videoId, equals('video-1'));
    });

    test('throws DioException on command failure', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/playback/control'),
        statusCode: 400,
        data: {'error': 'Invalid command'},
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      expect(
        () => apiClient.sendControlCommand(command: 'invalid'),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('reportStatus', () {
    test('successfully reports status', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/status/report'),
        statusCode: 200,
        data: {'message': 'Status received'},
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final state = PlaybackStatus(
        deviceId: 'test-device-123',
        playbackState: PlaybackState.playing,
        currentVideo: CurrentVideoInfo(
          videoId: 'video-1',
          title: 'Test Video',
          positionMs: 1000,
          durationMs: 120000,
          progressPercent: 0.8,
        ),
        playlist: PlaylistInfo(
          id: 'playlist-123',
          name: 'Test Playlist',
          currentIndex: 0,
          totalVideos: 5,
        ),
      );

      await apiClient.reportStatus(currentState: state);

      verify(mockDio.post(
        any,
        data: anyNamed('data'),
      )).called(1);
    });

    test('does not throw on failure', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/api/v1/signage/status/report'),
        type: DioExceptionType.connectionTimeout,
      ));

      final state = PlaybackStatus(
        deviceId: 'test-device-123',
        playbackState: PlaybackState.stopped,
      );

      // Should not throw
      await apiClient.reportStatus(currentState: state);
    });
  });

  group('uploadHistory', () {
    test('successfully uploads history', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/history/upload'),
        statusCode: 200,
        data: {'message': 'History uploaded successfully'},
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final entries = [
        PlaybackHistoryEntry(
          id: '1',
          videoId: 'video-1',
          playedAt: DateTime.now(),
          completionPercent: 100.0,
        ),
      ];

      await apiClient.uploadHistory(entries: entries);

      verify(mockDio.post(
        any,
        data: anyNamed('data'),
      )).called(1);
    });

    test('throws DioException on upload failure', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/history/upload'),
        statusCode: 500,
        data: {'error': 'Internal server error'},
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      final entries = [
        PlaybackHistoryEntry(
          id: '1',
          videoId: 'video-1',
          playedAt: DateTime.now(),
          completionPercent: 100.0,
        ),
      ];

      expect(
        () => apiClient.uploadHistory(entries: entries),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('checkConnectivity', () {
    test('returns true when backend is reachable', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/health'),
        statusCode: 200,
        data: {'status': 'ok'},
      );

      when(mockDio.get(any)).thenAnswer((_) async => mockResponse);

      final result = await apiClient.checkConnectivity();

      expect(result, isTrue);
    });

    test('returns false when backend is unreachable', () async {
      when(mockDio.get(any)).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/health'),
        type: DioExceptionType.connectionTimeout,
      ));

      final result = await apiClient.checkConnectivity();

      expect(result, isFalse);
    });
  });

  group('getServerInfo', () {
    test('returns server info successfully', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/info'),
        statusCode: 200,
        data: {
          'version': '1.0.0',
          'capabilities': ['playlist_sync', 'history_tracking'],
        },
      );

      when(mockDio.get(any)).thenAnswer((_) async => mockResponse);

      final result = await apiClient.getServerInfo();

      expect(result['version'], equals('1.0.0'));
      expect(result['capabilities'], hasLength(2));
    });
  });

  group('getVideoMetadata', () {
    test('returns video metadata successfully', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/video/video-1/metadata'),
        statusCode: 200,
        data: {
          'id': 'video-1',
          'title': 'Test Video',
          'duration_ms': 120000,
          'file_size_bytes': 104857600,
        },
      );

      when(mockDio.get(any)).thenAnswer((_) async => mockResponse);

      final result = await apiClient.getVideoMetadata(videoId: 'video-1');

      expect(result['id'], equals('video-1'));
      expect(result['duration_ms'], equals(120000));
    });
  });

  group('reportError', () {
    test('successfully reports error', () async {
      final mockResponse = Response(
        requestOptions: RequestOptions(path: '/api/v1/signage/error/report'),
        statusCode: 200,
        data: {'message': 'Error received'},
      );

      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenAnswer((_) async => mockResponse);

      await apiClient.reportError(
        errorType: 'Test Error',
        errorMessage: 'Test error message',
      );

      verify(mockDio.post(
        any,
        data: anyNamed('data'),
      )).called(1);
    });

    test('does not throw on failure', () async {
      when(mockDio.post(
        any,
        data: anyNamed('data'),
      )).thenThrow(DioException(
        requestOptions: RequestOptions(path: '/api/v1/signage/error/report'),
        type: DioExceptionType.connectionTimeout,
      ));

      // Should not throw
      await apiClient.reportError(
        errorType: 'Test Error',
        errorMessage: 'Test error message',
      );
    });
  });
}
