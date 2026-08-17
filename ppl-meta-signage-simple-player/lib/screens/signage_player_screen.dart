import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:video_player/video_player.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/services/discovery_service.dart';
import 'package:signage_simple_player/services/config_service.dart';
import 'package:signage_simple_player/widgets/player_controls.dart';
import 'package:signage_simple_player/widgets/status_overlay.dart';
import 'package:signage_simple_player/main.dart';

/// Full-screen signage player screen
/// 
/// Features:
/// - Full-screen video playback
/// - Development controls (can be hidden for production)
/// - Status overlays (playlist, network, errors)
/// - Responsive layout
/// - Keyboard shortcuts
class SignagePlayerScreen extends StatefulWidget {
  final bool showControls;
  final bool showStatusOverlay;

  const SignagePlayerScreen({
    super.key,
    this.showControls = true,
    this.showStatusOverlay = true,
  });

  @override
  State<SignagePlayerScreen> createState() => _SignagePlayerScreenState();
}

class _SignagePlayerScreenState extends State<SignagePlayerScreen> {
  bool _controlsVisible = false;
  bool _statusVisible = true;

  @override
  void initState() {
    super.initState();
    
    // Enable immersive mode
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    
    // Allow both portrait and landscape orientations
    _allowAllOrientations();

    // Auto-hide status overlay after 10 seconds
    if (widget.showStatusOverlay) {
      Future.delayed(const Duration(seconds: 10), () {
        if (mounted) {
          setState(() => _statusVisible = false);
        }
      });
    }
  }

