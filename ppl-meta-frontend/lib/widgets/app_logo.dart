import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/whitelabel_provider.dart';

/// A widget that displays the current logo - either the whitelabel
/// custom logo if one has been uploaded, or the default Eyenet logo.
class AppLogo extends ConsumerWidget {
  final double height;
  final BoxFit? fit;

  const AppLogo({
    super.key,
    this.height = 32,
    this.fit,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logoState = ref.watch(whitelabelLogoProvider);

    return logoState.when(
      data: (customLogo) {
        if (customLogo != null) {
          return Image.memory(
            customLogo,
            height: height,
            fit: fit ?? BoxFit.contain,
            errorBuilder: (context, error, stackTrace) {
              return _buildDefaultLogo();
            },
          );
        }
        return _buildDefaultLogo();
      },
      loading: () {
        // During loading, show nothing or a small placeholder.
        // This prevents flickering on first load.
        return _buildDefaultLogo();
      },
      error: (error, stack) {
        return _buildDefaultLogo();
      },
    );
  }

  Widget _buildDefaultLogo() {
    return Image.asset(
      'assets/images/eyenet-logo.png',
      height: height,
      fit: fit ?? BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        return Icon(
          Icons.security,
          size: height * 0.8,
          color: Colors.blue,
        );
      },
    );
  }
}