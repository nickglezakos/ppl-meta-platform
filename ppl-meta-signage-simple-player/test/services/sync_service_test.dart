import 'package:flutter_test/flutter_test.dart';
import 'package:logger/logger.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:signage_simple_player/services/sync_service.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/api/api_exceptions.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/models/video_list.dart';

import 'sync_service_test.mocks.dart';

@GenerateMocks([SignageApiClient, PlaylistDatabase])
void main() {
  late MockSignageApiClient mockApiClient;
  late MockPlaylistDatabase mockDatabase;
  late Logger logger;
  late SyncService syncService;

  setUp(() {
    mockApiClient = MockSignageApiClient();
    mockDatabase = MockPlaylistDatabase();
    logger = Logger(level: Level.off);
    
    syncService = SyncService(
      apiClient: mockApiClient,
      database: mockDatabase,
      logger: logger,
    );
  });

  VideoList _createMockPlaylist({
    String id = 'test-playlist',
    String name = 'Test Playlist',
    int syncVersion = 1,
    int videoCount = 3,
  }) {
    final videos = List.generate(
      videoCount,
      (i) => VideoItem(
        id: 'video-$i',
        videoId: 'video-id-$i',
        title: 'Video $i',
        url: 'http://example.com/video$i.mp4',
        sequenceOrder: i,
        durationMs: 60000,
      ),
    );

    return VideoList(
      id: id,
      name: name,
      sourceListId: 'source-$id',
      syncVersion: syncVersion,
      videos: videos,
    );
  }

  group('SyncService - Initial State', () {
    test('starts with idle status', () {
      expect(syncService.status, SyncStatus.idle);
      expect(syncService.isSyncing, false);
      expect(syncService.canSync, true);
      expect(syncService.lastResult, isNull);
      expect(syncService.lastSyncTime, isNull);
    });

    test('provides status message when never synced', () {
      expect(syncService.getStatusMessage(), 'Ready to sync');
    });
  });

  group('SyncService - Manual Sync', () {
    test('syncs new playlist successfully', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(playlist.id)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(playlist)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylists();

      expect(result.success, true);
      expect(result.playlistsSynced, 1);
      expect(result.videosAdded, 3);
      expect(result.videosUpdated, 0);
      expect(result.videosRemoved, 0);
      
      expect(syncService.status, SyncStatus.success);
      expect(syncService.isSyncing, false);
      expect(syncService.lastResult, result);
      expect(syncService.lastSyncTime, isNotNull);

      verify(mockApiClient.syncPlaylist()).called(1);
      verify(mockDatabase.getPlaylist(playlist.id)).called(1);
      verify(mockDatabase.upsertPlaylist(playlist)).called(1);
    });

    test('updates existing playlist with new version', () async {
      final existingPlaylist = _createMockPlaylist(syncVersion: 1);
      final updatedPlaylist = _createMockPlaylist(syncVersion: 2, videoCount: 4);
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      when(mockDatabase.getPlaylist(updatedPlaylist.id))
          .thenAnswer((_) async => existingPlaylist);
      when(mockDatabase.upsertPlaylist(updatedPlaylist)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylists();

      expect(result.success, true);
      expect(result.playlistsSynced, 1);
      expect(result.videosAdded, 1); // 4 new - 3 old
      expect(result.videosUpdated, 3); // 3 existing videos

      verify(mockDatabase.upsertPlaylist(updatedPlaylist)).called(1);
    });

    test('skips unchanged playlist', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(playlist.id))
          .thenAnswer((_) async => playlist);

      final result = await syncService.syncPlaylists();

      expect(result.success, true);
      expect(result.playlistsSynced, 0);
      expect(result.videosAdded, 0);

      verify(mockDatabase.getPlaylist(playlist.id)).called(1);
      verifyNever(mockDatabase.upsertPlaylist(any));
    });

    test('handles no assigned playlist', () async {
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => null);

      final result = await syncService.syncPlaylists();

      expect(result.success, true);
      expect(result.playlistsSynced, 0);
      expect(syncService.status, SyncStatus.success);
    });

    test('handles API error', () async {
      when(mockApiClient.syncPlaylist())
          .thenThrow(ApiException('Network error', statusCode: 500));

      final result = await syncService.syncPlaylists();

      expect(result.success, false);
      expect(result.errorMessage, contains('Network error'));
      expect(syncService.status, SyncStatus.error);
      expect(syncService.isSyncing, false);
    });

    test('handles database error', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(playlist.id)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(playlist))
          .thenThrow(Exception('Database write failed'));
      
      final result = await syncService.syncPlaylists();

      expect(result.success, false);
      expect(result.errorMessage, contains('Database write failed'));
      expect(syncService.status, SyncStatus.error);
    });

    test('prevents concurrent syncs', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async {
        await Future.delayed(const Duration(milliseconds: 100));
        return playlist;
      });
      when(mockDatabase.getPlaylist(any)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      // Start first sync
      final future1 = syncService.syncPlaylists();
      
      // Try to start second sync while first is running
      await Future.delayed(const Duration(milliseconds: 10));
      final result2 = await syncService.syncPlaylists();

      expect(result2.success, false);
      expect(result2.errorMessage, contains('already in progress'));

      // Wait for first sync to complete
      final result1 = await future1;
      expect(result1.success, true);
    });
  });

  group('SyncService - Sync Single Playlist', () {
    test('syncs specific playlist by ID when assigned', () async {
      final playlist = _createMockPlaylist(id: 'target-playlist');
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist('target-playlist')).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(playlist)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylistById('target-playlist');

      expect(result.success, true);
      expect(result.playlistsSynced, 1);
      
      verify(mockDatabase.upsertPlaylist(playlist)).called(1);
    });

    test('handles no playlist assigned to device', () async {
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => null);

      final result = await syncService.syncPlaylistById('target');

      expect(result.success, false);
      expect(result.errorMessage, contains('No playlist assigned'));
    });

    test('handles wrong playlist ID (different than assigned)', () async {
      final assignedPlaylist = _createMockPlaylist(id: 'assigned-playlist');
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => assignedPlaylist);

      final result = await syncService.syncPlaylistById('different-playlist');

      expect(result.success, false);
      expect(result.errorMessage, contains('not assigned to this device'));
      verifyNever(mockDatabase.upsertPlaylist(any));
    });

    test('updates specific existing playlist', () async {
      final existingPlaylist = _createMockPlaylist(id: 'target', syncVersion: 1);
      final updatedPlaylist = _createMockPlaylist(id: 'target', syncVersion: 2);
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      when(mockDatabase.getPlaylist('target'))
          .thenAnswer((_) async => existingPlaylist);
      when(mockDatabase.upsertPlaylist(updatedPlaylist)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylistById('target');

      expect(result.success, true);
      verify(mockDatabase.upsertPlaylist(updatedPlaylist)).called(1);
    });
  });

  group('SyncService - Status and State', () {
    test('updates status during sync lifecycle', () async {
      final playlist = _createMockPlaylist();
      
      expect(syncService.status, SyncStatus.idle);

      when(mockApiClient.syncPlaylist()).thenAnswer((_) async {
        expect(syncService.status, SyncStatus.syncing);
        expect(syncService.isSyncing, true);
        return playlist;
      });
      when(mockDatabase.getPlaylist(any)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      await syncService.syncPlaylists();

      expect(syncService.status, SyncStatus.success);
      expect(syncService.isSyncing, false);
    });

    test('provides informative status messages', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(any)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      await syncService.syncPlaylists();

      final message = syncService.getStatusMessage();
      expect(message, contains('1 playlist'));
      expect(message, contains('3 videos'));
    });

    test('shouldSyncBasedOnTime returns true when never synced', () {
      expect(syncService.shouldSyncBasedOnTime(const Duration(hours: 1)), true);
    });

    test('shouldSyncBasedOnTime checks threshold', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(any)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      await syncService.syncPlaylists();

      // Just synced, should not need sync again
      expect(syncService.shouldSyncBasedOnTime(const Duration(hours: 1)), false);
      
      // Would need sync after long threshold
      expect(syncService.shouldSyncBasedOnTime(const Duration(microseconds: 1)), true);
    });

    test('reset clears state', () async {
      final playlist = _createMockPlaylist();
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => playlist);
      when(mockDatabase.getPlaylist(any)).thenAnswer((_) async => null);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      await syncService.syncPlaylists();
      
      expect(syncService.lastResult, isNotNull);
      expect(syncService.status, SyncStatus.success);

      syncService.reset();

      expect(syncService.status, SyncStatus.idle);
      expect(syncService.lastResult, isNull);
      expect(syncService.isSyncing, false);
    });
  });

  group('SyncService - Conflict Resolution', () {
    test('detects video additions', () async {
      final existingPlaylist = _createMockPlaylist(videoCount: 2);
      final updatedPlaylist = _createMockPlaylist(videoCount: 4);
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      when(mockDatabase.getPlaylist(updatedPlaylist.id))
          .thenAnswer((_) async => existingPlaylist);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylists();

      expect(result.videosAdded, 2); // 4 - 2
      expect(result.videosUpdated, 2); // existing videos
    });

    test('detects video removals', () async {
      final existingPlaylist = _createMockPlaylist(videoCount: 5);
      final updatedPlaylist = _createMockPlaylist(videoCount: 3);
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      when(mockDatabase.getPlaylist(updatedPlaylist.id))
          .thenAnswer((_) async => existingPlaylist);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylists();

      expect(result.videosRemoved, 2); // 5 - 3
      expect(result.videosUpdated, 3);
    });

    test('detects name changes', () async {
      final existingPlaylist = _createMockPlaylist(name: 'Old Name');
      final updatedPlaylist = _createMockPlaylist(name: 'New Name');
      
      when(mockApiClient.syncPlaylist()).thenAnswer((_) async => updatedPlaylist);
      when(mockDatabase.getPlaylist(updatedPlaylist.id))
          .thenAnswer((_) async => existingPlaylist);
      when(mockDatabase.upsertPlaylist(any)).thenAnswer((_) async => {});

      final result = await syncService.syncPlaylists();

      expect(result.playlistsSynced, 1);
      verify(mockDatabase.upsertPlaylist(any)).called(1);
    });
  });

  group('SyncResult', () {
    test('formats success message', () {
      final result = SyncResult(
        success: true,
        playlistsSynced: 2,
        videosAdded: 5,
        videosUpdated: 3,
        videosRemoved: 1,
      );

      final message = result.toString();
      expect(message, contains('2 playlists'));
      expect(message, contains('+5 videos'));
      expect(message, contains('~3 updated'));
      expect(message, contains('-1 removed'));
    });

    test('formats error message', () {
      final result = SyncResult(
        success: false,
        errorMessage: 'Connection failed',
      );

      expect(result.toString(), contains('failed'));
      expect(result.toString(), contains('Connection failed'));
    });
  });
}
