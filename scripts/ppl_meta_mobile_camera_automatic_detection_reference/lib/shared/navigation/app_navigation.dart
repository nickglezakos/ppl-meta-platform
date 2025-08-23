import 'package:flutter/material.dart';
import '../../features/camera/camera.dart';

/// Navigation helpers for the PPL Meta Camera app
class AppNavigation {
  /// Navigate to the gallery screen
  static void toGallery(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const GalleryScreen(),
      ),
    );
  }

  /// Navigate back to camera from any screen
  static void toCamera(BuildContext context) {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (context) => const CameraScreen(),
      ),
      (route) => false,
    );
  }

  /// Navigate with custom transition
  static void pushWithSlideTransition(
    BuildContext context,
    Widget destination, {
    Duration duration = const Duration(milliseconds: 300),
  }) {
    Navigator.of(context).push(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => destination,
        transitionDuration: duration,
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          const begin = Offset(1.0, 0.0);
          const end = Offset.zero;
          const curve = Curves.easeInOut;

          var tween = Tween(begin: begin, end: end).chain(
            CurveTween(curve: curve),
          );

          return SlideTransition(
            position: animation.drive(tween),
            child: child,
          );
        },
      ),
    );
  }
}
