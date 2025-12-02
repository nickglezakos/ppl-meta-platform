import 'package:flutter_test/flutter_test.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:signage_simple_player/models/playback_history.dart';
import 'package:uuid/uuid.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  late PlaylistDatabase database;

  setUpAll(() {
    // Initialize FFI for testing
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  setUp(() async {
    // Get a new instance for each test
    database = PlaylistDatabase();
  });

  tearDown(() async {
    await database.close();
  });

  group('Playlist Operations', () {
    test('upsert and get playlist', () async {
      final playlist = VideoList(
        id: const Uuid().v4(),
        name: 'Test Playlist',
        description: 'Test Description',
        sourceListId: 'source-123',
        syncVersion: 1,
        isActive: true,
        loopMode: LoopMode.continuous,
        transitionDurationMs: 500,
        videos: [
          VideoItem(
            id: const Uuid().v4(),
            videoId: 'video-1',
            title: 'Video 1',
            url: 'https://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 120000,
          ),
          VideoItem(
            id: const Uuid().v4(),
            videoId: 'video-2',
            title: 'Video 2',
            url: 'https://example.com/video2.mp4',
            sequenceOrder: 1,
            durationMs: 150000,
          ),
        ],
      );

      await database.upsertPlaylist(playlist);
      
      final retrieved = await database.getPlaylist(playlist.id);
      
      expect(retrieved, isNotNull);
      expect(retrieved!.id, equals(playlist.id));
      expect(retrieved.name, equals(playlist.name));
      expect(retrieved.videos.length, equals(2));
      expect(retrieved.videos[0].title, equals('Video 1'));
      expect(retrieved.videos[1].title, equals('Video 2'));
    });

    test('get all playlists', () async {
      final playlist1 = VideoList(
        id: const Uuid().v4(),
        name: 'Playlist 1',
        sourceListId: 'source-1',
        videos: [],
      );
      
      final playlist2 = VideoList(
        id: const Uuid().v4(),
        name: 'Playlist 2',
        sourceListId: 'source-2',
        isActive: false,
        videos: [],
      );

      await database.upsertPlaylist(playlist1);
      await database.upsertPlaylist(playlist2);
      
      final allPlaylists = await database.getAllPlaylists();
      expect(allPlaylists.length, equals(2));
      
      final activePlaylists = await database.getAllPlaylists(activeOnly: true);
      expect(activePlaylists.length, equals(1));
      expect(activePlaylists.first.name, equals('Playlist 1'));
    });

    test('delete playlist', () async {
      final playlist = VideoList(
        id: const Uuid().v4(),
        name: 'To Delete',
        sourceListId: 'source-1',
        videos: [],
      );

      await database.upsertPlaylist(playlist);
      
      final exists = await database.getPlaylist(playlist.id);
      expect(exists, isNotNull);
      
      await database.deletePlaylist(playlist.id);
      
      final deleted = await database.getPlaylist(playlist.id);
      expect(deleted, isNull);
    });

    test('update playlist videos', () async {
      final playlistId = const Uuid().v4();
      
      final playlist1 = VideoList(
        id: playlistId,
        name: 'Test',
        sourceListId: 'source-1',
        videos: [
          VideoItem(
            id: const Uuid().v4(),
            videoId: 'video-1',
            title: 'Video 1',
            url: 'https://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 120000,
          ),
        ],
      );

      await database.upsertPlaylist(playlist1);
      
      // Update with different videos
      final playlist2 = VideoList(
        id: playlistId,
        name: 'Test',
        sourceListId: 'source-1',
        videos: [
          VideoItem(
            id: const Uuid().v4(),
            videoId: 'video-2',
            title: 'Video 2',
            url: 'https://example.com/video2.mp4',
            sequenceOrder: 0,
            durationMs: 150000,
          ),
          VideoItem(
            id: const Uuid().v4(),
            videoId: 'video-3',
            title: 'Video 3',
            url: 'https://example.com/video3.mp4',
            sequenceOrder: 1,
            durationMs: 180000,
          ),
        ],
      );

      await database.upsertPlaylist(playlist2);
      
      final updated = await database.getPlaylist(playlistId);
      expect(updated!.videos.length, equals(2));
      expect(updated.videos[0].videoId, equals('video-2'));
      expect(updated.videos[1].videoId, equals('video-3'));
    });
  });

  group('History Operations', () {
    test('insert and query history', () async {
      final entry = PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-1',
        videoTitle: 'Test Video',
        playlistId: 'playlist-1',
        playlistName: 'Test Playlist',
        startedAt: DateTime.now(),
        deviceId: 'device-123',
        createdAt: DateTime.now(),
      );

      final insertedId = await database.insertHistory(entry);
      expect(insertedId, equals(entry.id));
      
      final history = await database.queryHistory(limit: 10);
      expect(history.length, equals(1));
      expect(history.first.videoId, equals('video-1'));
    });

    test('update history entry', () async {
      final entry = PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-1',
        videoTitle: 'Test Video',
        playlistId: 'playlist-1',
        startedAt: DateTime.now(),
        deviceId: 'device-123',
        createdAt: DateTime.now(),
      );

      await database.insertHistory(entry);
      
      final completedAt = DateTime.now();
      await database.updateHistory(entry.id, {
        'completed_at': completedAt.toIso8601String(),
        'duration_played_ms': 120000,
        'completion_percent': 100.0,
      });
      
      final history = await database.queryHistory(limit: 1);
      expect(history.first.completedAt, isNotNull);
      expect(history.first.durationPlayedMs, equals(120000));
      expect(history.first.completionPercent, equals(100.0));
    });

    test('query history with filters', () async {
      final now = DateTime.now();
      
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-1',
        videoTitle: 'Video 1',
        playlistId: 'playlist-1',
        startedAt: now.subtract(const Duration(hours: 2)),
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-2',
        videoTitle: 'Video 2',
        playlistId: 'playlist-2',
        startedAt: now.subtract(const Duration(hours: 1)),
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      final allHistory = await database.queryHistory();
      expect(allHistory.length, equals(2));
      
      final playlist1History = await database.queryHistory(playlistId: 'playlist-1');
      expect(playlist1History.length, equals(1));
      expect(playlist1History.first.videoId, equals('video-1'));
      
      final video2History = await database.queryHistory(videoId: 'video-2');
      expect(video2History.length, equals(1));
      expect(video2History.first.videoTitle, equals('Video 2'));
    });

    test('count history entries', () async {
      final now = DateTime.now();
      
      for (int i = 0; i < 5; i++) {
        await database.insertHistory(PlaybackHistoryEntry(
          id: const Uuid().v4(),
          videoId: 'video-$i',
          videoTitle: 'Video $i',
          playlistId: 'playlist-1',
          startedAt: now.subtract(Duration(hours: i)),
          deviceId: 'device-123',
          createdAt: now,
        ));
      }
      
      final count = await database.countHistory();
      expect(count, equals(5));
      
      final playlistCount = await database.countHistory(playlistId: 'playlist-1');
      expect(playlistCount, equals(5));
    });

    test('get playback summary', () async {
      final now = DateTime.now();
      
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-1',
        videoTitle: 'Video 1',
        playlistId: 'playlist-1',
        startedAt: now,
        durationPlayedMs: 120000,
        completionPercent: 100.0,
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-1',
        videoTitle: 'Video 1',
        playlistId: 'playlist-1',
        startedAt: now,
        durationPlayedMs: 120000,
        completionPercent: 100.0,
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'video-2',
        videoTitle: 'Video 2',
        playlistId: 'playlist-1',
        startedAt: now,
        durationPlayedMs: 60000,
        completionPercent: 50.0,
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      final summary = await database.getPlaybackSummary();
      
      expect(summary.totalPlaybackTimeMs, equals(300000)); // 120k + 120k + 60k
      expect(summary.uniqueVideosPlayed, equals(2));
      expect(summary.averageCompletionRate, closeTo(83.33, 0.01));
      expect(summary.mostPlayedVideo, isNotNull);
      expect(summary.mostPlayedVideo!.videoId, equals('video-1'));
      expect(summary.mostPlayedVideo!.playCount, equals(2));
    });

    test('cleanup old history', () async {
      final now = DateTime.now();
      
      // Insert recent entry
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'recent',
        videoTitle: 'Recent Video',
        playlistId: 'playlist-1',
        startedAt: now,
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      // Insert old entry
      await database.insertHistory(PlaybackHistoryEntry(
        id: const Uuid().v4(),
        videoId: 'old',
        videoTitle: 'Old Video',
        playlistId: 'playlist-1',
        startedAt: now.subtract(const Duration(days: 100)),
        deviceId: 'device-123',
        createdAt: now,
      ));
      
      final beforeCleanup = await database.countHistory();
      expect(beforeCleanup, equals(2));
      
      await database.cleanupOldHistory(retentionDays: 90);
      
      final afterCleanup = await database.countHistory();
      expect(afterCleanup, equals(1));
      
      final remaining = await database.queryHistory();
      expect(remaining.first.videoId, equals('recent'));
    });
  });
}
