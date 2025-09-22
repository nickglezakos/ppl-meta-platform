import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/face_data_providers.dart';

/// Widget to display the face count for a media item
class FaceCountWidget extends ConsumerWidget {
  final String mediaId;
  final bool showIcon;
  final bool compact;
  final Color? textColor;
  final Color? iconColor;

  const FaceCountWidget({
    super.key,
    required this.mediaId,
    this.showIcon = true,
    this.compact = false,
    this.textColor,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faceData = ref.watch(mediaFaceDataProvider(mediaId));
    
    if (compact) {
      return _buildCompactWidget(context, faceData);
    } else {
      return _buildFullWidget(context, faceData);
    }
  }

  Widget _buildCompactWidget(BuildContext context, MediaFaceDataState faceData) {
    final theme = Theme.of(context);
    final effectiveTextColor = textColor ?? theme.textTheme.bodySmall?.color ?? Colors.white70;
    final effectiveIconColor = iconColor ?? effectiveTextColor;

    if (faceData.isLoading) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                strokeWidth: 1.5,
                valueColor: AlwaysStoppedAnimation<Color>(effectiveIconColor),
              ),
            ),
            const SizedBox(width: 4),
          ],
          Text(
            'Loading...',
            style: TextStyle(
              color: effectiveTextColor,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    if (faceData.hasError) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            Icon(
              Icons.error_outline,
              size: 12,
              color: Colors.red[300],
            ),
            const SizedBox(width: 4),
          ],
          Text(
            'Error',
            style: TextStyle(
              color: Colors.red[300],
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (showIcon) ...[
          Icon(
            Icons.face,
            size: 12,
            color: effectiveIconColor,
          ),
          const SizedBox(width: 4),
        ],
        Text(
          '${faceData.totalCount}',
          style: TextStyle(
            color: effectiveTextColor,
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildFullWidget(BuildContext context, MediaFaceDataState faceData) {
    final theme = Theme.of(context);
    final effectiveTextColor = textColor ?? theme.textTheme.bodyMedium?.color ?? Colors.white;
    final effectiveIconColor = iconColor ?? effectiveTextColor;

    if (faceData.isLoading) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.blue.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              'Loading faces...',
              style: TextStyle(
                color: Colors.blue,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    if (faceData.hasError) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.red.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 16,
              color: Colors.red[300],
            ),
            const SizedBox(width: 8),
            Text(
              'Face load error',
              style: TextStyle(
                color: Colors.red[300],
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    Color containerColor;
    Color borderColor;
    if (faceData.totalCount > 0) {
      containerColor = Colors.green.withOpacity(0.1);
      borderColor = Colors.green.withOpacity(0.3);
    } else {
      containerColor = Colors.grey.withOpacity(0.1);
      borderColor = Colors.grey.withOpacity(0.3);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: containerColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.face,
            size: 16,
            color: faceData.totalCount > 0 ? Colors.green : Colors.grey,
          ),
          const SizedBox(width: 8),
          Text(
            'Faces: ${faceData.totalCount}',
            style: TextStyle(
              color: faceData.totalCount > 0 ? Colors.green : Colors.grey,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Compact face count display for tight spaces
class CompactFaceCountWidget extends ConsumerWidget {
  final String mediaId;
  final Color? color;

  const CompactFaceCountWidget({
    super.key,
    required this.mediaId,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FaceCountWidget(
      mediaId: mediaId,
      compact: true,
      showIcon: true,
      textColor: color,
      iconColor: color,
    );
  }
}

/// Face count badge for overlay display
class FaceCountBadge extends ConsumerWidget {
  final String mediaId;
  final Color? backgroundColor;
  final Color? textColor;

  const FaceCountBadge({
    super.key,
    required this.mediaId,
    this.backgroundColor,
    this.textColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faceData = ref.watch(mediaFaceDataProvider(mediaId));
    
    if (faceData.isLoading) {
      return Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: backgroundColor ?? Colors.blue.withOpacity(0.8),
          borderRadius: BorderRadius.circular(12),
        ),
        child: SizedBox(
          width: 12,
          height: 12,
          child: CircularProgressIndicator(
            strokeWidth: 1.5,
            valueColor: AlwaysStoppedAnimation<Color>(
              textColor ?? Colors.white,
            ),
          ),
        ),
      );
    }

    if (faceData.hasError) {
      return Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: backgroundColor ?? Colors.red.withOpacity(0.8),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(
          Icons.error_outline,
          size: 12,
          color: textColor ?? Colors.white,
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: backgroundColor ?? Colors.black.withOpacity(0.7),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.face,
            size: 10,
            color: textColor ?? Colors.white,
          ),
          const SizedBox(width: 2),
          Text(
            '${faceData.totalCount}',
            style: TextStyle(
              color: textColor ?? Colors.white,
              fontSize: 9,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}