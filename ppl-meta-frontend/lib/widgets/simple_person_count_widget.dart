/// PPL Meta Frontend - Simple Person Count Widget
/// 
/// A simplified widget for displaying person counts using the new PPL Thread
/// service integration. This widget follows the READ-ONLY pattern where it
/// only retrieves stored person objects data without triggering workflows.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:developer' as developer;

import '../providers/ppl_thread_providers.dart';

/// Simple person count widget using PPL Thread service
class SimplePersonCountWidget extends ConsumerWidget {
  final String mediaId;
  final bool showIcon;
  final Color? textColor;
  final Color? iconColor;
  final double? fontSize;
  final FontWeight? fontWeight;

  const SimplePersonCountWidget({
    super.key,
    required this.mediaId,
    this.showIcon = true,
    this.textColor,
    this.iconColor,
    this.fontSize,
    this.fontWeight,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final effectiveTextColor = textColor ?? theme.textTheme.bodySmall?.color ?? Colors.white70;
    final effectiveIconColor = iconColor ?? effectiveTextColor;
    final effectiveFontSize = fontSize ?? 10;
    final effectiveFontWeight = fontWeight ?? FontWeight.w600;

    // Watch the person count provider
    final personCountAsync = ref.watch(personCountProvider(mediaId));

    return personCountAsync.when(
      data: (personCount) {
        developer.log(
          'Person count received: $personCount for media $mediaId',
          name: 'SimplePersonCountWidget',
        );

        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showIcon) ...[
              Icon(
                Icons.people,
                size: effectiveFontSize + 2,
                color: personCount > 0 ? Colors.blue.shade300 : effectiveIconColor,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              '$personCount persons',
              style: TextStyle(
                color: personCount > 0 ? Colors.blue.shade300 : effectiveTextColor,
                fontSize: effectiveFontSize,
                fontWeight: effectiveFontWeight,
              ),
            ),
          ],
        );
      },
      loading: () => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            SizedBox(
              width: effectiveFontSize,
              height: effectiveFontSize,
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
              fontSize: effectiveFontSize,
              fontWeight: effectiveFontWeight,
            ),
          ),
        ],
      ),
      error: (error, stackTrace) {
        developer.log(
          'Error getting person count for media $mediaId: $error',
          name: 'SimplePersonCountWidget',
          error: error,
          stackTrace: stackTrace,
        );

        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showIcon) ...[
              Icon(
                Icons.error_outline,
                size: effectiveFontSize + 2,
                color: Colors.red[300],
              ),
              const SizedBox(width: 4),
            ],
            Text(
              '0 persons',
              style: TextStyle(
                color: Colors.red[300],
                fontSize: effectiveFontSize,
                fontWeight: effectiveFontWeight,
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Enhanced person count widget that combines face count and person count
class EnhancedPersonCountWidget extends ConsumerWidget {
  final String mediaId;
  final int faceCount;
  final bool compact;
  final bool showIcon;
  final Color? textColor;
  final Color? iconColor;

  const EnhancedPersonCountWidget({
    super.key,
    required this.mediaId,
    required this.faceCount,
    this.compact = false,
    this.showIcon = true,
    this.textColor,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final effectiveTextColor = textColor ?? theme.textTheme.bodySmall?.color ?? Colors.white70;
    final effectiveIconColor = iconColor ?? effectiveTextColor;
    final fontSize = compact ? 10.0 : 12.0;

    if (faceCount == 0) {
      // No faces detected - only show face count
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            Icon(
              Icons.face,
              size: fontSize + 2,
              color: effectiveIconColor,
            ),
            const SizedBox(width: 4),
          ],
          Text(
            '0 faces',
            style: TextStyle(
              color: effectiveTextColor,
              fontSize: fontSize,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
    }

    // Faces detected - show both counts
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Face count
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showIcon) ...[
              Icon(
                Icons.face,
                size: fontSize + 2,
                color: effectiveIconColor,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              '$faceCount faces',
              style: TextStyle(
                color: effectiveTextColor,
                fontSize: fontSize,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        
        // Person count
        const SizedBox(height: 2),
        SimplePersonCountWidget(
          mediaId: mediaId,
          showIcon: showIcon,
          textColor: textColor,
          iconColor: iconColor,
          fontSize: fontSize,
          fontWeight: FontWeight.w600,
        ),
      ],
    );
  }
}