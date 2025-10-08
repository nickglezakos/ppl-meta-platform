import 'package:flutter/material.dart';
import 'widgets/face_detection_test_page.dart';

void main() {
  runApp(const FaceDetectionTestApp());
}

class FaceDetectionTestApp extends StatelessWidget {
  const FaceDetectionTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Face Detection API Test',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const FaceDetectionTestPage(),
      debugShowCheckedModeBanner: false,
    );
  }
}