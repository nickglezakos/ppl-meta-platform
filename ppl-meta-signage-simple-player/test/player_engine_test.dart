import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/models/video_list.dart' show VideoList, VideoItem, LoopMode;
import 'package:signage_simple_player/models/playback_models.dart';

@GenerateMocks([PlaylistDatabase])
import 'player_engine_test.mocks.dart';

void main() {
  late SignagePlayerEngine playerEngine;
  late MockPlaylistDatabase mockDatabase;
  late Logger logger;

  setUp(() {
    mockDatabase = MockPlaylistDatabase();
    logger = Logger(level: Level.off); // Disable logging in tests
    playerEngine = SignagePlayerEngine(
      database: mockDatabase,
      logger: logger,
      preloadCount: 2,
    );
  });

  tearDown(() {
    playerEngine.dispose();
  });

  group('SignagePlayerEngine', () {
    group('Initialization', () {
      test('starts in stopped state', () {
        expect(playerEngine.state, equals(PlaybackState.stopped));
        expect(playerEngine.isStopped, isTrue);
        expect(playerEngine.isPlaying, isFalse);
        expect(playerEngine.isPaused, isFalse);
      });

      test('has no playlist loaded initially', () {
        expect(playerEngine.currentPlaylist, isNull);
        expect(playerEngine.currentVideo, isNull);
        expect(playerEngine.currentIndex, equals(0));
      });

      test('defaults to continuous loop mode', () {
        expect(playerEngine.loopMode, equals(LoopMode.continuous));
      });
    });

    group('loadPlaylist', () {
      test('loads playlist from database successfully', () async {
        final playlist = VideoList(
          id: 'playlist-1',
          name: 'Test Playlist',
          sourceListId: 'source-1',
          videos: [
            VideoItem(
              id: 'item-1',
              videoId: 'video-1',
              title: 'Video 1',
              url: 'http://example.com/video1.mp4',
              sequenceOrder: 0,
              durationMs: 120000,
            ),
            VideoItem(
              id: 'item-2',
              videoId: 'video-2',
              title: 'Video 2',
              url: 'http://example.com/video2.mp4',
              sequenceOrder: 1,
              durationMs: 180000,
            ),
          ],
        );

        when(mockDatabase.getPlaylist('playlist-1')).thenAnswer((_) async => playlist);

        final result = await playerEngine.loadPlaylist('playlist-1');

        expect(result, isTrue);
        expect(playerEngine.currentPlaylist, equals(playlist));
        expect(playerEngine.currentIndex, equals(0));
        expect(playerEngine.state, equals(PlaybackState.stopped));
      });

      test('returns false when playlist not found', () async {
        when(mockDatabase.getPlaylist('missing-playlist')).thenAnswer((_) async => null);

        final result = await playerEngine.loadPlaylist('missing-playlist');

        expect(result, isFalse);
        expect(playerEngine.state, equals(PlaybackState.error));
        expect(playerEngine.currentPlaylist, isNull);
      });

      test('returns false when playlist is empty', () async {
        final emptyPlaylist = VideoList(
          id: 'empty-playlist',
          name: 'Empty Playlist',
          sourceListId: 'source-empty',
          videos: [],
        );

        when(mockDatabase.getPlaylist('empty-playlist'))
            .thenAnswer((_) async => emptyPlaylist);

        final result = await playerEngine.loadPlaylist('empty-playlist');

        expect(result, isFalse);
        expect(playerEngine.state, equals(PlaybackState.error));
      });

      test('handles database errors gracefully', () async {
        when(mockDatabase.getPlaylist(any))
            .thenThrow(Exception('Database error'));

        final result = await playerEngine.loadPlaylist('playlist-1');

        expect(result, isFalse);
        expect(playerEngine.state, equals(PlaybackState.error));
      });
    });

    group('Loop Modes', () {
      test('can set continuous loop mode', () {
        playerEngine.setLoopMode(LoopMode.continuous);
        expect(playerEngine.loopMode, equals(LoopMode.continuous));
      });

      test('can set once loop mode', () {
        playerEngine.setLoopMode(LoopMode.once);
        expect(playerEngine.loopMode, equals(LoopMode.once));
      });

      test('can set single loop mode', () {
        playerEngine.setLoopMode(LoopMode.single);
        expect(playerEngine.loopMode, equals(LoopMode.single));
      });
    });

    group('Playback Status', () {
      test('returns correct status when stopped', () {
        final status = playerEngine.getPlaybackStatus('test-device');

        expect(status.deviceId, equals('test-device'));
        expect(status.playbackState, equals(PlaybackState.stopped));
        expect(status.currentVideo, isNull);
        expect(status.playlist, isNull);
      });

      test('returns progress information when available', () {
        expect(playerEngine.currentPosition, equals(Duration.zero));
        expect(playerEngine.currentDuration, equals(Duration.zero));
        expect(playerEngine.progressPercent, equals(0.0));
      });
    });

    group('State Management', () {
      test('notifies listeners on state changes', () {
        var notified = false;
        playerEngine.addListener(() {
          notified = true;
        });

        playerEngine.setLoopMode(LoopMode.once);

        expect(notified, isTrue);
      });

      test('provides correct state getters', () {
        expect(playerEngine.isStopped, isTrue);
        expect(playerEngine.isPlaying, isFalse);
        expect(playerEngine.isPaused, isFalse);
        expect(playerEngine.isLoading, isFalse);
        expect(playerEngine.hasError, isFalse);
      });
    });

    group('Current Video Info', () {
      test('returns null when no playlist loaded', () {
        expect(playerEngine.currentVideo, isNull);
        expect(playerEngine.nextVideo, isNull);
      });

      test('returns correct video when playlist loaded', () async {
        final playlist = VideoList(
          id: 'playlist-1',
          name: 'Test Playlist',
          sourceListId: 'source-1',
          videos: [
            VideoItem(
              id: 'item-1',
              videoId: 'video-1',
              title: 'Video 1',
              url: 'http://example.com/video1.mp4',
              sequenceOrder: 0,
              durationMs: 120000,
            ),
            VideoItem(
              id: 'item-2',
              videoId: 'video-2',
              title: 'Video 2',
              url: 'http://example.com/video2.mp4',
              sequenceOrder: 1,
              durationMs: 180000,
            ),
          ],
        );

        when(mockDatabase.getPlaylist('playlist-1')).thenAnswer((_) async => playlist);
        await playerEngine.loadPlaylist('playlist-1');

        expect(playerEngine.currentVideo?.videoId, equals('video-1'));
        expect(playerEngine.nextVideo?.videoId, equals('video-2'));
      });
    });

    group('Error Handling', () {
      test('handles play without playlist gracefully', () async {
        final result = await playerEngine.play();
        expect(result, isFalse);
      });

      test('handles next without playlist gracefully', () async {
        final result = await playerEngine.next();
        expect(result, isFalse);
      });

      test('handles previous without playlist gracefully', () async {
        final result = await playerEngine.previous();
        expect(result, isFalse);
      });

      test('pause does nothing when not playing', () async {
        // Should not throw
        await playerEngine.pause();
        expect(playerEngine.state, equals(PlaybackState.stopped));
      });

      test('resume does nothing when not paused', () async {
        // Should not throw
        await playerEngine.resume();
        expect(playerEngine.state, equals(PlaybackState.stopped));
      });
    });

    group('Cleanup', () {
      test('dispose cleans up resources', () {
        // Dispose is already called in tearDown, so just verify it can be called
        final engine = SignagePlayerEngine(
          database: mockDatabase,
          logger: logger,
        );
        engine.dispose();
        // Should not throw and should clean up controllers
      });

      test('stop resets index to 0', () async {
        final playlist = VideoList(
          id: 'playlist-1',
          name: 'Test Playlist',
          sourceListId: 'source-1',
          videos: [
            VideoItem(
              id: 'item-1',
              videoId: 'video-1',
              title: 'Video 1',
              url: 'http://example.com/video1.mp4',
              sequenceOrder: 0,
              durationMs: 120000,
            ),
          ],
        );

        when(mockDatabase.getPlaylist('playlist-1')).thenAnswer((_) async => playlist);
        await playerEngine.loadPlaylist('playlist-1');

        await playerEngine.stop();

        expect(playerEngine.currentIndex, equals(0));
        expect(playerEngine.state, equals(PlaybackState.stopped));
      });
    });
  });
}
