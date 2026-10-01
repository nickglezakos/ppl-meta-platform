import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/models/rich_message_models.dart';

/// Manages a non-blocking rich message overlay above playlist playback.
///
/// Intentionally does **not** touch [SignagePlayerEngine] — showing or
/// dismissing an overlay must never pause, stop, or switch playlists.
class RichMessageOverlayService extends ChangeNotifier {
  final Logger _logger;
  final AudioPlayer _audioPlayer = AudioPlayer();

  RichMessageOverlayPayload? _current;
  Timer? _dismissTimer;
  bool _visible = false;
  int _showGeneration = 0;

  RichMessageOverlayService({required Logger logger}) : _logger = logger;

  bool get isVisible => _visible;
  RichMessageOverlayPayload? get current => _current;

  /// Increments on every [show] so the UI can remount even for the same template.
  int get showGeneration => _showGeneration;

  /// Show an overlay. Replaces any currently visible message.
  Future<void> show(RichMessageOverlayPayload payload) async {
    _logger.i(
      'Rich message overlay show template=${payload.templateId} '
      'durationMs=${payload.durationMs} layout=${payload.layout} '
      'generation=${_showGeneration + 1}',
    );

    // Tear down first (with notify) so WebView/widgets remount on the next show.
    final wasVisible = _visible;
    await dismiss(notify: wasVisible);
    if (wasVisible) {
      // Yield a frame so Flutter disposes the previous overlay subtree.
      await Future<void>.delayed(const Duration(milliseconds: 50));
    }

    _showGeneration += 1;
    _current = payload;
    _visible = true;
    notifyListeners();

    await _playSound(payload.soundUrl);

    final durationMs = payload.durationMs > 0 ? payload.durationMs : 15000;
    _dismissTimer = Timer(Duration(milliseconds: durationMs), () {
      dismiss();
    });
  }

  /// Hide the overlay and stop overlay sound only.
  Future<void> dismiss({bool notify = true}) async {
    _dismissTimer?.cancel();
    _dismissTimer = null;

    final wasVisible = _visible;
    _visible = false;
    _current = null;

    try {
      await _audioPlayer.stop();
    } catch (e) {
      _logger.w('Failed to stop overlay sound: $e');
    }

    if (notify && wasVisible) {
      notifyListeners();
    }
  }

  Future<void> _playSound(String? soundUrl) async {
    if (soundUrl == null || soundUrl.isEmpty) return;
    try {
      await _audioPlayer.setUrl(soundUrl);
      await _audioPlayer.play();
    } catch (e, stack) {
      _logger.w('Failed to play overlay sound', error: e, stackTrace: stack);
    }
  }

  @override
  void dispose() {
    _dismissTimer?.cancel();
    _audioPlayer.dispose();
    super.dispose();
  }
}
