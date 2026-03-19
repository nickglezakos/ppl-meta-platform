// MVR Face Thumbnail Widget
// Reusable widget for displaying face thumbnails with quality indicators

import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/mvr_best_image.dart';

class MVRFaceThumbnail extends StatelessWidget {
  final String? imageUrl;
  final double? qualityScore;
  final double radius;
  final bool showQualityBadge;
  final VoidCallback? onTap;

  const MVRFaceThumbnail({
    super.key,
    this.imageUrl,
    this.qualityScore,
    this.radius = 30,
    this.showQualityBadge = true,
    this.onTap,
  });

  factory MVRFaceThumbnail.fromBestImage(
    BestImageResponse? bestImage, {
    double radius = 30,
    bool showQualityBadge = true,
    VoidCallback? onTap,
  }) {
    return MVRFaceThumbnail(
      imageUrl: bestImage?.bestFace?.imageUrl,
      qualityScore: bestImage?.bestFace?.qualityScore,
      radius: radius,
      showQualityBadge: showQualityBadge,
      onTap: onTap,
    );
  }

  Color _getQualityColor(double quality) {
    if (quality >= 0.9) return Colors.green;
    if (quality >= 0.7) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    final widget = Stack(
      children: [
        CircleAvatar(
          radius: radius,
          backgroundColor: Colors.grey[300],
          child: imageUrl != null
              ? ClipOval(
                  child: CachedNetworkImage(
                    imageUrl: imageUrl!,
                    width: radius * 2,
                    height: radius * 2,
                    fit: BoxFit.cover,
                    placeholder: (context, url) => SizedBox(
                      width: radius,
                      height: radius,
                      child: const CircularProgressIndicator(strokeWidth: 2),
                    ),
                    errorWidget: (context, url, error) => Icon(
                      Icons.person,
                      size: radius,
                      color: Colors.grey[600],
                    ),
                  ),
                )
              : Icon(
                  Icons.person,
                  size: radius,
                  color: Colors.grey[600],
                ),
        ),
        // Quality badge
        if (showQualityBadge && qualityScore != null)
          Positioned(
            bottom: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: _getQualityColor(qualityScore!),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 1),
              ),
              child: Icon(
                Icons.check,
                size: radius * 0.4,
                color: Colors.white,
              ),
            ),
          ),
      ],
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: widget,
      );
    }

    return widget;
  }
}

class MVRFrameThumbnail extends StatelessWidget {
  final String? imageUrl;
  final double width;
  final double height;
  final VoidCallback? onTap;

  const MVRFrameThumbnail({
    super.key,
    this.imageUrl,
    this.width = 60,
    this.height = 40,
    this.onTap,
  });

  factory MVRFrameThumbnail.fromBestImage(
    BestImageResponse? bestImage, {
    double width = 60,
    double height = 40,
    VoidCallback? onTap,
  }) {
    return MVRFrameThumbnail(
      imageUrl: bestImage?.frameImage?.imageUrl,
      width: width,
      height: height,
      onTap: onTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    final widget = ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: imageUrl != null
          ? CachedNetworkImage(
              imageUrl: imageUrl!,
              width: width,
              height: height,
              fit: BoxFit.cover,
              placeholder: (context, url) => Container(
                width: width,
                height: height,
                color: Colors.grey[300],
                child: const Center(
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
              errorWidget: (context, url, error) => Container(
                width: width,
                height: height,
                color: Colors.grey[300],
                child: Icon(
                  Icons.image_not_supported,
                  color: Colors.grey[600],
                ),
              ),
            )
          : Container(
              width: width,
              height: height,
              color: Colors.grey[300],
              child: Icon(
                Icons.image,
                color: Colors.grey[600],
              ),
            ),
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: widget,
      );
    }

    return widget;
  }
}
