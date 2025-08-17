import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../widgets/video_player_widget.dart';
import '../core/api/api_client.dart';
import '../widgets/custom_app_bar.dart';
import '../core/providers/features_provider.dart';

/// Full preview screen for media files
/// Shows media content in full screen with title in navigation bar and back button
class MediaPreviewScreen extends ConsumerStatefulWidget {
  final MediaItem mediaItem;

  const MediaPreviewScreen({
    super.key,
    required this.mediaItem,
  });

  @override
  ConsumerState<MediaPreviewScreen> createState() => _MediaPreviewScreenState();
}

class _MediaPreviewScreenState extends ConsumerState<MediaPreviewScreen> {
  VideoPlayerController? _videoController;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: DarkCustomAppBar(
        title: widget.mediaItem.originalFilename ?? widget.mediaItem.filename ?? 'Media Preview',
        onBackPressed: () {
          // Try to pop first, if that fails, go to gallery
          if (context.canPop()) {
            context.pop();
          } else {
            context.go('/gallery');
          }
        },
      ),
      backgroundColor: Colors.black,
      body: _buildMediaContent(context, ref),
    );
  }

  Widget _buildMediaContent(BuildContext context, WidgetRef ref) {
    switch (widget.mediaItem.mediaType) {
      case MediaType.image:
        return _buildImagePreview(context, ref);
      case MediaType.video:
        return _buildVideoPreview(context, ref);
      default:
        return _buildUnsupportedMediaPreview(context);
    }
  }

  Widget _buildImagePreview(BuildContext context, WidgetRef ref) {
    final imageUrl = widget.mediaItem.url ?? widget.mediaItem.thumbnailUrl;
    if (imageUrl == null) {
      return _buildErrorPreview(context, 'No image URL available');
    }

    return Center(
      child: InteractiveViewer(
        panEnabled: true,
        boundaryMargin: const EdgeInsets.all(20),
        minScale: 0.5,
        maxScale: 3.0,
        child: Image.network(
          imageUrl.startsWith('/') ? 'http://localhost:8080$imageUrl' : imageUrl,
          fit: BoxFit.contain,
          width: double.infinity,
          height: double.infinity,
          headers: {
            if (ref.read(apiClientProvider).authToken != null)
              'Authorization': 'Bearer ${ref.read(apiClientProvider).authToken}',
          },
          errorBuilder: (context, error, stackTrace) {
            return _buildErrorPreview(context, 'Failed to load image');
          },
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded / loadingProgress.expectedTotalBytes!
                    : null,
                valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildVideoPreview(BuildContext context, WidgetRef ref) {
    final apiClient = ref.read(apiClientProvider);
    
    return Center(
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width,
          maxHeight: MediaQuery.of(context).size.height - kToolbarHeight,
        ),
        child: FutureBuilder<bool>(
          future: _shouldUseEmbeddedFaceDetection(ref),
          builder: (context, snapshot) {
            final useEmbedded = snapshot.data ?? false;
            
            // Choose video URL based on face detection strategy
            final videoUrl = useEmbedded 
                ? '/api/v1/stream/video/${widget.mediaItem.uuid}?face_detection=true&confidence_threshold=0.5'
                : '/api/v1/media/stream/${widget.mediaItem.uuid}';
            
            debugPrint('🎯 Using Issue 052 Hybrid Face Detection Architecture');
            debugPrint('🎥 Video URL: $videoUrl');
            
            return Stack(
              children: [
                VideoPlayerWidget(
                  videoUrl: videoUrl,
                  headers: {
                    if (apiClient.authToken != null)
                      'Authorization': 'Bearer ${apiClient.authToken}',
                  },
                  onControllerReady: (controller) {
                    debugPrint('🎬 Video controller ready with ${useEmbedded ? "embedded" : "overlay"} face detection');
                    setState(() {
                      _videoController = controller;
                    });
                  },
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  /// Determine if we should use embedded face detection
  /// Use dual API strategy for better browser compatibility and streaming camera support
  Future<bool> _shouldUseEmbeddedFaceDetection(WidgetRef ref) async {
    // SWITCH TO DUAL API STRATEGY for browser compatibility
    // Embedded face detection returns MJPEG format which causes browser errors
    // Dual API approach: normal video streaming + separate Vision service overlays
    // This also supports future streaming cameras (RTMP/HLS/WebRTC)
    debugPrint('🎯 Using dual API strategy - normal video + Vision service overlays');
    return false;
  }

  Widget _buildUnsupportedMediaPreview(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            _getMediaTypeIcon(widget.mediaItem.mediaType),
            size: 64,
            color: Colors.white70,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Preview not available',
            style: AppTextStyles.h6.copyWith(
              color: Colors.white70,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'This media type is not supported for preview',
            style: AppTextStyles.bodyMedium.copyWith(
              color: Colors.white54,
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton.icon(
            onPressed: () {
              // TODO: Implement download functionality
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Download functionality not implemented yet')),
              );
            },
            icon: const Icon(Icons.download),
            label: const Text('Download'),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorPreview(BuildContext context, String message) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red,
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Error',
            style: AppTextStyles.h6.copyWith(
              color: Colors.white,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            message,
            style: AppTextStyles.bodyMedium.copyWith(
              color: Colors.white70,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          ElevatedButton(
            onPressed: () {
              if (context.canPop()) {
                context.pop();
              } else {
                context.go('/gallery');
              }
            },
            child: const Text('Go Back'),
          ),
        ],
      ),
    );
  }

  IconData _getMediaTypeIcon(MediaType mediaType) {
    switch (mediaType) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.video_library;
      case MediaType.audio:
        return Icons.audiotrack;
      case MediaType.document:
        return Icons.description;
      default:
        return Icons.insert_drive_file;
    }
  }

  @override
  void dispose() {
    // Clear video controller reference without disposing
    // (the VideoPlayerWidget will handle its own disposal)
    _videoController = null;
    super.dispose();
  }
}
