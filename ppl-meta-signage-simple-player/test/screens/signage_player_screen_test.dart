import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:provider/provider.dart';
import 'package:signage_simple_player/screens/signage_player_screen.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/services/discovery_service.dart';
import 'package:signage_simple_player/services/history_tracking_service.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/models/playback_models.dart';
import 'package:signage_simple_player/models/video_list.dart';

import 'package:signage_simple_player/widgets/player_controls.dart';
import 'package:signage_simple_player/widgets/status_overlay.dart';

import 'signage_player_screen_test.mocks.dart';

@GenerateMocks([
  SignagePlayerEngine,
  SignageDiscoveryService,
  HistoryTrackingService,
  SignageApiClient,
])
void main() {
  late MockSignagePlayerEngine mockPlayerEngine;
  late MockSignageDiscoveryService mockDiscoveryService;
  late MockHistoryTrackingService mockHistoryTracker;
  late MockSignageApiClient mockApiClient;

  setUp(() {
    mockPlayerEngine = MockSignagePlayerEngine();
    mockDiscoveryService = MockSignageDiscoveryService();
    mockHistoryTracker = MockHistoryTrackingService();
    mockApiClient = MockSignageApiClient();

    // Default mock behaviors
    when(mockPlayerEngine.isPlaying).thenReturn(false);
    when(mockPlayerEngine.isPaused).thenReturn(false);
    when(mockPlayerEngine.isStopped).thenReturn(true);
    when(mockPlayerEngine.isLoading).thenReturn(false);
    when(mockPlayerEngine.hasError).thenReturn(false);
    when(mockPlayerEngine.currentController).thenReturn(null);
    when(mockPlayerEngine.currentPlaylist).thenReturn(null);
    when(mockPlayerEngine.currentVideo).thenReturn(null);
    when(mockPlayerEngine.nextVideo).thenReturn(null);
    when(mockPlayerEngine.currentPosition).thenReturn(Duration.zero);
    when(mockPlayerEngine.currentDuration).thenReturn(Duration.zero);
    when(mockPlayerEngine.progressPercent).thenReturn(0.0);

    when(mockDiscoveryService.isRegistered).thenReturn(false);
    when(mockHistoryTracker.isTracking).thenReturn(false);
  });

  Widget createTestWidget({
    bool showControls = true,
    bool showStatusOverlay = true,
  }) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<SignagePlayerEngine>.value(
          value: mockPlayerEngine,
        ),
        Provider<SignageDiscoveryService>.value(
          value: mockDiscoveryService,
        ),
        Provider<HistoryTrackingService>.value(
          value: mockHistoryTracker,
        ),
        Provider<SignageApiClient>.value(
          value: mockApiClient,
        ),
      ],
      child: MaterialApp(
        home: SignagePlayerScreen(
          showControls: showControls,
          showStatusOverlay: showStatusOverlay,
        ),
      ),
    );
  }

  group('SignagePlayerScreen', () {
    testWidgets('renders placeholder when no content', (tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.text('PPL Meta Signage Player'), findsOneWidget);
      expect(find.text('No playlist loaded'), findsOneWidget);
      expect(find.byIcon(Icons.smart_display_outlined), findsOneWidget);
    });

    testWidgets('shows loading indicator when loading', (tester) async {
      when(mockPlayerEngine.isLoading).thenReturn(true);

      await tester.pumpWidget(createTestWidget());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays error when player has error', (tester) async {
      when(mockPlayerEngine.hasError).thenReturn(true);
      when(mockPlayerEngine.errorMessage).thenReturn('Test error message');

      await tester.pumpWidget(createTestWidget());

      expect(find.text('Playback Error'), findsOneWidget);
      expect(find.text('Test error message'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('shows retry button on error', (tester) async {
      when(mockPlayerEngine.hasError).thenReturn(true);
      when(mockPlayerEngine.errorMessage).thenReturn('Test error');

      await tester.pumpWidget(createTestWidget());

      expect(find.widgetWithText(ElevatedButton, 'Retry'), findsOneWidget);

      // Tap retry button
      await tester.tap(find.widgetWithText(ElevatedButton, 'Retry'));
      await tester.pump();

      verify(mockPlayerEngine.stop()).called(1);
      verify(mockPlayerEngine.play()).called(1);
    });

    testWidgets('shows start playback button when playlist loaded', (tester) async {
      final mockPlaylist = VideoList(
        id: 'test-playlist',
        name: 'Test Playlist',
        sourceListId: 'test-source',
        videos: [],
        loopMode: LoopMode.continuous,
      );

      when(mockPlayerEngine.currentPlaylist).thenReturn(mockPlaylist);

      await tester.pumpWidget(createTestWidget());

      expect(find.text('Playlist loaded: Test Playlist'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Start Playback'), findsOneWidget);

      // Tap start playback
      await tester.tap(find.widgetWithText(ElevatedButton, 'Start Playback'));
      await tester.pump();

      verify(mockPlayerEngine.play()).called(1);
    });

    testWidgets('toggles controls visibility on tap', (tester) async {
      await tester.pumpWidget(createTestWidget());

      // Controls should not be visible initially
      expect(find.byType(PlayerControls), findsNothing);

      // Tap to show controls
      await tester.tap(find.byType(GestureDetector).first);
      await tester.pump();

      // Controls should now be visible
      expect(find.byType(PlayerControls), findsOneWidget);
    });

    testWidgets('hides status overlay initially', (tester) async {
      await tester.pumpWidget(createTestWidget());

      // Initially visible
      expect(find.byType(StatusOverlay), findsOneWidget);

      // Should auto-hide after 10 seconds
      await tester.pump(const Duration(seconds: 10));

      expect(find.byType(StatusOverlay), findsNothing);
    });

    testWidgets('can be created without controls', (tester) async {
      await tester.pumpWidget(createTestWidget(showControls: false));

      // Info toggle button should not be present
      expect(find.byIcon(Icons.info), findsNothing);
      expect(find.byIcon(Icons.info_outline), findsNothing);
    });

    testWidgets('can be created without status overlay', (tester) async {
      await tester.pumpWidget(createTestWidget(showStatusOverlay: false));

      expect(find.byType(StatusOverlay), findsNothing);
    });
  });

  group('PlayerControls', () {
    testWidgets('displays play button when not playing', (tester) async {
      await tester.pumpWidget(createTestWidget());

      // Show controls
      await tester.tap(find.byType(GestureDetector).first);
      await tester.pump();

      expect(find.byIcon(Icons.play_arrow), findsOneWidget);
    });

    testWidgets('displays pause button when playing', (tester) async {
      when(mockPlayerEngine.isPlaying).thenReturn(true);

      await tester.pumpWidget(createTestWidget());

      // Show controls
      await tester.tap(find.byType(GestureDetector).first);
      await tester.pump();

      expect(find.byIcon(Icons.pause), findsOneWidget);
    });

    testWidgets('shows video info when video is playing', (tester) async {
      final mockVideo = VideoItem(
        id: 'test-video',
        videoId: 'test-video-id',
        title: 'Test Video Title',
        url: 'http://example.com/video.mp4',
        sequenceOrder: 0,
        durationMs: 60000,
      );

      when(mockPlayerEngine.currentVideo).thenReturn(mockVideo);
      when(mockPlayerEngine.isPlaying).thenReturn(true);

      await tester.pumpWidget(createTestWidget());

      // Show controls
      await tester.tap(find.byType(GestureDetector).first);
      await tester.pump();

      expect(find.text('Test Video Title'), findsOneWidget);
    });
  });

  group('StatusOverlay', () {
    testWidgets('displays system information', (tester) async {
      when(mockDiscoveryService.isRegistered).thenReturn(true);
      when(mockHistoryTracker.isTracking).thenReturn(true);

      await tester.pumpWidget(createTestWidget());

      expect(find.text('PPL Meta Signage Player'), findsAtLeastNWidgets(1));
      expect(find.byIcon(Icons.smart_display), findsOneWidget);
    });

    testWidgets('shows online status when registered', (tester) async {
      when(mockDiscoveryService.isRegistered).thenReturn(true);

      await tester.pumpWidget(createTestWidget());

      // Status overlay should be visible initially
      expect(find.byType(StatusOverlay), findsOneWidget);
    });

    testWidgets('shows offline status when not registered', (tester) async {
      when(mockDiscoveryService.isRegistered).thenReturn(false);

      await tester.pumpWidget(createTestWidget());

      expect(find.byType(StatusOverlay), findsOneWidget);
    });
  });

  group('Keyboard Shortcuts', () {
    testWidgets('space key toggles play/pause', (tester) async {
      await tester.pumpWidget(createTestWidget());

      // Simulate space key press
      await tester.sendKeyEvent(LogicalKeyboardKey.space);
      await tester.pump();

      verify(mockPlayerEngine.play()).called(1);
    });

    testWidgets('right arrow key plays next video', (tester) async {
      await tester.pumpWidget(createTestWidget());

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pump();

      verify(mockPlayerEngine.next()).called(1);
    });

    testWidgets('left arrow key plays previous video', (tester) async {
      await tester.pumpWidget(createTestWidget());

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
      await tester.pump();

      verify(mockPlayerEngine.previous()).called(1);
    });

    testWidgets('escape key stops playback', (tester) async {
      await tester.pumpWidget(createTestWidget());

      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pump();

      verify(mockPlayerEngine.stop()).called(1);
    });
  });
}
