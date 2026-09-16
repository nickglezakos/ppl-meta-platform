import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
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
        if (customLogo != null && customLogo.isNotEmpty) {
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
      loading: () => _buildDefaultLogo(),
      error: (error, stack) => _buildDefaultLogo(),
    );
  }

  Widget _buildDefaultLogo() {
    final boxFit = fit ?? BoxFit.contain;
    return Image.asset(
      'assets/images/eyenet-logo.png',
      height: height,
      fit: boxFit,
      errorBuilder: (context, error, stackTrace) {
        // PNG may be missing from older web AssetManifest builds.
        return SvgPicture.asset(
          'assets/images/eyenet-dark.svg',
          height: height,
          fit: boxFit,
          placeholderBuilder: (_) => Icon(
            Icons.security,
            size: height * 0.8,
            color: Colors.blue,
          ),
        );
      },
    );
  }
}