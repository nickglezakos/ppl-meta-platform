import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/models/video_list.dart';

/// Player control panel widget
/// 
/// Shows playback controls for development and testing:
/// - Play/Pause/Stop buttons
/// - Previous/Next navigation
/// - Progress bar with seek
/// - Loop mode selector
/// - Volume control (future)
class PlayerControls extends StatelessWidget {
  final VoidCallback? onClose;

  const PlayerControls({
    super.key,
    this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final playerEngine = context.watch<SignagePlayerEngine>();

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [
            Colors.black.withOpacity(0.9),
            Colors.black.withOpacity(0.7),
            Colors.transparent,
          ],
        ),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Progress bar
          _buildProgressBar(playerEngine),
          const SizedBox(height: 16),

          // Control buttons row
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Previous button
              IconButton(
                icon: const Icon(Icons.skip_previous, size: 32),
                color: Colors.white,
                onPressed: playerEngine.currentPlaylist != null
                    ? () => playerEngine.previous()
                    : null,
              ),

              const SizedBox(width: 8),

              // Stop button
              IconButton(
                icon: const Icon(Icons.stop, size: 32),
                color: Colors.white,
                onPressed: playerEngine.isPlaying || playerEngine.isPaused
                    ? () => playerEngine.stop()
                    : null,
              ),

              const SizedBox(width: 16),

              // Play/Pause button
              Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.blue,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.blue.withOpacity(0.5),
                      blurRadius: 16,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: IconButton(
                  icon: Icon(
                    playerEngine.isPlaying 
                        ? Icons.pause 
                        : Icons.play_arrow,
                    size: 48,
                  ),
                  color: Colors.white,
                  onPressed: () {
                    if (playerEngine.isPlaying) {
                      playerEngine.pause();
                    } else if (playerEngine.isPaused) {
                      playerEngine.resume();
                    } else {
                      playerEngine.play();
                    }
                  },
                ),
              ),

              const SizedBox(width: 16),

              // Next button
              IconButton(
                icon: const Icon(Icons.skip_next, size: 32),
                color: Colors.white,
                onPressed: playerEngine.currentPlaylist != null
                    ? () => playerEngine.next()
                    : null,
              ),

              const SizedBox(width: 8),

              // Loop mode button
              _buildLoopModeButton(playerEngine),
            ],
          ),

          const SizedBox(height: 12),

          // Video info and close button
          Row(
            children: [
              Expanded(
                child: _buildVideoInfo(playerEngine),
              ),
              if (onClose != null)
                IconButton(
                  icon: const Icon(Icons.close, size: 20),
                  color: Colors.white.withOpacity(0.7),
                  onPressed: onClose,
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProgressBar(SignagePlayerEngine playerEngine) {
    final duration = playerEngine.currentDuration;
    final position = playerEngine.currentPosition;

    return Column(
      children: [
        SliderTheme(
          data: SliderThemeData(
            activeTrackColor: Colors.blue,
            inactiveTrackColor: Colors.white.withOpacity(0.3),
            thumbColor: Colors.blue,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
            overlayShape: const RoundSliderOverlayShape(overlayRadius: 12),
            trackHeight: 4,
          ),
          child: Slider(
            value: duration.inSeconds > 0
                ? position.inSeconds.toDouble()
                : 0.0,
            min: 0.0,
            max: duration.inSeconds > 0 ? duration.inSeconds.toDouble() : 1.0,
            onChanged: (value) {
              playerEngine.seekTo(Duration(seconds: value.toInt()));
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _formatDuration(position),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.8),
                  fontSize: 12,
                ),
              ),
              Text(
                _formatDuration(duration),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.8),
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLoopModeButton(SignagePlayerEngine playerEngine) {
    final loopMode = playerEngine.currentPlaylist?.loopMode ?? LoopMode.continuous;

    IconData icon;
    String tooltip;

    switch (loopMode) {
      case LoopMode.continuous:
        icon = Icons.repeat;
        tooltip = 'Loop: Continuous';
        break;
      case LoopMode.once:
        icon = Icons.repeat_one;
        tooltip = 'Loop: Once';
        break;
      case LoopMode.single:
        icon = Icons.repeat_one_on;
        tooltip = 'Loop: Single';
        break;
    }

    return IconButton(
      icon: Icon(icon, size: 24),
      color: Colors.white,
      tooltip: tooltip,
      onPressed: () {
        LoopMode newMode;
        switch (loopMode) {
          case LoopMode.continuous:
            newMode = LoopMode.once;
            break;
          case LoopMode.once:
            newMode = LoopMode.single;
            break;
          case LoopMode.single:
            newMode = LoopMode.continuous;
            break;
        }
        playerEngine.setLoopMode(newMode);
      },
    );
  }

  Widget _buildVideoInfo(SignagePlayerEngine playerEngine) {
    final currentVideo = playerEngine.currentVideo;
    final nextVideo = playerEngine.nextVideo;

    if (currentVideo == null) {
      return Text(
        'No video loaded',
        style: TextStyle(
          color: Colors.white.withOpacity(0.7),
          fontSize: 14,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          currentVideo.title,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w500,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        if (nextVideo != null) ...[
          const SizedBox(height: 4),
          Text(
            'Next: ${nextVideo.title}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 12,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ],
    );
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:'
          '${minutes.toString().padLeft(2, '0')}:'
          '${seconds.toString().padLeft(2, '0')}';
    } else {
      return '${minutes.toString().padLeft(2, '0')}:'
          '${seconds.toString().padLeft(2, '0')}';
    }
  }
}
