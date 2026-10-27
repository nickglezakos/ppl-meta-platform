import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:provider/provider.dart';
import 'package:signage_simple_player/screens/signage_player_screen.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/services/discovery_service.dart';
import 'package:signage_simple_player/services/desktop_window_service.dart';
import 'package:signage_simple_player/services/history_tracking_service.dart';
import 'package:signage_simple_player/services/rich_message_overlay_service.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/models/playback_models.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:logger/logger.dart';

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
  late RichMessageOverlayService richMessageOverlay;

  setUp(() {
    mockPlayerEngine = MockSignagePlayerEngine();
    mockDiscoveryService = MockSignageDiscoveryService();
    mockHistoryTracker = MockHistoryTrackingService();
    mockApiClient = MockSignageApiClient();
    richMessageOverlay = RichMessageOverlayService(
      logger: Logger(level: Level.nothing),
    );

    // Desktop Esc/F11 must not kill the test process or call real wmctrl.
    DesktopWindowService.exitProcessOnQuit = false;
    DesktopWindowService.enableProcessCalls = false;
    DesktopWindowService.instance.resetForTest();

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
    when(mockPlayerEngine.play()).thenAnswer((_) async => true);
    when(mockPlayerEngine.pause()).thenAnswer((_) async {});
    when(mockPlayerEngine.stop()).thenAnswer((_) async {});
    when(mockPlayerEngine.next()).thenAnswer((_) async => true);
    when(mockPlayerEngine.previous()).thenAnswer((_) async => true);

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
        ChangeNotifierProvider<RichMessageOverlayService>.value(
          value: richMessageOverlay,
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
    // Avoid the 10s status-overlay auto-hide timer pending after dispose.
    Widget keyboardHarness() =>
        createTestWidget(showControls: false, showStatusOverlay: false);

    testWidgets('space key toggles play/pause', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      // Simulate space key press
      await tester.sendKeyEvent(LogicalKeyboardKey.space);
      await tester.pump();

      verify(mockPlayerEngine.play()).called(1);
    });

    testWidgets('right arrow key plays next video', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pump();

      verify(mockPlayerEngine.next()).called(1);
    });

    testWidgets('left arrow key plays previous video', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
      await tester.pump();

      verify(mockPlayerEngine.previous()).called(1);
    });

    testWidgets('escape key stops playback and quits on desktop', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pump();

      verify(mockPlayerEngine.stop()).called(1);
      // flutter test runs on the host OS; on Linux/macOS/Windows Esc quits.
      if (Platform.isLinux || Platform.isWindows || Platform.isMacOS) {
        expect(DesktopWindowService.instance.quitCallCount, 1);
      }
    });

    testWidgets('F11 toggles fullscreen on desktop', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      await tester.sendKeyEvent(LogicalKeyboardKey.f11);
      await tester.pump();

      if (Platform.isLinux || Platform.isWindows || Platform.isMacOS) {
        expect(DesktopWindowService.instance.toggleFullscreenCallCount, 1);
      }
    });

    testWidgets('Q quits on desktop', (tester) async {
      await tester.pumpWidget(keyboardHarness());

      await tester.sendKeyEvent(LogicalKeyboardKey.keyQ);
      await tester.pump();

      if (Platform.isLinux || Platform.isWindows || Platform.isMacOS) {
        verify(mockPlayerEngine.stop()).called(1);
        expect(DesktopWindowService.instance.quitCallCount, 1);
      }
    });
  });
}
