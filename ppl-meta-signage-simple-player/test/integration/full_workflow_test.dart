import 'package:flutter_test/flutter_test.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/services/sync_service.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import 'full_workflow_test.mocks.dart';

@GenerateMocks([SignageApiClient])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Integration - Full Workflow', () {
    late PlaylistDatabase database;
    late MockSignageApiClient mockApiClient;
    late SyncService syncService;
    late SignagePlayerEngine playerEngine;
    late HistoryTrackingService historyService;
    late Logger logger;

    setUp(() async {
      logger = Logger(level: Level.off);
      
      // Use in-memory database for testing
      database = PlaylistDatabase(databasePath: ':memory:');
      await database.initialize();
      
      mockApiClient = MockSignageApiClient();
      
      syncService = SyncService(
        apiClient: mockApiClient,
        database: database,
        logger: logger,
      );
      
      playerEngine = SignagePlayerEngine(
        database: database,
        logger: logger,
      );
      
      historyService = HistoryTrackingService(
        apiClient: mockApiClient,
        logger: logger,
      );
    });

    tearDown(() async {
      await playerEngine.dispose();
      await database.close();
    });

    test('Complete workflow: sync -> load -> play -> track', () async {
      // 1. Create mock playlist
      final mockPlaylist = VideoList(
        id: 'test-playlist-1',
        name: 'Test Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [
          VideoItem(
            id: 'video-1',
            videoId: 'vid-1',
            title: 'Test Video 1',
            url: 'http://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 30000,
          ),
          VideoItem(
            id: 'video-2',
            videoId: 'vid-2',
            title: 'Test Video 2',
            url: 'http://example.com/video2.mp4',
            sequenceOrder: 1,
            durationMs: 45000,
          ),
        ],
      );

      // 2. Mock API to return playlist
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => mockPlaylist);

      // 3. Sync playlist
      final syncResult = await syncService.syncPlaylists();
      expect(syncResult.success, true);
      expect(syncResult.playlistsSynced, 1);
      expect(syncResult.videosAdded, 2);

      // 4. Verify playlist in database
      final savedPlaylists = await database.getAllPlaylists();
      expect(savedPlaylists.length, 1);
      expect(savedPlaylists.first.id, 'test-playlist-1');
      expect(savedPlaylists.first.videos.length, 2);

      // 5. Load playlist into player
      await playerEngine.loadPlaylist('test-playlist-1');
      expect(playerEngine.currentPlaylist, isNotNull);
      expect(playerEngine.currentPlaylist!.id, 'test-playlist-1');
      expect(playerEngine.totalVideos, 2);

      // 6. Track video playback start
      historyService.trackVideoStart(
        playlistId: 'test-playlist-1',
        videoId: 'video-1',
      );
      expect(historyService.hasActivePlayback, true);

      // 7. Track video completion
      historyService.trackVideoComplete(
        playlistId: 'test-playlist-1',
        videoId: 'video-1',
        actualDurationMs: 30000,
      );
      expect(historyService.hasActivePlayback, false);

      // 8. Verify history tracking
      final history = historyService.getPendingHistory();
      expect(history.length, 1);
      expect(history.first.videoId, 'video-1');
      expect(history.first.completionStatus, 'completed');
    });

    test('Sync update workflow: detect and apply changes', () async {
      // 1. Initial sync with 2 videos
      final initialPlaylist = VideoList(
        id: 'playlist-1',
        name: 'Initial Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [
          VideoItem(
            id: 'video-1',
            videoId: 'vid-1',
            title: 'Video 1',
            url: 'http://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 30000,
          ),
          VideoItem(
            id: 'video-2',
            videoId: 'vid-2',
            title: 'Video 2',
            url: 'http://example.com/video2.mp4',
            sequenceOrder: 1,
            durationMs: 45000,
          ),
        ],
      );

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => initialPlaylist);
      
      final initialSync = await syncService.syncPlaylists();
      expect(initialSync.playlistsSynced, 1);
      expect(initialSync.videosAdded, 2);

      // 2. Load into player
      await playerEngine.loadPlaylist('playlist-1');
      expect(playerEngine.totalVideos, 2);

      // 3. Updated sync with 3 videos (1 added, 1 removed)
      final updatedPlaylist = VideoList(
        id: 'playlist-1',
        name: 'Updated Playlist',
        sourceListId: 'source-1',
        syncVersion: 2,
        videos: [
          VideoItem(
            id: 'video-1',
            videoId: 'vid-1',
            title: 'Video 1',
            url: 'http://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 30000,
          ),
          VideoItem(
            id: 'video-3',
            videoId: 'vid-3',
            title: 'Video 3 (New)',
            url: 'http://example.com/video3.mp4',
            sequenceOrder: 1,
            durationMs: 60000,
          ),
        ],
      );

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);

      final updateSync = await syncService.syncPlaylists();
      expect(updateSync.success, true);
      expect(updateSync.playlistsSynced, 1);
      expect(updateSync.videosAdded, 1); // video-3
      expect(updateSync.videosRemoved, 1); // video-2
      expect(updateSync.videosUpdated, 1); // video-1

      // 4. Reload playlist in player
      await playerEngine.loadPlaylist('playlist-1');
      expect(playerEngine.totalVideos, 2);
      expect(playerEngine.currentPlaylist!.syncVersion, 2);
    });

    test('Error handling workflow: API failure -> retry -> success', () async {
      // 1. First sync attempt fails
      when(mockApiClient.syncPlaylist())
          .thenThrow(Exception('Network error'));

      final failedSync = await syncService.syncPlaylists();
      expect(failedSync.success, false);
      expect(failedSync.errorMessage, contains('Network error'));

      // 2. Verify no playlist in database
      final playlists = await database.getAllPlaylists();
      expect(playlists.length, 0);

      // 3. Retry succeeds
      final mockPlaylist = VideoList(
        id: 'playlist-1',
        name: 'Test Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [
          VideoItem(
            id: 'video-1',
            videoId: 'vid-1',
            title: 'Video 1',
            url: 'http://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 30000,
          ),
        ],
      );

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => mockPlaylist);

      final successSync = await syncService.syncPlaylists();
      expect(successSync.success, true);
      expect(successSync.playlistsSynced, 1);

      // 4. Verify playlist now in database
      final playlistsAfterRetry = await database.getAllPlaylists();
      expect(playlistsAfterRetry.length, 1);
    });

    test('Player state management: play -> pause -> resume -> next', () async {
      // 1. Setup playlist
      final mockPlaylist = VideoList(
        id: 'playlist-1',
        name: 'Test Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [
          VideoItem(
            id: 'video-1',
            videoId: 'vid-1',
            title: 'Video 1',
            url: 'http://example.com/video1.mp4',
            sequenceOrder: 0,
            durationMs: 30000,
          ),
          VideoItem(
            id: 'video-2',
            videoId: 'vid-2',
            title: 'Video 2',
            url: 'http://example.com/video2.mp4',
            sequenceOrder: 1,
            durationMs: 45000,
          ),
        ],
      );

      await database.upsertPlaylist(mockPlaylist);
      await playerEngine.loadPlaylist('playlist-1');

      // 2. Check initial state
      expect(playerEngine.isPlaying, false);
      expect(playerEngine.currentIndex, 0);
      expect(playerEngine.currentVideoItem, isNotNull);
      expect(playerEngine.currentVideoItem!.id, 'video-1');

      // 3. Test next video
      playerEngine.playNext();
      expect(playerEngine.currentIndex, 1);
      expect(playerEngine.currentVideoItem!.id, 'video-2');

      // 4. Test previous video
      playerEngine.playPrevious();
      expect(playerEngine.currentIndex, 0);
      expect(playerEngine.currentVideoItem!.id, 'video-1');

      // 5. Test skip to specific video
      playerEngine.skipToVideo(1);
      expect(playerEngine.currentIndex, 1);
      expect(playerEngine.currentVideoItem!.id, 'video-2');
    });

    test('History tracking with batch reporting', () async {
      // Mock successful history submission
      when(mockApiClient.submitPlaybackHistory(any))
          .thenAnswer((_) async => {});

      // 1. Track multiple video completions
      historyService.trackVideoStart(
        playlistId: 'playlist-1',
        videoId: 'video-1',
      );
      historyService.trackVideoComplete(
        playlistId: 'playlist-1',
        videoId: 'video-1',
        actualDurationMs: 30000,
      );

      historyService.trackVideoStart(
        playlistId: 'playlist-1',
        videoId: 'video-2',
      );
      historyService.trackVideoComplete(
        playlistId: 'playlist-1',
        videoId: 'video-2',
        actualDurationMs: 45000,
      );

      // 2. Verify pending history
      expect(historyService.getPendingHistory().length, 2);

      // 3. Submit batch
      await historyService.submitPendingHistory();

      // 4. Verify history cleared
      expect(historyService.getPendingHistory().length, 0);
      verify(mockApiClient.submitPlaybackHistory(any)).called(1);
    });

    test('Concurrent sync prevention', () async {
      final mockPlaylist = VideoList(
        id: 'playlist-1',
        name: 'Test Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [],
      );

      // Setup slow API response
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async {
        await Future.delayed(const Duration(milliseconds: 100));
        return mockPlaylist;
      });

      // Start first sync
      final firstSync = syncService.syncPlaylists();

      // Try to start second sync immediately
      await Future.delayed(const Duration(milliseconds: 10));
      final secondSync = await syncService.syncPlaylists();

      // Second should fail with "already in progress"
      expect(secondSync.success, false);
      expect(secondSync.errorMessage, contains('already in progress'));

      // First should succeed
      final firstResult = await firstSync;
      expect(firstResult.success, true);
    });
  });
}
