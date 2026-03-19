import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path/path.dart' as path;
import '../utils/platform_file_download.dart';

/// Service for capturing screenshots of the current page
class ScreenshotService {
  static final ScreenshotService _instance = ScreenshotService._internal();
  factory ScreenshotService() => _instance;
  ScreenshotService._internal();

  GlobalKey? _currentPageKey;
  
  /// Register the current page's GlobalKey for screenshot capture
  void registerPage(GlobalKey key) {
    _currentPageKey = key;
  }

  /// Capture the current page and save to docs/screenshots directory
  Future<String?> captureAndSave({String? fileName}) async {
    if (_currentPageKey == null) {
      print('❌ No page registered for screenshot');
      return null;
    }

    try {
      // Get the RenderRepaintBoundary
      final RenderRepaintBoundary boundary = _currentPageKey!.currentContext!
          .findRenderObject() as RenderRepaintBoundary;

      // Wait for any pending layouts/paints to complete
      await Future.delayed(const Duration(milliseconds: 50));

      // Convert to image with device pixel ratio for sharp screenshots
      final double pixelRatio = kIsWeb ? 2.0 : 3.0; // Lower ratio for web to avoid memory issues
      final ui.Image image = await boundary.toImage(pixelRatio: pixelRatio);
      
      // Convert to PNG bytes
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) {
        print('❌ Failed to convert image to bytes');
        return null;
      }

      final pngBytes = byteData.buffer.asUint8List();

      // Determine filename
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-').split('.')[0];
      final filename = fileName ?? 'screenshot_$timestamp.png';

      if (kIsWeb) {
        // Web platform: Download directly to browser downloads
        final savedPath = await downloadFileBytes(
          bytes: pngBytes,
          filename: filename,
          mimeType: 'image/png',
        );
        print('✅ Screenshot downloaded: $savedPath');
        print('📊 Image size: ${(pngBytes.length / 1024).toStringAsFixed(2)} KB');
        print('📐 Dimensions: ${image.width}x${image.height}');

        return savedPath;
      } else {
        // Desktop/Mobile platform: Save to docs/screenshots directory
        final projectRoot = Directory.current.path.contains('ppl-meta-frontend')
            ? Directory.current.parent.path
            : Directory.current.path;
        
        final screenshotsDir = Directory(path.join(projectRoot, 'docs', 'screenshots'));
        
        // Create directory if it doesn't exist
        if (!await screenshotsDir.exists()) {
          await screenshotsDir.create(recursive: true);
          print('📁 Created directory: ${screenshotsDir.path}');
        }

        // Save file
        final file = File(path.join(screenshotsDir.path, filename));
        await file.writeAsBytes(pngBytes);

        final savedPath = file.path;
        print('✅ Screenshot saved: $savedPath');
        print('📊 Image size: ${(pngBytes.length / 1024).toStringAsFixed(2)} KB');
        print('📐 Dimensions: ${image.width}x${image.height}');

        return savedPath;
      }
    } catch (e, stackTrace) {
      print('❌ Error capturing screenshot: $e');
      print(stackTrace);
      return null;
    }
  }

  /// Quick capture with auto-generated filename
  Future<String?> captureNow() async {
    return await captureAndSave();
  }
}