  void _allowAllOrientations() {
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
    ]);
  }

  void _toggleOrientation() {
    _allowAllOrientations();
  }

  @override
  void dispose() {
    // Restore system UI and orientation
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setPreferredOrientations([]);
    super.dispose();
  }

  void _toggleControls() {
    setState(() {
      _controlsVisible = !_controlsVisible;
    });
  }

  void _toggleStatus() {
    setState(() {
      _statusVisible = !_statusVisible;
    });
  }

  /// Factory reset: clears all stored configuration and returns the player to
  /// the initial Backend Setup screen (StartupScreen re-runs the config check
  /// and shows the setup screen because nothing is configured).
  Future<void> _doConfigureReset(
      BuildContext parentContext, ConfigService configService) async {
    await configService.resetAllConfiguration();
    if (!parentContext.mounted) return;
    Navigator.of(parentContext).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const StartupScreen()),
      (route) => false,
    );
  }

  void _showConfigDialog() {
    final parentContext = context;
    final configService = parentContext.read<ConfigService>();
    final ipController = TextEditingController(text: configService.backendIP);
    final portController = TextEditingController(text: configService.discoveryPort.toString());

    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => AlertDialog(
        title: const Text('Backend Configuration'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: ipController,
              decoration: const InputDecoration(
                labelText: 'Backend IP Address',
                hintText: '192.168.1.38',
              ),
              keyboardType: TextInputType.text,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: portController,
              decoration: const InputDecoration(
                labelText: 'Discovery Port',
                hintText: '8006',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            Text(
              'Current: ${configService.discoveryServiceUrl}',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop(); // close the dialog
              _doConfigureReset(parentContext, configService);
            },
            style: TextButton.styleFrom(
              foregroundColor: Colors.red.shade700,
            ),
            child: const Text('Reset & Reconfigure'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final success = await configService.saveBackendUrl(
                ipController.text.trim(),
                portController.text.trim(),
              );
              
              if (success && parentContext.mounted) {
                Navigator.of(context).pop();

                ScaffoldMessenger.of(parentContext).showSnackBar(
                  const SnackBar(
                    content: Text('Configuration saved. Reconnecting...'),
                    duration: Duration(seconds: 2),
                  ),
                );

                final discoveryService = parentContext.read<SignageDiscoveryService>();
                final reconnected = await discoveryService.initialize();

                if (!parentContext.mounted) {
                  return;
                }

                ScaffoldMessenger.of(parentContext).showSnackBar(
                  SnackBar(
                    content: Text(
                      reconnected
                          ? 'Connected with new backend settings'
                          : 'Settings saved. Waiting for backend connection...',
                    ),
                    duration: const Duration(seconds: 3),
                  ),
                );
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final playerEngine = context.watch<SignagePlayerEngine>();

    return Scaffold(
      backgroundColor: Colors.black,
      body: Focus(
        autofocus: true,
        onKeyEvent: (node, event) => _handleKeyPress(event, playerEngine),
        child: GestureDetector(
          onTap: _toggleControls,
          onDoubleTap: () {
            if (playerEngine.isPlaying) {
              playerEngine.pause();
            } else {
              playerEngine.play();
            }
          },
          onLongPress: _showConfigDialog,
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Video player
              _buildVideoPlayer(playerEngine),

              // Loading indicator
              if (playerEngine.isLoading)
                const Center(
                  child: CircularProgressIndicator(
                    color: Colors.white,
                  ),
                ),

              // Error display
              if (playerEngine.hasError)
                _buildErrorDisplay(playerEngine),

              // No content placeholder
              if (!playerEngine.isPlaying && 
                  !playerEngine.isLoading && 
                  !playerEngine.hasError)
                _buildPlaceholder(),

              // Status overlay (top)
              if (widget.showStatusOverlay && _statusVisible)
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: StatusOverlay(
                    onClose: _toggleStatus,
                  ),
                ),

              // Player controls (bottom)
              if (widget.showControls && _controlsVisible)
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: PlayerControls(
                    onClose: _toggleControls,
                  ),
                ),

              // Debug info toggle button and settings
              if (widget.showControls)
                Positioned(
                  top: 16,
                  right: 16,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Orientation toggle button
                      IconButton(
                        icon: Icon(
                          Icons.screen_rotation,
                          color: Colors.white.withValues(alpha: 0.7),
                        ),
                        onPressed: _toggleOrientation,
                        tooltip: 'Allow Portrait + Landscape',
                      ),
                      IconButton(
                        icon: Icon(
                          Icons.settings,
                          color: Colors.white.withValues(alpha: 0.7),
                        ),
                        onPressed: _showConfigDialog,
                        tooltip: 'Configuration',
                      ),
                      IconButton(
                        icon: Icon(
                          _statusVisible ? Icons.info : Icons.info_outline,
                          color: Colors.white.withValues(alpha: 0.7),
                        ),
                        onPressed: _toggleStatus,
                        tooltip: 'Toggle Info',
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVideoPlayer(SignagePlayerEngine playerEngine) {
    final controller = playerEngine.currentController;

    if (controller == null || !controller.value.isInitialized) {
      return const SizedBox.expand();
    }

    return Center(
      child: AspectRatio(
        aspectRatio: controller.value.aspectRatio,
        child: VideoPlayer(controller),
      ),
    );
  }

  Widget _buildErrorDisplay(SignagePlayerEngine playerEngine) {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        margin: const EdgeInsets.symmetric(horizontal: 64),
        decoration: BoxDecoration(
          color: Colors.red.withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline,
              color: Colors.white,
              size: 64,
            ),
            const SizedBox(height: 16),
            const Text(
              'Playback Error',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              playerEngine.errorMessage ?? 'Unknown error occurred',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                playerEngine.stop();
                playerEngine.play();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: Colors.red,
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder() {
    final playerEngine = context.watch<SignagePlayerEngine>();

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Image.asset(
            'assets/images/eyenet-logo.png',
            height: 100,
            errorBuilder: (context, error, stackTrace) {
              return Icon(
                Icons.smart_display_outlined,
                size: 120,
                color: Colors.white.withValues(alpha: 0.3),
              );
            },
          ),
          const SizedBox(height: 8),
          Text(
            playerEngine.currentPlaylist != null
                ? 'Playlist loaded: ${playerEngine.currentPlaylist!.name}'
                : 'No playlist loaded',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 32),
          if (playerEngine.currentPlaylist != null)
            ElevatedButton.icon(
              onPressed: () => playerEngine.play(),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Playback'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
              ),
            )
          else
            Text(
              'Waiting for content...',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
        ],
      ),
    );
  }

  KeyEventResult _handleKeyPress(KeyEvent event, SignagePlayerEngine playerEngine) {
    if (event is! KeyDownEvent) {
      return KeyEventResult.ignored;
    }

    switch (event.logicalKey) {
      case LogicalKeyboardKey.space:
        if (playerEngine.isPlaying) {
          playerEngine.pause();
        } else {
          playerEngine.play();
        }
        return KeyEventResult.handled;

      case LogicalKeyboardKey.arrowRight:
        playerEngine.next();
        return KeyEventResult.handled;

      case LogicalKeyboardKey.arrowLeft:
        playerEngine.previous();
        return KeyEventResult.handled;

      case LogicalKeyboardKey.escape:
        playerEngine.stop();
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyI:
        _toggleStatus();
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyC:
        _toggleControls();
        return KeyEventResult.handled;

      case LogicalKeyboardKey.keyO:
        _toggleOrientation();
        return KeyEventResult.handled;

      default:
        return KeyEventResult.ignored;
    }
  }
}
