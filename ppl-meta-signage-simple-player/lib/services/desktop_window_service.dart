import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

/// Linux/desktop window helpers for kiosk signage.
///
/// The Docker entrypoint forces fullscreen via `wmctrl` on startup. This
/// service lets operators toggle that and quit the app from the keyboard
/// without needing window chrome.
class DesktopWindowService {
  DesktopWindowService({Logger? logger}) : _logger = logger ?? Logger();

  final Logger _logger;

  /// When false, [quit] records the request but does not call [exit].
  /// Tests set this to false so Escape cannot kill the test process.
  static bool exitProcessOnQuit = true;

  /// When false, [toggleFullscreen] / [exitFullscreen] skip shelling out to
  /// wmctrl (used by unit/widget tests).
  static bool enableProcessCalls = true;

  /// Flutter application / wmctrl class name used by entrypoint.sh.
  static const String windowClass = 'signage_simple_player.signage_simple_player';

  static final DesktopWindowService instance = DesktopWindowService();

  /// True on Linux/Windows/macOS desktop builds (not web/Android/iOS).
  bool get isDesktop {
    if (kIsWeb) return false;
    return Platform.isLinux || Platform.isWindows || Platform.isMacOS;
  }

  /// Number of [quit] calls (for tests).
  @visibleForTesting
  int quitCallCount = 0;

  /// Number of [toggleFullscreen] calls (for tests).
  @visibleForTesting
  int toggleFullscreenCallCount = 0;

  @visibleForTesting
  void resetForTest() {
    quitCallCount = 0;
    toggleFullscreenCallCount = 0;
  }

  /// Toggle windowed ↔ fullscreen (Linux via wmctrl; no-op elsewhere).
  Future<void> toggleFullscreen() async {
    toggleFullscreenCallCount++;
    if (!isDesktop) return;

    if (!Platform.isLinux) {
      _logger.w('Fullscreen toggle is only implemented for Linux signage');
      return;
    }

    if (!enableProcessCalls) return;

    try {
      final result = await Process.run('wmctrl', [
        '-xr',
        windowClass,
        '-b',
        'toggle,fullscreen',
      ]);
      if (result.exitCode != 0) {
        // Fallback: match by title substring
        final fallback = await Process.run('wmctrl', [
          '-r',
          'signage_simple_player',
          '-b',
          'toggle,fullscreen',
        ]);
        if (fallback.exitCode != 0) {
          _logger.w(
            'wmctrl fullscreen toggle failed '
            '(${result.stderr}${fallback.stderr}). '
            'Is wmctrl installed?',
          );
        } else {
          _logger.i('Fullscreen toggled (title match)');
        }
      } else {
        _logger.i('Fullscreen toggled');
      }
    } catch (e, stack) {
      _logger.e('Fullscreen toggle failed', error: e, stackTrace: stack);
    }
  }

  /// Leave fullscreen so the window gains chrome (Linux).
  Future<void> exitFullscreen() async {
    if (!isDesktop || !Platform.isLinux) return;
    if (!enableProcessCalls) return;
    try {
      await Process.run('wmctrl', [
        '-xr',
        windowClass,
        '-b',
        'remove,fullscreen',
      ]);
    } catch (e, stack) {
      _logger.e('Exit fullscreen failed', error: e, stackTrace: stack);
    }
  }

  /// Quit the player process (stops the Docker container main process).
  Future<void> quit() async {
    quitCallCount++;
    _logger.i('Quit requested (exitProcessOnQuit=$exitProcessOnQuit)');
    if (!exitProcessOnQuit) return;
    exit(0);
  }
}
