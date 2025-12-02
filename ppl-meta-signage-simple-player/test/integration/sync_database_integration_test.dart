import 'package:flutter_test/flutter_test.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/services/sync_service.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';

import '../services/sync_service_test.mocks.dart';

@GenerateMocks([SignageApiClient])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Integration - Sync to Database', () {
    late PlaylistDatabase database;
    late MockSignageApiClient mockApiClient;
    late SyncService syncService;
    late Logger logger;

    setUp(() async {
      logger = Logger(level: Level.off);
      database = PlaylistDatabase(logger: logger);
      mockApiClient = MockSignageApiClient();
      
      syncService = SyncService(
        apiClient: mockApiClient,
        database: database,
        logger: logger,
      );
    });

    tearDown() async {
      await database.clearAllPlaylists();
    });

    test('Complete workflow: API -> Sync -> Database', () async {
      // 1. Create mock playlist from API
      final mockPlaylist = VideoList(
        id: 'integration-test-1',
        name: 'Integration Test Playlist',
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

      // 2. Mock API response
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => mockPlaylist);

      // 3. Trigger sync
      final syncResult = await syncService.syncPlaylists();
      expect(syncResult.success, true);
      expect(syncResult.playlistsSynced, 1);
      expect(syncResult.videosAdded, 2);

      // 4. Verify playlist persisted in database
      final savedPlaylist = await database.getPlaylist('integration-test-1');
      expect(savedPlaylist, isNotNull);
      expect(savedPlaylist!.name, 'Integration Test Playlist');
      expect(savedPlaylist.videos.length, 2);
      expect(savedPlaylist.videos[0].title, 'Test Video 1');
      expect(savedPlaylist.videos[1].title, 'Test Video 2');

      // 5. Verify playlist in getAll query
      final allPlaylists = await database.getAllPlaylists();
      expect(allPlaylists.length, greaterThanOrEqualTo(1));
      expect(allPlaylists.any((p) => p.id == 'integration-test-1'), true);
    });

    test('Update workflow: API change -> Sync -> Database updated', () async {
      // 1. Initial sync
      final initialPlaylist = VideoList(
        id: 'update-test-1',
        name: 'Initial Name',
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

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => initialPlaylist);
      await syncService.syncPlaylists();

      // 2. Verify initial state
      var savedPlaylist = await database.getPlaylist('update-test-1');
      expect(savedPlaylist!.name, 'Initial Name');
      expect(savedPlaylist.syncVersion, 1);
      expect(savedPlaylist.videos.length, 1);

      // 3. Updated playlist from API
      final updatedPlaylist = VideoList(
        id: 'update-test-1',
        name: 'Updated Name',
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
            id: 'video-2',
            videoId: 'vid-2',
            title: 'Video 2 (New)',
            url: 'http://example.com/video2.mp4',
            sequenceOrder: 1,
            durationMs: 60000,
          ),
        ],
      );

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      final updateResult = await syncService.syncPlaylists();

      // 4. Verify update detected
      expect(updateResult.success, true);
      expect(updateResult.playlistsSynced, 1);
      expect(updateResult.videosAdded, 1);
      expect(updateResult.videosUpdated, 1);

      // 5. Verify database updated
      savedPlaylist = await database.getPlaylist('update-test-1');
      expect(savedPlaylist!.name, 'Updated Name');
      expect(savedPlaylist.syncVersion, 2);
      expect(savedPlaylist.videos.length, 2);
    });

    test('Concurrent sync prevention integration', () async {
      final mockPlaylist = VideoList(
        id: 'concurrent-test-1',
        name: 'Test Playlist',
        sourceListId: 'source-1',
        syncVersion: 1,
        videos: [],
      );

      // Slow API response
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async {
        await Future.delayed(const Duration(milliseconds: 100));
        return mockPlaylist;
      });

      // Start first sync
      final firstSync = syncService.syncPlaylists();

      // Try second sync immediately
      await Future.delayed(const Duration(milliseconds: 10));
      final secondSync = await syncService.syncPlaylists();

      // Second should fail
      expect(secondSync.success, false);
      expect(secondSync.errorMessage, contains('already in progress'));

      // First should succeed
      final firstResult = await firstSync;
      expect(firstResult.success, true);

      // Verify only one playlist in database
      final playlists = await database.getAllPlaylists();
      expect(playlists.where((p) => p.id == 'concurrent-test-1').length, 1);
    });

    test('Error recovery: API failure -> no database changes', () async {
      // Record initial state
      final initialPlaylists = await database.getAllPlaylists();
      final initialCount = initialPlaylists.length;

      // API fails
      when(mockApiClient.syncPlaylist())
          .thenThrow(Exception('Network error'));

      final failedSync = await syncService.syncPlaylists();
      expect(failedSync.success, false);

      // Verify no new playlists added
      final afterPlaylists = await database.getAllPlaylists();
      expect(afterPlaylists.length, initialCount);
    });
  });
}
