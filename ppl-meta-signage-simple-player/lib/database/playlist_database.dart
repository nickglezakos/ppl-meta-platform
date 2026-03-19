import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:logger/logger.dart';
import '../models/video_list.dart';
import '../models/playback_history.dart';
import '../config/app_config.dart';

/// SQLite database for local playlist and history storage
class PlaylistDatabase {
  static PlaylistDatabase? _instance;
  static Database? _database;
  final Logger _logger;

  PlaylistDatabase._internal({Logger? logger})
      : _logger = logger ?? Logger();

  factory PlaylistDatabase({Logger? logger}) {
    _instance ??= PlaylistDatabase._internal(logger: logger);
    return _instance!;
  }

  /// Get database instance
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  /// Initialize database
  Future<Database> _initDatabase() async {
    try {
      final databasesPath = await getDatabasesPath();
      final path = join(databasesPath, AppConfig.databaseName);

      _logger.i('Initializing database at: $path');

      return await openDatabase(
        path,
        version: AppConfig.databaseVersion,
        onCreate: _onCreate,
        onUpgrade: _onUpgrade,
      );
    } catch (e, stackTrace) {
      _logger.e('Failed to initialize database', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Create database tables
  Future<void> _onCreate(Database db, int version) async {
    _logger.i('Creating database tables (version $version)');

    await db.execute('''
      CREATE TABLE playlists (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        source_list_id TEXT NOT NULL,
        last_synced_at TEXT,
        sync_version INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        loop_mode TEXT DEFAULT 'continuous',
        transition_duration_ms INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    ''');

    await db.execute('''
      CREATE TABLE playlist_videos (
        id TEXT PRIMARY KEY,
        playlist_id TEXT NOT NULL,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        sequence_order INTEGER NOT NULL,
        duration_ms INTEGER NOT NULL,
        metadata TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE
      )
    ''');

    await db.execute('''
      CREATE TABLE playback_history (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        video_title TEXT NOT NULL,
        playlist_id TEXT NOT NULL,
        playlist_name TEXT,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        duration_played_ms INTEGER DEFAULT 0,
        completion_percent REAL DEFAULT 0.0,
        playback_quality TEXT,
        interruptions INTEGER DEFAULT 0,
        error_occurred INTEGER DEFAULT 0,
        error_message TEXT,
        device_id TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    ''');

    // Create indexes
    await db.execute('CREATE INDEX idx_playlist_videos_playlist_id ON playlist_videos(playlist_id)');
    await db.execute('CREATE INDEX idx_playlist_videos_sequence ON playlist_videos(sequence_order)');
    await db.execute('CREATE INDEX idx_playback_history_started_at ON playback_history(started_at)');
    await db.execute('CREATE INDEX idx_playback_history_video_id ON playback_history(video_id)');
    await db.execute('CREATE INDEX idx_playback_history_playlist_id ON playback_history(playlist_id)');

    _logger.i('Database tables created successfully');
  }

  /// Handle database upgrades
  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    _logger.i('Upgrading database from version $oldVersion to $newVersion');
    // Add migration logic here when schema changes
  }

  // ==================== PLAYLIST OPERATIONS ====================

  /// Insert or update playlist
  Future<void> upsertPlaylist(VideoList playlist) async {
    final db = await database;
    
    try {
      await db.transaction((txn) async {
        // Upsert playlist
        await txn.insert(
          'playlists',
          {
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description,
            'source_list_id': playlist.sourceListId,
            'last_synced_at': playlist.lastSyncedAt?.toIso8601String(),
            'sync_version': playlist.syncVersion,
            'is_active': playlist.isActive ? 1 : 0,
            'loop_mode': playlist.loopMode.name,
            'transition_duration_ms': playlist.transitionDurationMs,
          },
          conflictAlgorithm: ConflictAlgorithm.replace,
        );

        // Delete old videos
        await txn.delete(
          'playlist_videos',
          where: 'playlist_id = ?',
          whereArgs: [playlist.id],
        );

        // Insert new videos
        for (var video in playlist.videos) {
          await txn.insert('playlist_videos', {
            'id': video.id,
            'playlist_id': playlist.id,
            'video_id': video.videoId,
            'title': video.title,
            'url': video.url,
            'sequence_order': video.sequenceOrder,
            'duration_ms': video.durationMs,
            'metadata': video.metadata?.toString(),
          });
        }
      });

      _logger.d('Playlist ${playlist.name} upserted successfully');
    } catch (e, stackTrace) {
      _logger.e('Failed to upsert playlist', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get playlist by ID
  Future<VideoList?> getPlaylist(String playlistId) async {
    final db = await database;
    
    try {
      final playlistMaps = await db.query(
        'playlists',
        where: 'id = ?',
        whereArgs: [playlistId],
      );

      if (playlistMaps.isEmpty) return null;

      final playlistMap = playlistMaps.first;
      
      // Get videos for this playlist
      final videoMaps = await db.query(
        'playlist_videos',
        where: 'playlist_id = ?',
        whereArgs: [playlistId],
        orderBy: 'sequence_order ASC',
      );

      return _buildVideoListFromMaps(playlistMap, videoMaps);
    } catch (e, stack) {
      _logger.e('Error fetching playlist by ID', error: e, stackTrace: stack);
      return null;
    }
  }

  /// Get playlist by backend source_list_id (UUID from backend)
  /// This is used when backend sends playlist switch commands
  Future<VideoList?> getPlaylistBySourceId(String sourceListId) async {
    final db = await database;
    
    try {
      final playlistMaps = await db.query(
        'playlists',
        where: 'source_list_id = ?',
        whereArgs: [sourceListId],
      );

      if (playlistMaps.isEmpty) return null;

      final playlistMap = playlistMaps.first;
      final playlistId = playlistMap['id'] as String;
      
      // Get videos for this playlist using the local ID
      final videoMaps = await db.query(
        'playlist_videos',
        where: 'playlist_id = ?',
        whereArgs: [playlistId],
        orderBy: 'sequence_order ASC',
      );

      final videos = videoMaps.map((map) => VideoItem(
        id: map['id'] as String,
        videoId: map['video_id'] as String,
        title: map['title'] as String,
        url: map['url'] as String,
        sequenceOrder: map['sequence_order'] as int,
        durationMs: map['duration_ms'] as int,
        metadata: null,
      )).toList();

      return VideoList(
        id: playlistMap['id'] as String,
        name: playlistMap['name'] as String,
        description: playlistMap['description'] as String?,
        sourceListId: playlistMap['source_list_id'] as String,
        lastSyncedAt: playlistMap['last_synced_at'] != null
            ? DateTime.parse(playlistMap['last_synced_at'] as String)
            : null,
        syncVersion: playlistMap['sync_version'] as int,
        isActive: (playlistMap['is_active'] as int) == 1,
        loopMode: LoopMode.values.firstWhere(
          (e) => e.name == playlistMap['loop_mode'],
          orElse: () => LoopMode.continuous,
        ),
        transitionDurationMs: playlistMap['transition_duration_ms'] as int,
        videos: videos,
      );
    } catch (e, stack) {
      _logger.e('Error fetching playlist by source ID', error: e, stackTrace: stack);
      return null;
    }
  }

  /// Helper to build VideoList from database maps
  VideoList _buildVideoListFromMaps(
    Map<String, dynamic> playlistMap,
    List<Map<String, dynamic>> videoMaps,
  ) {
    final videos = videoMaps.map((map) => VideoItem(
      id: map['id'] as String,
      videoId: map['video_id'] as String,
      title: map['title'] as String,
      url: map['url'] as String,
      sequenceOrder: map['sequence_order'] as int,
      durationMs: map['duration_ms'] as int,
      metadata: null, // TODO: Parse JSON metadata if needed
    )).toList();

    return VideoList(
      id: playlistMap['id'] as String,
      name: playlistMap['name'] as String,
      description: playlistMap['description'] as String?,
      sourceListId: playlistMap['source_list_id'] as String,
      lastSyncedAt: playlistMap['last_synced_at'] != null
          ? DateTime.parse(playlistMap['last_synced_at'] as String)
          : null,
      syncVersion: playlistMap['sync_version'] as int,
      isActive: (playlistMap['is_active'] as int) == 1,
      loopMode: LoopMode.values.firstWhere(
        (e) => e.name == playlistMap['loop_mode'],
        orElse: () => LoopMode.continuous,
      ),
      transitionDurationMs: playlistMap['transition_duration_ms'] as int,
      videos: videos,
    );
  }

  /// Get all playlists
  Future<List<VideoList>> getAllPlaylists({bool activeOnly = false}) async {
    final db = await database;
    
    try {
      final playlistMaps = await db.query(
        'playlists',
        where: activeOnly ? 'is_active = ?' : null,
        whereArgs: activeOnly ? [1] : null,
        orderBy: 'name ASC',
      );

      final playlists = <VideoList>[];

      for (var playlistMap in playlistMaps) {
        final playlistId = playlistMap['id'] as String;
        final playlist = await getPlaylist(playlistId);
        if (playlist != null) {
          playlists.add(playlist);
        }
      }

      return playlists;
    } catch (e, stackTrace) {
      _logger.e('Failed to get playlists', error: e, stackTrace: stackTrace);
      return [];
    }
  }

  /// Delete playlist
  Future<bool> deletePlaylist(String playlistId) async {
    final db = await database;
    
    try {
      final result = await db.delete(
        'playlists',
        where: 'id = ?',
        whereArgs: [playlistId],
      );
      
      _logger.d('Playlist deleted: $playlistId');
      return result > 0;
    } catch (e, stackTrace) {
      _logger.e('Failed to delete playlist', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  // ==================== HISTORY OPERATIONS ====================

  /// Insert playback history entry
  Future<String?> insertHistory(PlaybackHistoryEntry entry) async {
    final db = await database;
    
    try {
      await db.insert('playback_history', {
        'id': entry.id,
        'video_id': entry.videoId,
        'video_title': entry.videoTitle,
        'playlist_id': entry.playlistId,
        'playlist_name': entry.playlistName,
        'started_at': entry.startedAt.toIso8601String(),
        'completed_at': entry.completedAt?.toIso8601String(),
        'duration_played_ms': entry.durationPlayedMs,
        'completion_percent': entry.completionPercent,
        'playback_quality': entry.playbackQuality,
        'interruptions': entry.interruptions,
        'error_occurred': entry.errorOccurred ? 1 : 0,
        'error_message': entry.errorMessage,
        'device_id': entry.deviceId,
      });

      _logger.d('History entry inserted: ${entry.id}');
      return entry.id;
    } catch (e, stackTrace) {
      _logger.e('Failed to insert history', error: e, stackTrace: stackTrace);
      return null;
    }
  }

  /// Update playback history entry
  Future<bool> updateHistory(String entryId, Map<String, dynamic> updates) async {
    final db = await database;
    
    try {
      final result = await db.update(
        'playback_history',
        updates,
        where: 'id = ?',
        whereArgs: [entryId],
      );
      
      _logger.d('History entry updated: $entryId');
      return result > 0;
    } catch (e, stackTrace) {
      _logger.e('Failed to update history', error: e, stackTrace: stackTrace);
      return false;
    }
  }

  /// Query playback history
  Future<List<PlaybackHistoryEntry>> queryHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? videoId,
    String? playlistId,
    int offset = 0,
    int limit = 50,
    String orderBy = 'started_at DESC',
  }) async {
    final db = await database;
    
    try {
      final whereClause = <String>[];
      final whereArgs = <dynamic>[];

      if (startDate != null) {
        whereClause.add('started_at >= ?');
        whereArgs.add(startDate.toIso8601String());
      }
      if (endDate != null) {
        whereClause.add('started_at <= ?');
        whereArgs.add(endDate.toIso8601String());
      }
      if (videoId != null) {
        whereClause.add('video_id = ?');
        whereArgs.add(videoId);
      }
      if (playlistId != null) {
        whereClause.add('playlist_id = ?');
        whereArgs.add(playlistId);
      }

      final maps = await db.query(
        'playback_history',
        where: whereClause.isNotEmpty ? whereClause.join(' AND ') : null,
        whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
        orderBy: orderBy,
        limit: limit,
        offset: offset,
      );

      return maps.map((map) => PlaybackHistoryEntry(
        id: map['id'] as String,
        videoId: map['video_id'] as String,
        videoTitle: map['video_title'] as String,
        playlistId: map['playlist_id'] as String,
        playlistName: map['playlist_name'] as String?,
        startedAt: DateTime.parse(map['started_at'] as String),
        completedAt: map['completed_at'] != null
            ? DateTime.parse(map['completed_at'] as String)
            : null,
        durationPlayedMs: map['duration_played_ms'] as int,
        completionPercent: map['completion_percent'] as double,
        playbackQuality: map['playback_quality'] as String?,
        interruptions: map['interruptions'] as int,
        errorOccurred: (map['error_occurred'] as int) == 1,
        errorMessage: map['error_message'] as String?,
        deviceId: map['device_id'] as String,
        createdAt: DateTime.parse(map['created_at'] as String),
      )).toList();
    } catch (e, stackTrace) {
      _logger.e('Failed to query history', error: e, stackTrace: stackTrace);
      return [];
    }
  }

  /// Count history entries
  Future<int> countHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? videoId,
    String? playlistId,
  }) async {
    final db = await database;
    
    try {
      final whereClause = <String>[];
      final whereArgs = <dynamic>[];

      if (startDate != null) {
        whereClause.add('started_at >= ?');
        whereArgs.add(startDate.toIso8601String());
      }
      if (endDate != null) {
        whereClause.add('started_at <= ?');
        whereArgs.add(endDate.toIso8601String());
      }
      if (videoId != null) {
        whereClause.add('video_id = ?');
        whereArgs.add(videoId);
      }
      if (playlistId != null) {
        whereClause.add('playlist_id = ?');
        whereArgs.add(playlistId);
      }

      final result = await db.rawQuery(
        'SELECT COUNT(*) as count FROM playback_history' +
            (whereClause.isNotEmpty ? ' WHERE ${whereClause.join(' AND ')}' : ''),
        whereArgs.isNotEmpty ? whereArgs : null,
      );

      return Sqflite.firstIntValue(result) ?? 0;
    } catch (e, stackTrace) {
      _logger.e('Failed to count history', error: e, stackTrace: stackTrace);
      return 0;
    }
  }

  /// Get playback summary statistics
  Future<PlaybackSummary> getPlaybackSummary({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final db = await database;
    
    try {
      final whereClause = <String>[];
      final whereArgs = <dynamic>[];

      if (startDate != null) {
        whereClause.add('started_at >= ?');
        whereArgs.add(startDate.toIso8601String());
      }
      if (endDate != null) {
        whereClause.add('started_at <= ?');
        whereArgs.add(endDate.toIso8601String());
      }

      final whereString = whereClause.isNotEmpty ? ' WHERE ${whereClause.join(' AND ')}' : '';

      // Total playback time and average completion
      final summaryResult = await db.rawQuery(
        'SELECT ' +
            'SUM(duration_played_ms) as total_time, ' +
            'COUNT(DISTINCT video_id) as unique_videos, ' +
            'AVG(completion_percent) as avg_completion ' +
            'FROM playback_history' + whereString,
        whereArgs.isNotEmpty ? whereArgs : null,
      );

      // Most played video
      final mostPlayedResult = await db.rawQuery(
        'SELECT video_id, video_title, COUNT(*) as play_count ' +
            'FROM playback_history' + whereString +
            ' GROUP BY video_id ' +
            'ORDER BY play_count DESC LIMIT 1',
        whereArgs.isNotEmpty ? whereArgs : null,
      );

      final summary = summaryResult.first;
      final mostPlayed = mostPlayedResult.isNotEmpty ? mostPlayedResult.first : null;

      return PlaybackSummary(
        totalPlaybackTimeMs: (summary['total_time'] as int?) ?? 0,
        uniqueVideosPlayed: (summary['unique_videos'] as int?) ?? 0,
        averageCompletionRate: (summary['avg_completion'] as double?) ?? 0.0,
        mostPlayedVideo: mostPlayed != null
            ? MostPlayedVideo(
                videoId: mostPlayed['video_id'] as String,
                playCount: mostPlayed['play_count'] as int,
                title: mostPlayed['video_title'] as String?,
              )
            : null,
      );
    } catch (e, stackTrace) {
      _logger.e('Failed to get playback summary', error: e, stackTrace: stackTrace);
      return PlaybackSummary(
        totalPlaybackTimeMs: 0,
        uniqueVideosPlayed: 0,
        averageCompletionRate: 0.0,
      );
    }
  }

  /// Clean up old history entries
  Future<int> cleanupOldHistory({int retentionDays = 90}) async {
    final db = await database;
    
    try {
      final cutoffDate = DateTime.now().subtract(Duration(days: retentionDays));
      
      final result = await db.delete(
        'playback_history',
        where: 'started_at < ?',
        whereArgs: [cutoffDate.toIso8601String()],
      );

      _logger.i('Cleaned up $result old history entries (older than $retentionDays days)');
      return result;
    } catch (e, stackTrace) {
      _logger.e('Failed to cleanup history', error: e, stackTrace: stackTrace);
      return 0;
    }
  }

  /// Close database connection
  Future<void> close() async {
    final db = await database;
    await db.close();
    _database = null;
    _logger.i('Database closed');
  }
}
