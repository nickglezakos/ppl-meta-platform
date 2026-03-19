import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// Placeholder widget shown when the user lacks the media:view capability.
class MediaPrivacyPlaceholder extends StatelessWidget {
  final double? width;
  final double? height;

  const MediaPrivacyPlaceholder({super.key, this.width, this.height});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      color: Colors.grey.shade900,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SvgPicture.asset(
                'assets/images/eyenet-dark.svg',
                width: 120,
                height: 120,
              ),
              const SizedBox(height: 24),
              Text(
                'Media Privacy',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.white70,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                'Media viewing is disabled for your account.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white38,
                    ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
