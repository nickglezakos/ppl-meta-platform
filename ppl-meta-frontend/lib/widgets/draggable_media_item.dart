import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';

/// A draggable wrapper for media items that provides visual feedback during drag operations
class DraggableMediaItem extends StatefulWidget {
  final Widget child;
  final MediaItem mediaItem;
  final bool isDragEnabled;
  final bool isSelected;
  final Function(MediaItem)? onDragStart;
  final Function(MediaItem)? onDragEnd;
  final Function(MediaItem, Offset)? onDragUpdate;

  const DraggableMediaItem({
    super.key,
    required this.child,
    required this.mediaItem,
    this.isDragEnabled = false,
    this.isSelected = false,
    this.onDragStart,
    this.onDragEnd,
    this.onDragUpdate,
  });

  @override
  State<DraggableMediaItem> createState() => _DraggableMediaItemState();
}

class _DraggableMediaItemState extends State<DraggableMediaItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  bool _isDragging = false;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 0.95,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isDragEnabled) {
      return widget.child;
    }

    return AnimatedBuilder(
      animation: _scaleAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: Draggable<MediaItem>(
            data: widget.mediaItem,
            feedback: _buildDragFeedback(),
            childWhenDragging: _buildChildWhenDragging(),
            onDragStarted: () {
              setState(() {
                _isDragging = true;
              });
              _animationController.forward();
              widget.onDragStart?.call(widget.mediaItem);
            },
            onDragEnd: (details) {
              setState(() {
                _isDragging = false;
              });
              _animationController.reverse();
              widget.onDragEnd?.call(widget.mediaItem);
            },
            onDragUpdate: (details) {
              widget.onDragUpdate?.call(widget.mediaItem, details.globalPosition);
            },
            child: widget.child,
          ),
        );
      },
    );
  }

  /// Build the feedback widget shown during dragging
  Widget _buildDragFeedback() {
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [
          BoxShadow(
            color: AppColors.black.withOpacity(0.3),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Stack(
          children: [
            // Media preview
            Container(
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                border: Border.all(
                  color: AppColors.primary,
                  width: 2,
                ),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Center(
                child: Icon(
                  _getMediaIcon(),
                  size: 32,
                  color: AppColors.primary,
                ),
              ),
            ),
            
            // Selection indicator
            if (widget.isSelected)
              Positioned(
                top: 4,
                right: 4,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check,
                    size: 12,
                    color: AppColors.white,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build the child widget shown while dragging
  Widget _buildChildWhenDragging() {
    return Opacity(
      opacity: 0.5,
      child: Stack(
        children: [
          widget.child,
          Container(
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.2),
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(
                color: AppColors.primary,
                width: 2,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Get appropriate icon for media type
  IconData _getMediaIcon() {
    switch (widget.mediaItem.mediaType) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.videocam;
      case MediaType.audio:
        return Icons.music_note;
      case MediaType.document:
        return Icons.description;
      case MediaType.pdf:
        return Icons.picture_as_pdf;
      case MediaType.text:
        return Icons.text_snippet;
      case MediaType.archive:
        return Icons.archive;
      case MediaType.other:
      default:
        return Icons.insert_drive_file;
    }
  }
}

/// A drop target that accepts dragged media items
class MediaDropTarget extends StatefulWidget {
  final Widget child;
  final Function(List<MediaItem>)? onAcceptMultiple;
  final Function(MediaItem)? onAcceptSingle;
  final bool isActive;
  final String? label;

  const MediaDropTarget({
    super.key,
    required this.child,
    this.onAcceptMultiple,
    this.onAcceptSingle,
    this.isActive = true,
    this.label,
  });

  @override
  State<MediaDropTarget> createState() => _MediaDropTargetState();
}

class _MediaDropTargetState extends State<MediaDropTarget>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _pulseAnimation;
  bool _isHovering = false;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.05,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isActive) {
      return widget.child;
    }

    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _pulseAnimation.value,
          child: DragTarget<MediaItem>(
            onAcceptWithDetails: (details) {
              widget.onAcceptSingle?.call(details.data);
              _animationController.stop();
              setState(() {
                _isHovering = false;
              });
            },
            onWillAcceptWithDetails: (details) {
              if (!_isHovering) {
                setState(() {
                  _isHovering = true;
                });
                _animationController.repeat(reverse: true);
              }
              return true;
            },
            onLeave: (data) {
              setState(() {
                _isHovering = false;
              });
              _animationController.stop();
            },
            builder: (context, candidateData, rejectedData) {
              return Container(
                decoration: BoxDecoration(
                  border: _isHovering
                      ? Border.all(
                          color: AppColors.primary,
                          width: 2,
                        )
                      : null,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  color: _isHovering
                      ? AppColors.primary.withOpacity(0.1)
                      : null,
                ),
                child: Stack(
                  children: [
                    widget.child,
                    if (_isHovering && widget.label != null)
                      Positioned.fill(
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.9),
                            borderRadius: BorderRadius.circular(AppRadius.md),
                          ),
                          child: Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.add_circle,
                                  color: AppColors.white,
                                  size: 32,
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                Text(
                                  widget.label!,
                                  style: AppTextStyles.bodyMedium.copyWith(
                                    color: AppColors.white,
                                    fontWeight: FontWeight.w600,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
  }
}
